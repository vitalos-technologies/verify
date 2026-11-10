# 15-minute demo script — synthetic demo tenant

| Field | Value |
|---|---|
| Audience | Recruitment / contractor-platform buyers and operational reviewers (discovery follow-ups, design-partner calls) |
| Data | **Synthetic only.** Tenant "Northstar Recruitment (demo)", created by `vv-admin seed-demo`. Mock identity provider, synthetic country `ZZ`. No real person, document or customer. |
| Presenter | Temitope Agbola |
| Devices | Laptop (console, screen-shared) + phone (applicant journey, shown via camera or phone mirroring) |
| Booking link for prospects | "Book a demo" → https://vitalos.co.uk |

## Honest-claims guardrails (read before every demo)

Say these plainly. Don't let a slide or answer contradict them.

| Do say | Don't say |
|---|---|
| "This is a **pilot-stage** product. What you're seeing runs on **synthetic data** with a **mock** identity engine." | "It's live", "customers use it", "it's accurate to X%" |
| "We're contracting a specialist document and face-check supplier; results will depend on that supplier and on our testing." | Any accuracy, fraud-catch or pass-rate figure |
| "It checks that someone is the genuine holder of a supported ID. Your team stays in control of hiring decisions." | "It's a **right-to-work** check", "**DBS** check", "**AML**/KYC compliant", "Home Office approved", "certified" |
| "We haven't had an external penetration test yet; it's planned before general availability." | "Bank-grade", "fully secure", "GDPR certified" |
| "Price we're testing: around £99/month plus £2.50 per completed check — a hypothesis for the pilot." | A firm price or discount promise |
| "Supported documents will be confirmed per country once the supplier and testing are in place." | "We support 200 countries" |

If asked about something not built: "Not yet — would that change whether you'd pilot?" Write it down.

## Before the demo (10 minutes)

- [ ] Fresh local or staging stack running; `VV_ENV` is development/test (seed-demo refuses to run in staging/production)
- [ ] `cd services/api && uv run vv-admin seed-demo` → note the owner and reviewer emails and the API key (shown once)
- [ ] Sign in to the console as `demo.owner@northstar.example` (magic link; in development the link is at `/dev/last-magic-link`) and enrol the authenticator on your own phone
- [ ] Second browser profile signed in as `demo.reviewer@northstar.example` (for second review / appeal)
- [ ] Platform operator session open on `/ops` in a third profile (optional section)
- [ ] Phone on the same network as the laptop; screen-sharing tested
- [ ] Close email, Slack, anything with real personal data
- [ ] Have one case in each state ready: approved, review required, declined, action required, expired, in progress

## Run sheet (15 minutes)

| Time | Screen | Goal |
|---|---|---|
| 0:00–1:00 | Intro | Set expectations |
| 1:00–2:30 | Home | Show the whole programme at a glance |
| 2:30–4:00 | New verification | One request → one link |
| 4:00–7:00 | Applicant journey on phone (QR handoff) | Applicant experience and alternatives |
| 7:00–9:00 | Review queue | Exceptions without spreadsheets |
| 9:00–11:00 | Case + evidence reveal | Distinct checks, controlled evidence access |
| 11:00–12:00 | Appeal | Fair challenge route |
| 12:00–13:00 | Usage | Transparent costs |
| 13:00–13:30 | Export | Evidence for audits, minimised |
| 13:30–14:00 | Operations (optional) | How Vitalos runs it without seeing evidence |
| 14:00–15:00 | Close | Pilot ask |

## Talk track

### 0:00 — Intro
"Thanks. I'll show you the full flow in about 12 minutes on a demo company called Northstar Recruitment. Everything here is synthetic — no real people — and the identity engine is a mock while we contract a specialist supplier. I'd like your honest view on whether this would save your team time."

Ask: "Before I start — how many ID checks did your team do last month?" (Use the answer later in Usage.)

### 1:00 — Home (`/app`)
- Point to counts by status: approved, needs review, declined, waiting on the applicant.
- "Each row is one applicant request. Your team sees what's stuck and why — no chasing in spreadsheets."
- Show filters by status and date. Note: no names in URLs or lists by default — just your own reference.

### 2:30 — New verification
- Click **New verification**. Enter a reference like `NS-CAND-1042` (your ATS ID, not a name).
- "The same thing can be done from your ATS through our API — one call."
- Show the link and QR code. "You'd normally email this; I'll open it on my phone."

### 4:00 — Applicant journey on the phone
Scan the QR (or open the link on laptop and use **use your phone** to hand off).
- **Intro**: "The applicant sees who's asking and why. The link works once and expires."
- **Your data**: "A short notice. Acknowledging it is recorded separately from consent, if your lawyers choose consent."
- **Confirm your email**: "Proves they control the inbox — we never treat that as proof of identity."
- **Capture**: "Here the supplier's camera step will run — document, then a live selfie. Today it's a mock panel."
  - Show "camera doesn't work" → alternative route and handoff appear. "No camera is **never** treated as fraud."
  - Pick a poor-quality capture → "Please try again" with a reason. "Two retries, then your alternative route."
- **Checking → Done**: "The phone shows done only when our server has the supplier's real result, not when the app says 'success'."
- Point at the footer: "The alternative route is on every screen — important for accessibility and fairness."

### 7:00 — Review queue (`/app/reviews`)
- "Anything not clearly approved lands here, oldest first."
- **Claim** a case: "A claim locks it to you for 15 minutes so two reviewers don't clash."
- "In the pilot, failed or unsure face or liveness results always come to a person. We don't auto-decline someone because of a camera or a score."

### 9:00 — Case page with evidence reveal (`/app/cases/{id}`)
- Show the separate checks: document authenticity, expiry, face match, liveness, email — each with result and reason.
- "A failed check can't be edited away. A reviewer can approve by an **alternative method** — say an in-person check — and that's labelled as such and needs a second reviewer."
- **Reveal evidence**: images are hidden by default. Enter a reason → authenticator code (step-up) → image shows.
  - "Every reveal needs a reason, a recent second-factor sign-in, and creates an access receipt. Download links last five minutes and only work for you."
- Timeline: "Everything that happened, in order — useful if a client audits you."
- Record a decision.

### 11:00 — Appeal
- On a declined case, **Create appeal** with the applicant's reason.
- "Appeals go to a different reviewer from the original decision, and evidence is held while it's open so it isn't deleted mid-dispute."
- Switch to the reviewer profile to show it in their queue.

### 12:00 — Usage (`/app/usage`)
- "You pay per **completed** verification — not for expired links or our technical failures. Credits are added, never edited."
- Use their number: "At [their volume] a month, at the price we're testing, that's about £[99 + volume × 2.50] — but that's a hypothesis. What would you expect to pay?"

### 13:00 — Export
- Click **Export**. "Default export has references, results, decision versions and timestamps — **no images or document numbers**. Evidence leaves only through the audited reveal."
- "Evidence is deleted 30 days after the decision by default; backups roll off within 35 days. Your organisation confirms those periods in the data agreement."

### 13:30 — Operations (optional, `/ops`)
- "This is our side. We see supplier health, queues and deletion backlogs — **metadata only**. Vitalos staff can't open your applicants' evidence."

### 14:00 — Close
- "We're looking for three design partners for a small, capped pilot. You'd name an operational owner, we'd agree documents, volume and success measures up front, and there's no obligation to continue."
- Ask: "Would that be worth doing? Who would own it on your side?"
- If yes → send `docs/commercial/pilot-intent-letter.md` after the call.

## Likely questions — honest answers

| Question | Answer |
|---|---|
| Is this a right-to-work check? | No. It checks identity. Right-to-work needs a Home Office–recognised process; we'd tell you if that changes. |
| How accurate is it? | We don't have measured results yet. We'll test the supplier before the pilot and share what we measure, with sample sizes. |
| Where is data stored? | Our platform is designed for AWS London. The supplier's processing location will be confirmed when we contract — we'll tell you before you use it. |
| Who's the supplier? | Being selected. We'll name it in the data agreement before any real data. |
| Are you certified (ISO 27001, Cyber Essentials, DVS)? | Not yet. [Owner to complete if any certification is obtained.] |
| Can it integrate with our ATS? | There's an API and signed webhooks now. Which ATS do you use? (write it down) |
| What if the applicant has no smartphone? | They can use a laptop webcam, hand off to another device, or use your alternative route. |
