# ScriptFlow — 3-Minute Demo Video Script

Total runtime target: 2:50. Hard cutoff: 3:00.

**Recording setup**
- Mac: QuickTime "New Screen Recording" or Loom
- Resolution: 1080p
- Audio: dedicated headset mic, not built-in
- Browser: full screen, hide bookmarks bar
- Have Prompt Opinion + sample patient + ScriptFlow already loaded
- Have ngrok already running so URLs in DevTools are visible
- Subtitles: turn on auto-captions (YouTube does this)

---

## SCRIPT (read aloud, time-coded)

### [0:00 – 0:18] HOOK — patient-safety frame
> "94 percent of patients face delays from prior authorization. 78 percent abandon treatment because of it. 19 percent of pharmacists report that a PA delay caused a serious adverse event. The hardest part of healthcare AI isn't intelligence — it's the last mile."
>
> *[Show a single slide: "Prior Auth: 94% delays · 78% abandonment · 19% adverse events"]*

### [0:18 – 0:35] THE FIX — what ScriptFlow is
> "ScriptFlow is a clinically-aware AI orchestrator. It takes a pharmacy claim rejection and produces a complete handoff package — pharmacist briefing, case snapshot, pre-filled PA form, simulated submission, and a follow-up task — in under a minute. It's an A2A agent, plus a custom MCP I built, both published on the Prompt Opinion marketplace."
>
> *[Cursor moves to the Prompt Opinion marketplace tab. Briefly highlight ScriptFlow and PA Analyzer listings.]*

### [0:35 – 1:00] SETUP — patient context
> "Here's our synthetic patient: Maria Garcia, 63, type 2 diabetes, prior heart attack, A1c 8.7. Her doctor prescribed Ozempic. Her insurance just denied it for step therapy."
>
> *[Click into Maria Garcia in PO. Show her uploaded clinical note. Then paste the rejection notice.]*

### [1:00 – 2:30] THE LIVE RUN — the meat
> "I'm asking ScriptFlow to resolve the case."
>
> *[Paste DEMO PROMPT 1 from demo_prompts.md. Click run.]*
>
> *[As the agent runs, narrate while pointing at the screen:]*
>
> "First, the triage agent classifies the rejection as step therapy — and here's the doctor lens — it scores patient-safety urgency. Because Maria has established cardiovascular disease and we're trying to start a GLP-1, ScriptFlow escalates this to Tier 1. The cardiologist already knows this medication is preferred for her. Most PA tools wouldn't catch that.
>
> Now the evidence agent is pulling her FHIR chart — her T2DM diagnosis, her prior metformin and glipizide, her A1c, and critically her ASCVD history. *[Point to the live evidence output.]*
>
> The planner builds the workflow.
>
> The form filler drafts a step therapy override request — not a regular PA — because ASCVD is the override criterion. *[Highlight the override section in the form.]*
>
> And here's the 5T output: Talk for the pharmacist *[point]*, Table for the snapshot *[point]*, Template for the form *[point]*, Transaction for submission *[point]*, Task for follow-up *[point]*. Notice the patient-safety banner at the top — Tier 1 cases get bridge-supply recommendations because waiting 72 hours could harm this patient."

### [2:30 – 2:50] STANDARDS + IMPACT
> "Behind the scenes, ScriptFlow uses MCP for tools, A2A for the agent, FHIR for clinical data, and SHARP context propagation for credentials. *[Briefly flash DevTools showing X-FHIR-Server-URL, X-Patient-ID headers.]*
>
> Time from rejection to submitted PA — under 90 seconds. The pharmacy team's job becomes review and approve, not chase paperwork. That's how we move from 78 percent abandonment toward zero."

### [2:50 – 3:00] CLOSE
> "ScriptFlow — published, standards-compliant, and synthetic-data-only. Thank you."

---

## What MUST be on screen for judges (Stage-1 verification)

- [x] Prompt Opinion marketplace listing visible
- [x] ScriptFlow agent invoked from inside the platform (not localhost)
- [x] PA Analyzer MCP visible in the workspace tools
- [x] All 5 T sections labeled in the output
- [x] Patient-safety urgency banner visible
- [x] SHARP context headers visible at least once (DevTools/logs)
- [x] "Synthetic data" disclaimer somewhere on screen
- [x] No real names, no real NPIs, no real insurance IDs

---

## Two takes minimum

Record at least two complete takes. Pick the cleanest. Don't try to edit if the first is rough — re-record. The 3-minute hard cap means every second counts.

## Upload

YouTube → Unlisted → paste the link into Devpost.
