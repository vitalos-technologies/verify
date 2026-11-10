# Manual accessibility test pack — AT-04 (WCAG 2.2 AA)

| Field | Value |
|---|---|
| Requirement | VV-004 / AT-04 Accessible capture: complete the supported journey using small-screen mobile, keyboard and screen reader; deny camera access. Expected: usable guidance and an alternative path; **no false fraud result for device limitations**. |
| Standard | WCAG 2.2 level AA |
| Status | **Not run.** Automated checks pass (Chromium mobile emulation at 390 px and 320 px, keyboard-only activation, focus to step heading, live-region announcements, axe WCAG 2.0/2.1/2.2 A/AA scan at each step, camera denied, invalid link, refresh — `apps/web/e2e/applicant.spec.ts`; axe on console — `apps/web/e2e/console.spec.ts`). Manual device and screen-reader testing has **not** been done. |
| Important limit | Capture today uses the **mock** provider's synthetic panel. When a real supplier SDK is integrated, re-run §3.5 (capture) in full — the supplier's camera UI is a new component and may fail on its own. |
| Tester(s) | [Owner to complete: name, experience, whether an assistive-technology user] |
| Build under test | [Owner to complete: commit SHA, URL (staging or local), date] |

## 1. Device and assistive-technology matrix

Fill in the actual versions used. "Required" rows must pass before the pilot.

| ID | Device / setting | Browser | Assistive technology | Required? | Version used | Tester | Date | Result |
|---|---|---|---|---|---|---|---|---|
| D1 | iPhone (current iOS) | Safari | VoiceOver | Required | [ ] | | | |
| D2 | Android phone (current) | Chrome | TalkBack | Required | [ ] | | | |
| D3 | Windows laptop | Firefox | NVDA | Required | [ ] | | | |
| D4 | Windows laptop | Chrome | NVDA | Required | [ ] | | | |
| D5 | Any desktop | Chrome or Firefox | **Keyboard only** (no mouse) | Required | [ ] | | | |
| D6 | Desktop | Chrome | Browser zoom **200%** | Required | [ ] | | | |
| D7 | Desktop | Chrome | Browser zoom **400%** (equals 320 px reflow at 1280 px width) | Required | [ ] | | | |
| D8 | Phone or emulator at **320 px** width | Chrome | — | Required | [ ] | | | |
| D9 | iOS or Android | Safari / Chrome | **Reduce motion** on | Required | [ ] | | | |
| D10 | Windows | Chrome or Edge | **Contrast themes** (high contrast) on | Required | [ ] | | | |
| D11 | **Low-memory Android** (≤ 3 GB RAM, e.g. an Android Go device) | Chrome | — | Required | [Owner to complete: model] | | | |
| D12 | iPhone | Safari | Larger Text (Dynamic Type at max accessibility size) | Recommended | [ ] | | | |
| D13 | Android | Chrome | Font size and display size at max | Recommended | [ ] | | | |
| D14 | macOS | Safari | VoiceOver | Recommended | [ ] | | | |
| D15 | Windows | Chrome | Dragon / voice control, or iOS Voice Control | Recommended | [ ] | | | |

## 2. How to set up a test run

1. Start the stack (local or staging). Local: see `README.md` — `./scripts/dev.sh --seed`, then `cd apps/web && VV_ENABLE_DUMMY_PROVIDER=1 npm run dev`.
2. Create a fresh verification for each run (API `POST /v1/verifications` with country `ZZ`, document `passport`, or console "New verification"). Each link works **once**.
3. Use a test email address you control; in development the code is visible via `/dev/last-contact-code`.
4. Use **synthetic data only**. Never photograph a real identity document.
5. Record every issue in §6 with the WCAG criterion, device ID and a screenshot/recording with no personal data.

## 3. Applicant journey scripts

For **each** of D1–D11, run scripts 3.1–3.9. Expected results apply to every device unless noted.

### 3.1 Open the link (intro — heading "Let's check it's you")

| Step | Action | Expected result | WCAG |
|---|---|---|---|
| 1 | Open the link | Page title names the step. Requesting business and purpose are shown. Link token disappears from the address bar. | 2.4.2 Page titled |
| 2 | Screen reader: read page from top | Heading level 1 is read first after landmarks; logical reading order; no "unlabelled button" | 1.3.1, 4.1.2 |
| 3 | Keyboard: Tab through page | Visible focus on every control, in a logical order; focus never hidden behind a sticky footer | 2.4.7, 2.4.11 Focus not obscured |
| 4 | Find the alternative route | Link to the alternative route is present in the footer and reachable by keyboard and screen reader; it is in the **same place** on every step | 3.2.6 Consistent help |
| 5 | Measure tap targets | Every button/link at least 24 × 24 CSS px or well spaced | 2.5.8 Target size |
| 6 | 320 px / 400% zoom | No horizontal scrolling; no text cut off | 1.4.10 Reflow |

### 3.2 Privacy notice (heading "Your data")

| Step | Action | Expected result | WCAG |
|---|---|---|---|
| 1 | Read the notice with screen reader | All text is read; links say where they go | 2.4.4 |
| 2 | Submit without acknowledging | Error summary appears ("There is a problem"), focus moves to it, error is linked to the checkbox | 3.3.1, 3.3.3 |
| 3 | Acknowledge and continue | Focus moves to the next step's heading; screen reader announces it | 2.4.3, 4.1.3 |
| 4 | If consent is shown separately from acknowledgement | They are two separate controls; consent is not pre-ticked | 3.3.2 Labels |

### 3.3 Email code (heading "Confirm your email")

| Step | Action | Expected result | WCAG |
|---|---|---|---|
| 1 | Enter email | Field has a visible label and `autocomplete="email"` | 1.3.5, 3.3.2 |
| 2 | Request code | Status "code sent" announced without moving focus unexpectedly | 4.1.3 |
| 3 | Enter code | Field accepts **paste** and phone autofill (`autocomplete="one-time-code"`); no puzzle or memory test | 3.3.8 Accessible authentication |
| 4 | Enter wrong code | Clear error linked to the field; remaining attempts not misleading | 3.3.1 |
| 5 | Wait past code expiry, then retry | Clear message and a way to send a new code | 2.2.1 Timing |

### 3.4 Device handoff (QR) — desktop to phone

| Step | Action | Expected result | WCAG |
|---|---|---|---|
| 1 | On desktop, choose "use your phone" | QR code has a text alternative and a **non-QR option** (e.g. a link to copy or send) for people who cannot scan | 1.1.1 |
| 2 | Scan on phone | Same verification continues on phone; desktop shows it moved | — |
| 3 | Try the QR again after use or after 10 minutes | "Link expired or already used" page, with what to do next | 3.3.1 |

### 3.5 Capture (document and selfie)

| Step | Action | Expected result | WCAG / AT-04 |
|---|---|---|---|
| 1 | Screen reader: start capture | Instructions are text, read aloud; no instruction is image-only or colour-only | 1.1.1, 1.4.1 |
| 2 | Keyboard: start and complete capture (mock panel) | All controls operable by keyboard; no drag-only action | 2.1.1, 2.5.7 |
| 3 | **Deny camera permission** | Plain message; alternative route and phone handoff offered; **no** "failed" or "fraud" outcome recorded (check console case afterwards) | AT-04 |
| 4 | Poor capture (mock "poor quality") | "Please try again" with a reason; focus to heading; retry count clear | 3.3.1, 4.1.3 |
| 5 | Reduce motion on | No animation that cannot be paused; liveness instructions still usable | 2.3.3 (AAA, advisory), 2.2.2 |
| 6 | Real supplier SDK only: flashing lights in liveness | No more than three flashes per second; warning given before start | 2.3.1 |
| 7 | Time limits in capture | Any timeout is announced in advance and can be extended or restarted without losing progress | 2.2.1 |

### 3.6 Processing (heading "Checking")

| Step | Action | Expected result | WCAG |
|---|---|---|---|
| 1 | Wait | Status changes are announced by screen reader (live region) without focus jumping repeatedly | 4.1.3 |
| 2 | Refresh / leave and come back | Progress is kept (server state) | — |
| 3 | Go offline | Offline message; recovers when back online | 3.3.1 |

### 3.7 Outcome (heading "Done" / "Please try again")

| Step | Action | Expected result |
|---|---|---|
| 1 | Read outcome | Plain-language result; no fraud wording; support and challenge route present |
| 2 | Close tab, reopen original link | "Session ended" or "Link expired or already used" with next steps |

### 3.8 Error pages

Open an invalid link, an expired link and a used link. Each must have an h1, explain what happened in one line, and give the alternative/support route.

### 3.9 Colour and text checks (desktop, once per build)

| Check | Expected | WCAG |
|---|---|---|
| Text contrast | ≥ 4.5:1 (≥ 3:1 for large text) | 1.4.3 |
| Focus ring and input borders contrast | ≥ 3:1 | 1.4.11 |
| Text spacing bookmarklet (line height 1.5, letter 0.12, word 0.16, paragraph 2) | Nothing overlaps or is cut | 1.4.12 |
| Windows contrast theme | All controls and focus visible | 1.4.11 |
| Portrait and landscape on phone | Both work | 1.3.4 |

## 4. Customer console scripts

Run with D3/D4 (NVDA), D5 (keyboard), D6/D7 (zoom). Use the synthetic demo tenant (`vv-admin seed-demo` — "Northstar Recruitment (demo)").

| Screen | Steps | Expected result |
|---|---|---|
| Sign-in (`/app/login`) | Sign in with email magic link; enrol authenticator; enter code | Labelled fields; code field accepts paste/autofill; QR for enrolment has a text secret alternative; errors linked to fields; no CAPTCHA puzzle (3.3.8) |
| Step-up dialog | Trigger an evidence reveal; dialog asks for a code | Focus moves into the dialog, is trapped while open, Escape closes, focus returns to the trigger (2.4.3, 4.1.2) |
| Home / verifications list | Tab through filters, list and "New verification" | Table has headers; status not shown by colour alone (1.4.1); pagination labelled |
| New verification | Create a request with a missing field | Error summary; QR / link shown has text alternative |
| Export | Use keyboard to export CSV | Button reachable; file download announced or obvious |
| Review queue (`/app/reviews`) | Claim a case | Claim result announced (4.1.3); lease time shown as text |
| Case page (`/app/cases/{id}`) | Read checks; reveal evidence with a reason; record decision; open appeal | Each check has result **and** reason in text; reveal requires a labelled reason field; image has an alt text naming its type (not its content); decision form errors linked; timeline readable as a list |
| Usage (`/app/usage`) | Read usage table | Table headers; currency read correctly |
| Session timeout | Leave idle 30 minutes | Warning before timeout if possible; sign-in again returns to the same page (2.2.1) |

## 5. Plan: sessions with 5 representative applicants (spec 04 §Design deliverables)

| Item | Plan |
|---|---|
| Who | 5 adults who resemble real applicants: at least **one assistive-technology user** (screen reader or switch/voice control); one person aged 55+; one person with English as an additional language; one person using an older/low-memory Android phone; one person with low digital confidence. [Owner to complete: final mix] |
| Recruitment | Through a disability-led user-research panel or charity network, local job clubs, or personal networks (not current applicants of a customer). [Owner to complete: recruiter or channel] |
| Payment | [Owner to complete: incentive per participant and method] — pay the same whether or not they finish |
| Consent | Written information sheet and consent form before the session: purpose, what is recorded (screen + audio, no face video unless agreed), how long it is kept ([Owner to complete: e.g. 90 days]), right to stop at any time without losing payment |
| Data | **Synthetic only.** Participants use the mock capture; for any document step use the supplied fake specimen document. Never ask participants to show their own ID or face to a live verification. |
| Format | 45–60 min, remote or in person, on the participant's own device where possible; 1 facilitator + 1 note-taker |
| Tasks | (1) Open the link from an email and finish the verification. (2) Switch from laptop to phone. (3) Imagine your camera does not work — what would you do? (4) Explain back, in your own words, what data is collected and who sees it (comprehension of notice). (5) Find how to challenge a result. |
| Measures | Task success (yes / with help / no), time, errors, comprehension score (0–2 per question), confidence rating 1–5, quotes |
| Accessibility | Offer materials in advance in accessible formats; allow breaks; ask participants to use their own AT setup |
| Output | Findings table (§6) with severity; changes made; record in `docs/evidence/` without personal data |

## 6. Results recording table

| ID | Date | Tester | Device (D#) | Script step | WCAG criterion | Issue (what happened) | Severity (Blocker / Major / Minor) | Screenshot ref (no PII) | Fix owner | Fixed in commit | Re-tested |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-001 | | | | | | | | | | | |
| A-002 | | | | | | | | | | | |
| A-003 | | | | | | | | | | | |

Severity guide: **Blocker** — task cannot be completed with that AT/device (fails AT-04). **Major** — completed only with workaround or significant confusion. **Minor** — friction or cosmetic.

## 7. Pass criteria for AT-04

- [ ] All Required devices (D1–D11) complete scripts 3.1–3.8 with no Blocker.
- [ ] Camera denied never produces a declined or fraud result.
- [ ] Alternative route is reachable from every applicant step on every device.
- [ ] Console scripts in §4 have no Blocker with NVDA and keyboard only.
- [ ] 5 participant sessions done, including ≥ 1 assistive-technology user; findings logged.
- [ ] Results signed off: [Owner to complete: name, date]. Record in `delivery/status.json` only with this evidence.
