# ScriptFlow Demo Prompts

These are the exact prompts to paste into Prompt Opinion during your demo recording.
They produce a clean, repeatable demo that hits all 5T deliverables and shows the patient-safety angle.

## Setup before recording

1. In Prompt Opinion → patients tab → import the synthetic patient "Maria Garcia (demo-patient-001)" or upload her clinical note from `sample_data/patient_maria_garcia_clinical_note.md`.
2. Optionally upload `sample_data/pharmacy_pa_sop.md` to a workspace collection so a follow-up demo can show grounded answers.
3. Connect the published ScriptFlow A2A agent to the workspace.
4. Connect the published PA Analyzer MCP server.

---

## DEMO PROMPT 1 — The headline case (use this in the video)

```
Patient: Maria Garcia (demo-patient-001) — 63yo with type 2 diabetes, status post NSTEMI
2023 with stent (established ASCVD), HbA1c 8.7% on max metformin + glipizide.

Pharmacy received this claim rejection from Aetna Better Health:

  "Reject Code 75 — PRIOR AUTHORIZATION REQUIRED.
   Subcode 75-A — STEP THERAPY EDIT — TRY PREFERRED FIRST.
   Plan requires documented trial and failure of (1) metformin AND (2) at least one
   other oral antidiabetic agent before approving GLP-1 RA therapy. Submit clinical
   documentation of medical necessity, prior therapy history, current A1c, and
   ICD-10 diagnosis codes. Step therapy override may be requested with documented
   contraindication or established ASCVD."

The prescribed medication is semaglutide (Ozempic) 0.25/0.5 mg pen, 1 pen,
28-day supply, prescribed by Dr. James Liu.

Please resolve this case.
```

**What ScriptFlow should do:**
1. triage_agent → STEP_THERAPY, Urgency Tier 2 (escalated to Tier 1 because of ASCVD + GLP-1 RA)
2. evidence_agent → pulls T2DM diagnosis, prior metformin/glipizide trials, A1c 8.7%, ASCVD history
3. planner_agent → 6-step plan, owners, time estimates
4. form_filler_agent → step-therapy override request citing ASCVD as the override criterion

**The win:** ScriptFlow correctly flags that this patient qualifies for a step-therapy OVERRIDE under most plan policies because she has established ASCVD — the GLP-1 is preferred therapy per ADA/ESC guidelines for T2DM + ASCVD. A naive PA tool would just collect the standard step-therapy docs; ScriptFlow recognizes the override path and saves days.

---

## DEMO PROMPT 2 — The denial / appeal scenario

```
Patient demo-patient-002 was prescribed adalimumab (Humira) for moderate-to-severe
plaque psoriasis (ICD-10 L40.0). The PA was denied. Denial letter says:

  "Denied. Patient has not documented trial and failure of two conventional
   systemic therapies. Plan considers methotrexate and cyclosporine first-line."

Patient HAS tried methotrexate for 14 weeks (discontinued for elevated transaminases)
and cyclosporine for 8 weeks (discontinued for hypertension).

Draft an appeal.
```

**What ScriptFlow should do:**
- Classify as DENIAL
- Pull evidence (or accept inline evidence)
- Draft an appeal letter via draft_appeal_letter
- Output the letter in the Template section, ready for prescriber signature
- Recommend peer-to-peer review

---

## DEMO PROMPT 3 — The Tier 1 patient-safety case (powerful for video)

```
Patient demo-patient-003 with non-valvular atrial fibrillation and CHA2DS2-VASc score 4.
Was on warfarin, switched 90 days ago to apixaban (Eliquis) per cardiology.

Pharmacy received:
  "Reject 70 — NDC NOT COVERED. Member benefit requires PA for brand apixaban."

Patient is at risk of stroke if anticoagulation lapses. What do we do?
```

**What ScriptFlow should do:**
- Triage tier = 1 CRITICAL (anticoagulant)
- Patient Safety Banner at top of output: "🚨 Tier 1 — anticoagulation lapse risk"
- Recommend bridge supply per state emergency-supply rules
- Expedited PA channel
- Task SLA: 4 hours
- This is the most impressive demo for showing the "doctor lens"

---

## DEMO PROMPT 4 — A2A consultation (show multi-agent collaboration)

After the main run, demonstrate that ScriptFlow can be CONSULTED by another agent:

In the general chat agent in Prompt Opinion, run:

```
I want to consult with ScriptFlow about an Ozempic rejection for our diabetic patient
with prior heart attack. Get me the workflow plan.
```

This shows judges your agent participates in the multi-agent ecosystem, not just standalone.
