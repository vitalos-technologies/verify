"""HTTP surface: public v1 API (contracts/openapi.json), applicant journey, provider callbacks, console.

Development-only routes (dummy provider capture, dev console login) are mounted only when
VV_ENV is development/test/ci.
"""


import os
import time
from dataclasses import dataclass
from datetime import UTC
from typing import Annotated, Any, Literal

from fastapi import Body, Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, ConfigDict, Field

from vv import applicant as ap
from vv import auth, billing, deletion, events, evidence, oidc, platform, review, service, webhooks
from vv.config import Settings, load_settings
from vv.db import Database
from vv.domain.coverage import CoverageRegistry
from vv.errors import ApiError
from vv.ids import new_id
from vv.log import log
from vv.providers.base import ProviderAdapter
from vv.providers.dummy import DummyProvider

APPLICANT_COOKIE = "vv_applicant"
CONSOLE_COOKIE = "vv_console"


# ------------------------------------------------------------------ request models (mirror openapi.json)
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSession(Strict):
    external_reference: str = Field(max_length=128, min_length=1)
    policy_id: str
    policy_version: int = Field(ge=1)
    country: str = Field(pattern=r"^[A-Z]{2}$")
    document_type: str


class ReviewDecision(Strict):
    expected_revision: int = Field(ge=1)
    outcome: Literal["approved", "declined", "action_required"]
    reason: str = Field(min_length=10, max_length=1000)
    method: Literal["evidence_review", "alternative_method"]
    evidence_ids: list[str] = Field(min_length=1)
    reviewer_reference: str | None = Field(default=None, max_length=128)


class WebhookEndpointRequest(Strict):
    url: str = Field(pattern=r"^https://")
    events: list[str] = Field(min_length=1)


class ReplayRequest(Strict):
    event_id: str
    endpoint_id: str


class DeleteRequest(Strict):
    subject_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=3, max_length=1000)
    controller_authorisation_reference: str = Field(min_length=1, max_length=200)


class ConsoleDecision(ReviewDecision):
    lock_version: int = Field(ge=1)


class SecondReview(Strict):
    confirm: bool


class AppealCreate(Strict):
    summary: str = Field(min_length=10, max_length=2000)


class AppealResolve(Strict):
    expected_revision: int = Field(ge=1)
    outcome: Literal["approved", "declined"]
    reason: str = Field(min_length=10, max_length=1000)
    method: Literal["evidence_review", "alternative_method"]
    evidence_ids: list[str] = Field(min_length=1)


class CreditRequest(Strict):
    ledger_key: str = Field(max_length=200)
    amount_minor: int = Field(gt=0)
    reason: str = Field(min_length=5, max_length=500)


class SupplierLine(Strict):
    provider_reference: str = Field(max_length=200)


class ReconcileRequest(Strict):
    period: str
    lines: list[SupplierLine] = Field(max_length=100_000)


class RevealRequest(Strict):
    reason: str = Field(min_length=10, max_length=500)


class LegalHoldRequest(Strict):
    subject_id: str
    owner: str = Field(min_length=3, max_length=200)
    reason: str = Field(min_length=10, max_length=1000)
    days: int = Field(ge=1, le=365)


class ExchangeRequest(Strict):
    token: str


class NoticeRequest(Strict):
    notice_version: str
    kind: Literal["acknowledgement", "explicit_consent"] = "acknowledgement"


class ContactSend(Strict):
    channel: Literal["email", "phone"]
    destination: str = Field(max_length=254)


class ContactVerify(Strict):
    code: str = Field(max_length=12)


class DummyCapture(Strict):
    capture_token: str
    scenario: str


class ApiKeyCreate(Strict):
    label: str = Field(default="", max_length=100)
    scopes: list[str] = Field(min_length=1)


class RevokeRequest(Strict):
    reason: str = Field(min_length=3, max_length=500)


class DevLogin(Strict):
    tenant_id: str
    user_subject: str


@dataclass
class AppState:
    settings: Settings
    db: Database
    coverage: CoverageRegistry
    providers: dict[str, ProviderAdapter]
    messenger: ap.DummyMessenger | None
    resolver: webhooks.Resolver
    store: evidence.LocalSealedStore | evidence.S3SealedStore


def create_app(settings: Settings | None = None, *, resolver: webhooks.Resolver | None = None,
               oidc_client: oidc.OidcClient | None = None) -> FastAPI:
    settings = settings or load_settings()
    if oidc_client is None and settings.oidc_issuer and settings.oidc_client_id:
        oidc_client = oidc.OidcClient(oidc.OidcConfig(
            settings.oidc_issuer, settings.oidc_client_id, settings.oidc_client_secret,
            settings.console_base_url.rstrip("/") + "/console/oidc/callback"))
    db = Database(settings.app_dsn)
    providers: dict[str, ProviderAdapter] = {}
    if settings.is_non_production:
        providers["dummy"] = DummyProvider(db, settings.dummy_provider_secret, settings.environment)
    state = AppState(settings, db, CoverageRegistry.load(settings.coverage_path), providers,
                     ap.DummyMessenger() if settings.is_non_production else None,
                     resolver or webhooks.default_resolver,
                     evidence.make_store(settings))
    app = FastAPI(title="Vitalos Verify API (prototype)", version="0.1.0", docs_url=None, redoc_url=None,
                  openapi_url="/openapi.json" if settings.is_non_production else None)
    app.state.vv = state

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = new_id("req")
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        route = request.scope.get("route")
        log("http.request", request_id=request.state.request_id, method=request.method,
            route=getattr(route, "path", "unmatched"), status_code=response.status_code,
            duration_ms=round((time.monotonic() - started) * 1000, 1))
        return response

    def error_body(request: Request, code: str, message: str) -> dict:
        return {"code": code, "message": message, "request_id": getattr(request.state, "request_id", "unknown")}

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return JSONResponse(error_body(request, exc.code, exc.message), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = sorted({".".join(str(p) for p in e.get("loc", [])[1:]) for e in exc.errors()})
        return JSONResponse(error_body(request, "invalid_request", "Invalid fields: " + ", ".join(fields)),
                            status_code=400)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log("http.unhandled", request_id=getattr(request.state, "request_id", None), error_type=type(exc).__name__)
        return JSONResponse(error_body(request, "internal_error", "An unexpected error occurred."), status_code=500)

    # -------------------------------------------------------------- dependencies
    def api_principal(request: Request, authorization: Annotated[str | None, Header()] = None) -> auth.Principal:
        principal = auth.authenticate_api_key(db, settings.hmac_pepper, authorization)
        _rate_limit(db, f"key:{principal.actor_id}", settings.api_rate_limit_per_minute)
        return principal

    def console_principal(request: Request, x_csrf_token: Annotated[str | None, Header()] = None) -> auth.Principal:
        return auth.authenticate_console(db, request.cookies.get(CONSOLE_COOKIE), x_csrf_token,
                                         mutating=request.method not in ("GET", "HEAD"),
                                         idle_seconds=settings.console_idle_seconds)

    def applicant_ctx(request: Request) -> ap.ApplicantContext:
        return ap.authenticate_applicant(db, request.cookies.get(APPLICANT_COOKIE))

    Api = Annotated[auth.Principal, Depends(api_principal)]
    Console = Annotated[auth.Principal, Depends(console_principal)]
    Applicant = Annotated[ap.ApplicantContext, Depends(applicant_ctx)]
    IdemKey = Annotated[str | None, Header(alias="Idempotency-Key")]

    def respond(status: int, body: Any) -> JSONResponse:
        return JSONResponse(body, status_code=status)

    # -------------------------------------------------------------- public API v1
    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "environment": settings.environment}

    @app.post("/v1/verifications")
    def create_verification(request: Request, principal: Api, body: CreateSession, idem: IdemKey = None):
        principal.require("sessions:create")
        payload = body.model_dump()
        with db.tenant_tx(principal.tenant_id) as conn:
            status, out = service.run_idempotent(
                conn, settings.data_key, principal.tenant_id, "createVerification", idem, payload,
                lambda c: service.create_session(
                    c, tenant_id=principal.tenant_id, actor_id=principal.actor_id, body=payload,
                    coverage=state.coverage, environment=settings.environment,
                    hosted_base_url=settings.hosted_base_url, hosted_ttl=settings.hosted_token_ttl_seconds,
                    price_minor=settings.session_price_minor, request_id=request.state.request_id))
        return respond(status, out)

    @app.get("/v1/verifications")
    def list_verifications(principal: Api, cursor: str | None = None, limit: int = 25,
                           state_filter: Annotated[str | None, Query(alias="state")] = None):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            return service.list_sessions(conn, principal.tenant_id, cursor=cursor, limit=limit, state=state_filter)

    @app.get("/v1/verifications/{session_id}")
    def get_verification(session_id: str, principal: Api):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            return service.session_view(conn, service.get_session(conn, principal.tenant_id, session_id))

    @app.post("/v1/verifications/{session_id}/decisions")
    def record_decision(request: Request, session_id: str, principal: Api, body: ReviewDecision, idem: IdemKey = None):
        principal.require("decisions:write")
        payload = body.model_dump()
        with db.tenant_tx(principal.tenant_id) as conn:
            status, out = service.run_idempotent(
                conn, settings.data_key, principal.tenant_id, f"recordReviewDecision:{session_id}", idem, payload,
                lambda c: service.record_review_decision(c, tenant_id=principal.tenant_id, session_id=session_id,
                                                         actor_id=principal.actor_id, body=payload,
                                                         request_id=request.state.request_id))
        return respond(status, out)

    @app.post("/v1/webhook-endpoints")
    def create_webhook_endpoint(request: Request, principal: Api, body: WebhookEndpointRequest):
        principal.require("webhooks:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            out = webhooks.create_endpoint(conn, settings.data_key, principal.tenant_id, body.url, body.events,
                                           state.resolver)
            service.audit(conn, principal.tenant_id, principal.actor_type, principal.actor_id, "webhook.create",
                          "webhook_endpoint", out["id"], request_id=request.state.request_id)
        return respond(201, out)

    @app.post("/v1/webhook-replays")
    def replay_webhook(request: Request, principal: Api, body: ReplayRequest, idem: IdemKey = None):
        principal.require("webhooks:manage")
        payload = body.model_dump()

        def run(c):
            out = webhooks.replay(c, principal.tenant_id, body.event_id, body.endpoint_id)
            service.audit(c, principal.tenant_id, principal.actor_type, principal.actor_id, "webhook.replay",
                          "webhook_delivery", out["id"], request_id=request.state.request_id)
            return 202, out

        with db.tenant_tx(principal.tenant_id) as conn:
            status, out = service.run_idempotent(conn, settings.data_key, principal.tenant_id, "replayWebhook", idem,
                                                 payload, run)
        return respond(status, out)

    @app.post("/v1/deletions")
    def request_deletion(request: Request, principal: Api, body: DeleteRequest, idem: IdemKey = None):
        principal.require("deletions:create")
        payload = body.model_dump()
        with db.tenant_tx(principal.tenant_id) as conn:
            status, out = service.run_idempotent(
                conn, settings.data_key, principal.tenant_id, "requestDeletion", idem, payload,
                lambda c: deletion.request_deletion(c, tenant_id=principal.tenant_id, actor_id=principal.actor_id,
                                                    body=payload, request_id=request.state.request_id))
        return respond(status, out)

    @app.get("/v1/deletions/{deletion_id}")
    def get_deletion(deletion_id: str, principal: Api):
        principal.require("deletions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            return deletion.get_deletion(conn, principal.tenant_id, deletion_id)

    # -------------------------------------------------------------- provider callbacks
    @app.post("/callbacks/{provider_name}")
    async def provider_callback(provider_name: str, request: Request):
        provider = state.providers.get(provider_name)
        if provider is None:
            raise ApiError(404, "not_found", "Resource not found.")
        raw = await request.body()
        if len(raw) > 64 * 1024:
            raise ApiError(413, "too_large", "Payload too large.")
        return respond(202, events.ingest_callback(db, provider, settings.data_key, raw, dict(request.headers)))

    # -------------------------------------------------------------- applicant journey
    def set_cookie(response: Response, name: str, value: str, path: str, max_age: int) -> None:
        response.set_cookie(name, value, max_age=max_age, path=path, httponly=True, samesite="strict",
                            secure=not settings.is_non_production or settings.hosted_base_url.startswith("https"))

    @app.post("/applicant/exchange")
    def applicant_exchange(body: ExchangeRequest, response: Response):
        cookie, ctx = ap.exchange_token(db, body.token, settings.applicant_session_ttl_seconds)
        set_cookie(response, APPLICANT_COOKIE, cookie, "/applicant", settings.applicant_session_ttl_seconds)
        with db.tenant_tx(ctx.tenant_id) as conn:
            return ap.applicant_view(conn, ctx)

    @app.post("/applicant/handoff")
    def applicant_handoff(ctx: Applicant):
        with db.tenant_tx(ctx.tenant_id) as conn:
            return respond(201, ap.create_handoff(conn, ctx))

    @app.post("/applicant/handoff/exchange")
    def applicant_handoff_exchange(body: ExchangeRequest, response: Response):
        cookie, ctx = ap.exchange_handoff(db, body.token, settings.applicant_session_ttl_seconds)
        set_cookie(response, APPLICANT_COOKIE, cookie, "/applicant", settings.applicant_session_ttl_seconds)
        with db.tenant_tx(ctx.tenant_id) as conn:
            return ap.applicant_view(conn, ctx)

    @app.get("/applicant/session")
    def applicant_session(ctx: Applicant):
        with db.tenant_tx(ctx.tenant_id) as conn:
            return ap.applicant_view(conn, ctx)

    @app.post("/applicant/notice")
    def applicant_notice(ctx: Applicant, body: NoticeRequest):
        with db.tenant_tx(ctx.tenant_id) as conn:
            ap.acknowledge_notice(conn, ctx, body.notice_version, body.kind)
            return ap.applicant_view(conn, ctx)

    @app.post("/applicant/contact/send")
    def applicant_contact_send(ctx: Applicant, body: ContactSend):
        return ap.send_contact_code(db, ctx, settings.hmac_pepper, state.messenger, body.channel, body.destination)

    @app.post("/applicant/contact/verify")
    def applicant_contact_verify(ctx: Applicant, body: ContactVerify):
        out = ap.verify_contact_code(db, ctx, settings.hmac_pepper, body.code)
        if "_error" in out:
            raise out["_error"]
        return out

    @app.post("/applicant/attempts")
    def applicant_attempt(request: Request, ctx: Applicant):
        with db.tenant_tx(ctx.tenant_id) as conn:
            provider_name = service.get_session(conn, ctx.tenant_id, ctx.session_id)["provider"]
        provider = state.providers.get(provider_name)
        if provider is None:
            raise ApiError(503, "provider.unavailable", "The verification service is temporarily unavailable.")
        return respond(201, ap.start_attempt(db, ctx, provider, request.state.request_id))

    @app.post("/applicant/attempts/{attempt_id}/submitted")
    def applicant_submitted(attempt_id: str, ctx: Applicant):
        return ap.mark_submitted(db, ctx, attempt_id)

    # -------------------------------------------------------------- console (cookie session + CSRF)
    def set_console_cookies(response: Response, token: str, csrf_token: str) -> None:
        set_cookie(response, CONSOLE_COOKIE, token, "/console", settings.console_absolute_seconds)
        # Double-submit CSRF token readable by the console script (not a credential on its own).
        response.set_cookie("vv_csrf", csrf_token, max_age=settings.console_absolute_seconds, path="/",
                            httponly=False, samesite="strict",
                            secure=not settings.is_non_production or settings.hosted_base_url.startswith("https"))

    @app.get("/console/oidc/start")
    def oidc_start(tenant: str | None = None):
        if oidc_client is None:
            raise ApiError(404, "not_found", "Resource not found.")
        with db.system_tx() as conn:
            url = oidc.start(conn, oidc_client, settings.data_key, tenant)
        return RedirectResponse(url, status_code=302)

    @app.get("/console/oidc/callback")
    def oidc_callback(code: str = "", state: str = ""):
        if oidc_client is None:
            raise ApiError(404, "not_found", "Resource not found.")
        result = oidc.finish(db, oidc_client, settings.data_key, code, state)
        with db.system_tx() as conn:
            members = list(conn.execute("SELECT * FROM vv_memberships_for_subject(%s)", (result["subject"],)))
        if result["tenant_hint"]:
            members = [m for m in members if m["tenant_id"] == result["tenant_hint"]]
        if len(members) != 1:
            # No silent binding by email; one subject in several organisations must pick one.
            raise ApiError(403, "no_membership" if not members else "choose_organisation",
                           "No access to this organisation." if not members else "Choose an organisation to sign in.")
        m = members[0]
        with db.tenant_tx(m["tenant_id"]) as conn:
            token, csrf_token = auth.create_console_session(
                conn, m["tenant_id"], m["id"], settings.console_absolute_seconds, auth_method="oidc",
                amr=result["amr"], auth_time=result["auth_time"])
            service.audit(conn, m["tenant_id"], "console", m["id"], "console.sign_in", "membership", m["id"],
                          reason="oidc+mfa")
        response = RedirectResponse(settings.console_base_url.rstrip("/") + "/app", status_code=302)
        set_console_cookies(response, token, csrf_token)
        return response

    @app.post("/console/api-keys")
    def console_create_key(request: Request, principal: Console, body: ApiKeyCreate):
        principal.require("api_keys:manage")
        principal.require_recent_auth()
        with db.tenant_tx(principal.tenant_id) as conn:
            key_id, raw = auth.create_api_key(conn, settings.hmac_pepper, settings.environment, principal.tenant_id,
                                              body.scopes, body.label, principal.actor_id)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "api_key.create", "api_key",
                          key_id, request_id=request.state.request_id)
        return respond(201, {"id": key_id, "key": raw, "note": "Shown once. Store it in a secret manager."})

    @app.post("/console/api-keys/{key_id}/revoke")
    def console_revoke_key(request: Request, key_id: str, principal: Console, body: RevokeRequest):
        principal.require("api_keys:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            row = conn.execute("UPDATE api_keys SET revoked_at = coalesce(revoked_at, now()), revoked_reason = "
                               "coalesce(revoked_reason, %s) WHERE tenant_id = %s AND id = %s RETURNING id",
                               (body.reason, principal.tenant_id, key_id)).fetchone()
            if row is None:
                raise ApiError(404, "not_found", "Resource not found.")
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "api_key.revoke", "api_key",
                          key_id, reason=body.reason, request_id=request.state.request_id)
        return {"id": key_id, "state": "revoked"}

    @app.post("/console/memberships/{membership_id}/revoke")
    def console_revoke_membership(request: Request, membership_id: str, principal: Console, body: RevokeRequest):
        principal.require("memberships:manage")
        principal.require_recent_auth()
        with db.tenant_tx(principal.tenant_id) as conn:
            auth.revoke_membership(conn, principal.tenant_id, membership_id, body.reason)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "membership.revoke",
                          "membership", membership_id, reason=body.reason, request_id=request.state.request_id)
        return {"id": membership_id, "state": "revoked"}

    @app.post("/console/policies")
    def console_create_policy(principal: Console, definition: Annotated[dict, Body()]):
        principal.require("policies:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            return respond(201, service.create_policy_draft(conn, principal.tenant_id, definition))

    @app.post("/console/policies/{key}/{version}/publish")
    def console_publish_policy(request: Request, key: str, version: int, principal: Console):
        principal.require("policies:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            out = service.publish_policy(conn, principal.tenant_id, key, version, state.coverage,
                                         settings.session_price_minor)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "policy.publish", "policy",
                          out["id"], request_id=request.state.request_id)
        return out

    @app.post("/console/legal-holds")
    def console_legal_hold(request: Request, principal: Console, body: LegalHoldRequest):
        principal.require("legal_holds:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            subj = conn.execute("SELECT id FROM subjects WHERE tenant_id = %s AND (id = %s OR external_reference = %s)",
                                (principal.tenant_id, body.subject_id, body.subject_id)).fetchone()
            if subj is None:
                raise ApiError(404, "not_found", "Resource not found.")
            hold_id = deletion.place_legal_hold(conn, principal.tenant_id, subj["id"], body.owner, body.reason,
                                                body.days)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "legal_hold.place", "subject",
                          subj["id"], reason=body.reason, request_id=request.state.request_id)
        return respond(201, {"id": hold_id, "state": "active"})

    # Review queue, leases, second review (VV-008).
    @app.get("/console/reviews")
    def console_review_queue(principal: Console, limit: int = 50):
        principal.require("decisions:write")
        with db.tenant_tx(principal.tenant_id) as conn:
            return review.queue(conn, principal.tenant_id, limit)

    @app.post("/console/reviews/{review_id}/claim")
    def console_review_claim(review_id: str, principal: Console):
        principal.require("decisions:write")
        with db.tenant_tx(principal.tenant_id) as conn:
            return review.claim(conn, principal.tenant_id, review_id, principal.actor_id)

    @app.post("/console/reviews/{review_id}/decision")
    def console_review_decide(request: Request, review_id: str, principal: Console, body: ConsoleDecision):
        principal.require("decisions:write")
        payload = body.model_dump(exclude={"lock_version"})
        with db.tenant_tx(principal.tenant_id) as conn:
            return review.decide(conn, principal.tenant_id, review_id, principal.actor_id, payload,
                                 body.lock_version, request.state.request_id)

    @app.post("/console/reviews/{review_id}/second-review")
    def console_second_review(request: Request, review_id: str, principal: Console, body: SecondReview):
        principal.require("decisions:write")
        with db.tenant_tx(principal.tenant_id) as conn:
            return review.second_review(conn, principal.tenant_id, review_id, principal.actor_id, body.confirm,
                                        request.state.request_id)

    # Appeals: recorded by the requesting organisation on the applicant's behalf.
    @app.post("/console/verifications/{session_id}/appeals")
    def console_appeal_create(session_id: str, principal: Console, body: AppealCreate):
        principal.require("decisions:write")
        with db.tenant_tx(principal.tenant_id) as conn:
            return respond(201, review.create_appeal(conn, principal.tenant_id, session_id, principal.actor_id,
                                                     body.summary))

    @app.post("/console/appeals/{appeal_id}/claim")
    def console_appeal_claim(appeal_id: str, principal: Console):
        principal.require("decisions:write")
        with db.tenant_tx(principal.tenant_id) as conn:
            return review.claim_appeal(conn, principal.tenant_id, appeal_id, principal.actor_id)

    @app.post("/console/appeals/{appeal_id}/resolve")
    def console_appeal_resolve(request: Request, appeal_id: str, principal: Console, body: AppealResolve):
        principal.require("decisions:write")
        with db.tenant_tx(principal.tenant_id) as conn:
            return review.resolve_appeal(conn, principal.tenant_id, appeal_id, principal.actor_id,
                                         body.model_dump(), request.state.request_id)

    # Usage and billing (VV-012).
    @app.get("/console/usage")
    def console_usage(principal: Console, period: str):
        principal.require("billing:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            return billing.summary(conn, principal.tenant_id, period)

    @app.post("/console/usage/credits")
    def console_credit(request: Request, principal: Console, body: CreditRequest):
        principal.require("billing:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            out = billing.add_credit(conn, principal.tenant_id, body.ledger_key, body.amount_minor, body.reason,
                                     principal.actor_id)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "billing.credit", "usage_event",
                          out["id"], reason=body.reason, request_id=request.state.request_id)
        return respond(201, out)

    @app.post("/console/invoices/{period}/issue")
    def console_issue_invoice(request: Request, period: str, principal: Console):
        principal.require("billing:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            out = billing.issue_invoice(conn, principal.tenant_id, period, principal.actor_id)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "billing.invoice", "invoice",
                          out["invoice_id"], request_id=request.state.request_id)
        return respond(201, out)

    @app.post("/console/usage/reconcile")
    def console_reconcile(principal: Console, body: ReconcileRequest):
        principal.require("billing:manage")
        with db.tenant_tx(principal.tenant_id) as conn:
            return billing.reconcile_supplier(conn, principal.tenant_id, body.period,
                                              [x.model_dump() for x in body.lines])

    # Evidence: list, purpose-bound reveal, expiring download, minimal export (VV-010, VV-024).
    @app.get("/console/verifications/{session_id}/evidence")
    def console_evidence(session_id: str, principal: Console):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            service.get_session(conn, principal.tenant_id, session_id)
            return {"items": evidence.list_for_session(conn, principal.tenant_id, session_id)}

    @app.post("/console/evidence/{evidence_id}/reveal")
    def console_reveal(request: Request, evidence_id: str, principal: Console, body: RevealRequest):
        principal.require_recent_auth()
        with db.tenant_tx(principal.tenant_id) as conn:
            role = conn.execute("SELECT role FROM memberships WHERE tenant_id = %s AND id = %s",
                                (principal.tenant_id, principal.actor_id)).fetchone()["role"]
            return evidence.reveal(conn, secret=settings.data_key, tenant_id=principal.tenant_id,
                                   evidence_id=evidence_id, member=principal.actor_id, role=role,
                                   reason=body.reason, request_id=request.state.request_id)

    @app.get("/console/evidence/download")
    def console_download(request: Request, token: str, principal: Console):
        data, ctype = evidence.download(db, state.store, secret=settings.data_key, tenant_id=principal.tenant_id,
                                        member=principal.actor_id, token=token, request_id=request.state.request_id)
        csp = "default-src 'none'; style-src 'unsafe-inline'"
        return RawResponse(data, media_type=ctype, headers={"Content-Disposition": "inline",
                                                           "Content-Security-Policy": csp})

    @app.get("/console/exports/verifications.csv")
    def console_export(request: Request, principal: Console, period: str):
        if not ({"sessions:read", "audit:read"} & principal.permissions):
            raise ApiError(403, "forbidden", "This credential is not permitted to perform this action.")
        billing._period(period)
        with db.tenant_tx(principal.tenant_id) as conn:
            body = evidence.export_csv(conn, principal.tenant_id, period)
            service.audit(conn, principal.tenant_id, "console", principal.actor_id, "export.verifications", "export",
                          period, request_id=request.state.request_id)
        return RawResponse(body, media_type="text/csv", headers={
            "Content-Disposition": f'attachment; filename="verifications-{period}.csv"'})

    @app.post("/console/verifications")
    def console_create(request: Request, principal: Console, body: CreateSession,
                       idem: IdemKey = None):
        principal.require("sessions:create")
        payload = body.model_dump()
        with db.tenant_tx(principal.tenant_id) as conn:
            status, out = service.run_idempotent(
                conn, settings.data_key, principal.tenant_id, "createVerification", idem, payload,
                lambda c: service.create_session(
                    c, tenant_id=principal.tenant_id, actor_id=principal.actor_id, body=payload,
                    coverage=state.coverage, environment=settings.environment,
                    hosted_base_url=settings.hosted_base_url, hosted_ttl=settings.hosted_token_ttl_seconds,
                    price_minor=settings.session_price_minor, request_id=request.state.request_id))
        return respond(status, out)

    @app.get("/console/stats")
    def console_stats(principal: Console):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            rows = {r["state"]: r["n"] for r in conn.execute(
                "SELECT state, count(*) AS n FROM sessions WHERE tenant_id = %s GROUP BY state",
                (principal.tenant_id,))}
            queue = conn.execute("SELECT count(*) AS n FROM reviews WHERE tenant_id = %s AND status <> 'closed'",
                                 (principal.tenant_id,)).fetchone()["n"]
        return {"total": sum(rows.values()), "verified": rows.get("approved", 0),
                "needs_review": rows.get("review_required", 0),
                "in_progress": sum(rows.get(k, 0) for k in ("created", "in_progress", "processing", "action_required")),
                "declined": rows.get("declined", 0), "review_queue": queue}

    # Platform administration / operations (metadata only).
    def platform_principal(request: Request) -> dict:
        return platform.authenticate(db, request.cookies.get("vv_platform"))

    @app.get("/platform/me")
    def platform_me(request: Request):
        op = platform_principal(request)
        return {"display_name": op["display_name"], "role": op["role"]}

    @app.get("/platform/organisations")
    def platform_orgs(request: Request):
        platform.require(platform_principal(request), {"platform_admin"})
        with db.system_tx() as conn:
            return platform.organisations(conn, state.coverage)

    @app.get("/platform/organisations/{tenant_id}/activity")
    def platform_org_activity(request: Request, tenant_id: str):
        platform.require(platform_principal(request), {"platform_admin"})
        with db.system_tx() as conn:
            return platform.activity(conn, tenant_id)

    @app.get("/platform/operations")
    def platform_ops(request: Request):
        platform.require(platform_principal(request), {"platform_admin", "operations"})
        with db.system_tx() as conn:
            out = platform.operations(conn, sorted(state.providers))
        out["environment"] = settings.environment
        return out

    @app.get("/console/me")
    def console_me(principal: Console):
        with db.tenant_tx(principal.tenant_id) as conn:
            t = conn.execute("SELECT name FROM tenants WHERE id = %s", (principal.tenant_id,)).fetchone()
            m = conn.execute("SELECT role FROM memberships WHERE tenant_id = %s AND id = %s",
                             (principal.tenant_id, principal.actor_id)).fetchone()
        return {"tenant_name": t["name"], "membership_id": principal.actor_id, "role": m["role"],
                "permissions": sorted(principal.permissions)}

    @app.get("/console/verifications")
    def console_list(principal: Console, cursor: str | None = None, limit: int = 25,
                     state_filter: Annotated[str | None, Query(alias="state")] = None):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            return service.list_sessions(conn, principal.tenant_id, cursor=cursor, limit=limit, state=state_filter)

    @app.get("/console/verifications/{session_id}/timeline")
    def console_timeline(session_id: str, principal: Console):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            service.get_session(conn, principal.tenant_id, session_id)
            decisions = [{"at": r["created_at"].astimezone(UTC).isoformat(), "kind": "decision",
                          "revision": r["revision"], "outcome": r["outcome"], "method": r["method"],
                          "actor_type": r["actor_type"], "reason_codes": list(r["reason_codes"])}
                         for r in conn.execute("SELECT * FROM decisions WHERE tenant_id = %s AND session_id = %s",
                                               (principal.tenant_id, session_id))]
            events_ = [{"at": r["created_at"].astimezone(UTC).isoformat(), "kind": "event",
                        "type": r["event_type"], "state": r["payload"]["state"]}
                       for r in conn.execute("SELECT * FROM outbox WHERE tenant_id = %s AND resource_id = %s",
                                             (principal.tenant_id, session_id))]
            rev = conn.execute("SELECT * , coalesce(lease_expires_at > now(), false) AS leased FROM reviews "
                               "WHERE tenant_id = %s AND session_id = %s AND status <> 'closed'",
                               (principal.tenant_id, session_id)).fetchone()
            appeal = conn.execute("SELECT id, status, assignee FROM appeals WHERE tenant_id = %s AND session_id = %s "
                                  "AND status <> 'resolved'", (principal.tenant_id, session_id)).fetchone()
        items = sorted(decisions + events_, key=lambda x: x["at"])
        return {"items": items,
                "review": review._out(rev) if rev else None,
                "appeal": dict(appeal) if appeal else None}

    @app.get("/console/verifications/{session_id}")
    def console_get_verification(session_id: str, principal: Console):
        principal.require("sessions:read")
        with db.tenant_tx(principal.tenant_id) as conn:
            return service.session_view(conn, service.get_session(conn, principal.tenant_id, session_id))

    # -------------------------------------------------------------- development-only routes
    if settings.is_non_production:
        @app.post("/console/dev-login")
        def dev_login(body: DevLogin, response: Response):
            """DEV ONLY: stands in for OIDC sign-in until the identity provider is selected (M01/M02)."""
            with db.tenant_tx(body.tenant_id) as conn:
                m = conn.execute("SELECT id FROM memberships WHERE tenant_id = %s AND user_subject = %s AND active",
                                 (body.tenant_id, body.user_subject)).fetchone()
                if m is None:
                    raise ApiError(401, "unauthenticated", "Valid credentials are required.")
                token, csrf = auth.create_console_session(conn, body.tenant_id, m["id"],
                                                          settings.console_absolute_seconds)
            set_console_cookies(response, token, csrf)
            return {"csrf_token": csrf}

        if os.environ.get("VV_DEV_EXPOSE_CODES") == "1":
            @app.get("/dev/last-contact-code")
            def dev_last_code():
                """DEV/E2E ONLY (VV_DEV_EXPOSE_CODES=1, non-production): read the dummy messenger's last code."""
                return {"code": state.messenger.last_sent}

        @app.post("/platform/dev-login")
        def platform_dev_login(body: DevLogin, response: Response):
            """DEV ONLY: platform operator sign-in (tenant_id is ignored; user_subject identifies the operator)."""
            with db.system_tx() as conn:
                op = conn.execute("SELECT id FROM platform_operators WHERE subject = %s AND active",
                                  (body.user_subject,)).fetchone()
                if op is None:
                    raise ApiError(401, "unauthenticated", "Valid credentials are required.")
                token, csrf = platform.create_session(conn, op["id"])
            set_cookie(response, "vv_platform", token, "/platform", 8 * 3600)
            return {"csrf_token": csrf}

        @app.post("/dummy-provider/capture")
        def dummy_capture(body: DummyCapture):
            """DEV ONLY: simulates the supplier-hosted capture and the supplier's signed callback."""
            dummy = state.providers["dummy"]
            assert isinstance(dummy, DummyProvider)
            try:
                reference = dummy.simulate_capture(body.capture_token, body.scenario)
            except ValueError:
                raise ApiError(400, "unknown_scenario", "Unknown synthetic scenario.") from None
            except PermissionError:
                raise ApiError(403, "capture_token_invalid", "Capture token invalid or already used.") from None
            raw, headers = dummy.build_callback(reference)
            events.ingest_callback(db, dummy, settings.data_key, raw, headers)
            return {"status": "captured", "note": "Synthetic dummy provider; no images processed."}

    return app


def _rate_limit(db: Database, bucket: str, per_minute: int) -> None:
    with db.system_tx() as conn:
        row = conn.execute(
            "INSERT INTO rate_limit_windows (bucket, window_start, count) VALUES (%s, date_trunc('minute', now()), 1) "
            "ON CONFLICT (bucket, window_start) DO UPDATE SET count = rate_limit_windows.count + 1 "
            "RETURNING count, 60 - extract(second FROM now())::int AS retry", (bucket,)).fetchone()
    if row["count"] > per_minute:
        raise ApiError(429, "rate_limited", "Too many requests.", {"Retry-After": str(max(1, row["retry"]))})


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8000, proxy_headers=True, access_log=False)  # noqa: S104
