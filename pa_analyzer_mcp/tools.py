"""
ScriptFlow PA Analyzer — core logic for prior authorization analysis.

Five tools live here:
1. classify_rejection           — categorize WHY a claim was rejected
2. identify_missing_documentation — list documents typically required to resolve it
3. extract_pa_evidence          — pull clinical evidence from a FHIR server
4. assess_clinical_urgency      — score the patient-safety risk of a delay (THE DOCTOR LENS)
5. draft_appeal_letter          — draft an appeal letter when a PA has been denied

These are exposed over MCP by server.py.
"""

from __future__ import annotations
import httpx
from typing import Any


# ============================================================================
# REJECTION CATEGORIES & DOCUMENTATION REQUIREMENTS
# ============================================================================

REJECTION_CATEGORIES = {
    "PA_REQUIRED": "Prior authorization is required before this medication can be dispensed.",
    "STEP_THERAPY": "Payer requires a documented trial and failure of preferred medications first.",
    "FORMULARY_EXCLUSION": "This medication is not on the payer's approved formulary.",
    "QUANTITY_LIMIT": "The quantity prescribed exceeds the payer's quantity limit.",
    "DIAGNOSIS_MISMATCH": "The diagnosis on file does not match approved indications.",
    "MISSING_PRIOR_TX": "Documentation of prior treatments tried is missing.",
    "AGE_RESTRICTION": "Patient does not meet age criteria for this medication.",
    "DENIAL": "The prior authorization request was denied. Appeal may be appropriate.",
    "UNKNOWN": "The rejection reason could not be classified from the provided information.",
}

DOC_REQUIREMENTS = {
    "PA_REQUIRED": [
        "Completed payer-specific PA form",
        "Clinical notes documenting diagnosis and medical necessity",
        "ICD-10 diagnosis codes",
        "Prescriber signature and NPI",
        "Drug name, strength, dose, quantity, and days supply",
    ],
    "STEP_THERAPY": [
        "Documentation of at least two prior medications tried (drug, dates, outcome)",
        "Reason for discontinuation of each prior agent (lack of efficacy, intolerance, contraindication)",
        "Clinical notes supporting failure of step-therapy regimen",
        "Documented contraindication to formulary alternatives, if applicable",
        "Step-therapy override request form (if applicable)",
    ],
    "FORMULARY_EXCLUSION": [
        "Formulary exception request form",
        "Letter of medical necessity from prescriber",
        "Documentation of why formulary alternatives are clinically inappropriate",
        "Published clinical evidence supporting the requested agent",
    ],
    "QUANTITY_LIMIT": [
        "Quantity-limit exception request form",
        "Dosing rationale from prescriber",
        "Supporting clinical guidelines or package insert reference",
    ],
    "DIAGNOSIS_MISMATCH": [
        "Updated diagnosis documentation",
        "ICD-10 codes matching the medication's approved indications",
        "Clinical notes supporting the diagnosis",
    ],
    "MISSING_PRIOR_TX": [
        "Complete medication history with dates",
        "Records of prior therapies including drug, dose, duration, and outcome",
    ],
    "AGE_RESTRICTION": [
        "Off-label use justification letter",
        "Published clinical evidence for this age group",
        "Documented lack of suitable age-appropriate alternatives",
    ],
    "DENIAL": [
        "Original PA submission and supporting documentation",
        "Written denial notice from payer",
        "Letter of medical necessity addressing each denial point",
        "Additional clinical evidence not previously submitted",
        "Request for peer-to-peer review",
    ],
    "UNKNOWN": [
        "Payer-specific PA form",
        "All available clinical documentation for manual review",
    ],
}


# ============================================================================
# CLINICAL URGENCY KNOWLEDGE BASE  (the "doctor lens")
# ============================================================================
#
# Each entry maps a medication or therapeutic class to a tier and a reason.
# Tier 1 = harm possible within hours/days (e.g. insulin, anticoagulants).
# Tier 2 = harm possible within 1-2 weeks (e.g. uncontrolled chronic disease).
# Tier 3 = standard, low immediate harm risk.
#
# In production this would be backed by a curated clinical knowledge graph;
# for the hackathon a reasonable rule-based table demonstrates the concept.

URGENCY_RULES = [
    # Tier 1 — life-threatening if delayed
    (["insulin", "novolog", "humalog", "lantus", "tresiba", "humulin"], 1,
     "Insulin therapy. Delays can precipitate diabetic ketoacidosis or severe hyperglycemia."),
    (["warfarin", "apixaban", "eliquis", "rivaroxaban", "xarelto", "dabigatran", "pradaxa", "edoxaban"], 1,
     "Anticoagulant. Delays risk thromboembolic events including stroke and pulmonary embolism."),
    (["levetiracetam", "keppra", "lamotrigine", "lamictal", "phenytoin", "valproate", "depakote"], 1,
     "Antiepileptic. Delays risk breakthrough seizures."),
    (["tacrolimus", "prograf", "cyclosporine", "mycophenolate", "cellcept"], 1,
     "Post-transplant immunosuppressant. Delays risk graft rejection."),
    (["methotrexate", "rituximab", "trastuzumab", "imatinib", "lenalidomide", "ibrutinib"], 1,
     "Active oncology therapy. Delays compromise treatment efficacy."),
    (["dolutegravir", "biktarvy", "tenofovir", "emtricitabine", "atripla"], 1,
     "HIV antiretroviral. Continuity is critical to prevent resistance."),
    (["nitroglycerin", "isosorbide", "metoprolol", "carvedilol"], 1,
     "Cardiac medication post-MI/HF. Delays risk decompensation."),
    (["amoxicillin", "azithromycin", "ceftriaxone", "doxycycline", "ciprofloxacin", "vancomycin"], 1,
     "Antibiotic. Delays risk progression of active infection."),
    # Tier 2 — chronic disease control at risk
    (["metformin", "glipizide", "sitagliptin", "januvia", "empagliflozin", "jardiance",
      "semaglutide", "ozempic", "wegovy", "mounjaro", "tirzepatide", "dulaglutide", "trulicity"], 2,
     "Diabetes therapy. Delays risk progression of hyperglycemia and long-term microvascular harm."),
    (["lisinopril", "losartan", "amlodipine", "hydrochlorothiazide", "atenolol"], 2,
     "Antihypertensive. Sustained interruption risks BP escalation."),
    (["albuterol", "fluticasone", "advair", "symbicort", "tiotropium", "spiriva"], 2,
     "Asthma/COPD controller or rescue. Delays risk exacerbation."),
    (["sertraline", "fluoxetine", "escitalopram", "venlafaxine", "duloxetine", "bupropion",
      "olanzapine", "risperidone", "quetiapine", "lithium"], 2,
     "Mental health medication. Discontinuation risks relapse or withdrawal."),
    (["adalimumab", "humira", "etanercept", "enbrel", "infliximab", "remicade", "ustekinumab", "stelara"], 2,
     "Specialty biologic. Lapses risk disease flare."),
    (["atorvastatin", "rosuvastatin", "simvastatin", "ezetimibe"], 2,
     "Lipid-lowering therapy. Long-term CV risk reduction is interrupted."),
]


def assess_clinical_urgency(medication: str, has_ascvd: bool = False,
                            has_active_infection: bool = False) -> dict:
    """
    Determine the clinical urgency tier of a medication delay.
    This is the doctor-lens that transforms ScriptFlow from an admin tool
    into a patient-safety tool.

    Args:
        medication: Drug name (brand or generic).
        has_ascvd: Patient has established atherosclerotic cardiovascular disease.
        has_active_infection: Patient has an active infection.

    Returns:
        dict with tier (1-3), description, sla_hours, recommended_action,
        and patient_safety_flags list.
    """
    med_lower = (medication or "").lower()
    matched_tier = 3
    matched_reason = "Standard medication. Routine PA timeline acceptable."

    for keywords, tier, reason in URGENCY_RULES:
        if any(kw in med_lower for kw in keywords):
            matched_tier = tier
            matched_reason = reason
            break

    # Comorbidity escalation: ASCVD patient on diabetes med = Tier 1
    flags: list[str] = []
    if has_ascvd and matched_tier == 2 and any(
        kw in med_lower for kw in
        ["metformin", "glipizide", "ozempic", "semaglutide", "jardiance", "empagliflozin", "trulicity"]
    ):
        matched_tier = 1
        flags.append("ESCALATED: Patient with ASCVD on diabetes therapy — guideline-directed cardio-protective regimen.")
    if has_active_infection and matched_tier > 1:
        matched_tier = 1
        flags.append("ESCALATED: Active infection — antimicrobial timing critical.")

    sla_map = {1: 4, 2: 24, 3: 72}
    action_map = {
        1: "EXPEDITE: page prescriber, request bridge supply if available, file expedited PA.",
        2: "PRIORITIZE: same-day PA submission, follow up at SLA midpoint.",
        3: "STANDARD: file PA within 24h, follow standard SLA.",
    }

    return {
        "medication": medication,
        "urgency_tier": matched_tier,
        "tier_label": {1: "CRITICAL", 2: "HIGH", 3: "STANDARD"}[matched_tier],
        "sla_hours": sla_map[matched_tier],
        "clinical_reason": matched_reason,
        "recommended_action": action_map[matched_tier],
        "patient_safety_flags": flags,
    }


# ============================================================================
# TOOL 1 — CLASSIFY REJECTION
# ============================================================================

def classify_rejection(rejection_text: str, medication: str = "") -> dict:
    """
    Classify a pharmacy rejection into a known category.
    Pattern-matches keywords; confidence is tagged so the orchestrator agent
    can decide whether to ask for clarification.
    """
    text = (rejection_text or "").lower()

    rules = [
        (["denied", "denial", "not approved", "rejected after"], "DENIAL"),
        (["pa req", "prior auth", "prior authorization", "authorization required"], "PA_REQUIRED"),
        (["step therapy", "try first", "step edit", "trial and failure", "preferred first"], "STEP_THERAPY"),
        (["not covered", "non-formulary", "off-formulary", "excluded"], "FORMULARY_EXCLUSION"),
        (["quantity", "qty limit", "day supply", "exceeds limit"], "QUANTITY_LIMIT"),
        (["diagnosis", "indication mismatch", "icd"], "DIAGNOSIS_MISMATCH"),
        (["prior therapy", "previous treatment", "history of prior"], "MISSING_PRIOR_TX"),
        (["age", "pediatric", "geriatric"], "AGE_RESTRICTION"),
    ]

    for keywords, category in rules:
        if any(kw in text for kw in keywords):
            return {
                "category": category,
                "description": REJECTION_CATEGORIES[category],
                "confidence": 0.85,
                "matched_keywords": [kw for kw in keywords if kw in text],
                "medication": medication,
            }

    return {
        "category": "UNKNOWN",
        "description": REJECTION_CATEGORIES["UNKNOWN"],
        "confidence": 0.30,
        "matched_keywords": [],
        "medication": medication,
        "note": "No keyword pattern matched. Manual review recommended.",
    }


# ============================================================================
# TOOL 2 — IDENTIFY MISSING DOCUMENTATION
# ============================================================================

def identify_missing_documentation(rejection_category: str, medication: str = "") -> dict:
    """
    Given a classified rejection category, return the documents typically required
    along with payer-agnostic submission guidance.
    """
    category = (rejection_category or "UNKNOWN").upper()
    if category not in DOC_REQUIREMENTS:
        category = "UNKNOWN"

    return {
        "rejection_category": category,
        "required_documents": DOC_REQUIREMENTS[category],
        "submission_guidance": (
            f"For {medication or 'this medication'}, submit the documents listed above via the payer's "
            f"electronic PA portal where available; fallback to fax. Standard turnaround is 24 to 72 hours; "
            f"request expedited review when clinical urgency justifies it."
        ),
    }


# ============================================================================
# TOOL 3 — EXTRACT PA EVIDENCE FROM FHIR
# ============================================================================

def extract_pa_evidence(
    fhir_base_url: str,
    fhir_access_token: str,
    patient_id: str,
    medication: str,
) -> dict:
    """
    Pull structured clinical evidence from a FHIR server to support a PA request.
    Queries Conditions, MedicationRequests, and recent Observations for the patient.
    """
    headers = {"Accept": "application/fhir+json"}
    if fhir_access_token:
        headers["Authorization"] = f"Bearer {fhir_access_token}"

    evidence: dict[str, Any] = {
        "patient_id": patient_id,
        "medication": medication,
        "conditions": [],
        "prior_medications": [],
        "recent_observations": [],
        "errors": [],
    }

    # ---- Conditions ----
    try:
        r = httpx.get(
            f"{fhir_base_url}/Condition",
            params={"patient": patient_id, "_count": 25},
            headers=headers, timeout=15,
        )
        if r.status_code == 200:
            for entry in r.json().get("entry", []):
                res = entry.get("resource", {}) or {}
                code = res.get("code", {}) or {}
                first_coding = (code.get("coding") or [{}])[0]
                evidence["conditions"].append({
                    "display": code.get("text") or first_coding.get("display", "Unknown"),
                    "code": first_coding.get("code", ""),
                    "system": first_coding.get("system", ""),
                    "clinical_status": (((res.get("clinicalStatus") or {}).get("coding") or [{}])[0]).get("code", ""),
                })
        else:
            evidence["errors"].append(f"Condition fetch returned {r.status_code}")
    except Exception as e:
        evidence["errors"].append(f"Condition fetch failed: {e}")

    # ---- Prior medications ----
    try:
        r = httpx.get(
            f"{fhir_base_url}/MedicationRequest",
            params={"patient": patient_id, "_count": 25, "_sort": "-authored"},
            headers=headers, timeout=15,
        )
        if r.status_code == 200:
            for entry in r.json().get("entry", []):
                res = entry.get("resource", {}) or {}
                med = res.get("medicationCodeableConcept", {}) or {}
                first_coding = (med.get("coding") or [{}])[0]
                evidence["prior_medications"].append({
                    "display": med.get("text") or first_coding.get("display", "Unknown"),
                    "status": res.get("status", ""),
                    "authored_on": res.get("authoredOn", ""),
                })
        else:
            evidence["errors"].append(f"MedicationRequest fetch returned {r.status_code}")
    except Exception as e:
        evidence["errors"].append(f"MedicationRequest fetch failed: {e}")

    # ---- Observations (labs, vitals) ----
    try:
        r = httpx.get(
            f"{fhir_base_url}/Observation",
            params={"patient": patient_id, "_count": 15, "_sort": "-date"},
            headers=headers, timeout=15,
        )
        if r.status_code == 200:
            for entry in r.json().get("entry", []):
                res = entry.get("resource", {}) or {}
                code = res.get("code", {}) or {}
                first_coding = (code.get("coding") or [{}])[0]
                value = res.get("valueQuantity", {}) or {}
                evidence["recent_observations"].append({
                    "display": code.get("text") or first_coding.get("display", "Unknown"),
                    "value": f"{value.get('value', '')} {value.get('unit', '')}".strip(),
                    "date": res.get("effectiveDateTime", ""),
                })
        else:
            evidence["errors"].append(f"Observation fetch returned {r.status_code}")
    except Exception as e:
        evidence["errors"].append(f"Observation fetch failed: {e}")

    evidence["summary"] = (
        f"Found {len(evidence['conditions'])} conditions, "
        f"{len(evidence['prior_medications'])} prior medications, "
        f"{len(evidence['recent_observations'])} recent observations."
    )
    return evidence


# ============================================================================
# TOOL 5 — DRAFT APPEAL LETTER
# ============================================================================

def draft_appeal_letter(
    medication: str,
    diagnosis: str,
    denial_reason: str,
    clinical_justification: str,
    prior_therapies: str = "",
    prescriber_name: str = "[Prescriber Name]",
    patient_id: str = "[Patient ID]",
) -> dict:
    """
    Generate a payer appeal letter from structured inputs.
    The orchestrator agent fills the inputs from gathered evidence;
    this tool produces the formatted letter the pharmacist will sign.
    """
    letter = f"""
[Pharmacy Letterhead]

[Date]

Attention: Appeals Department
[Payer Name]

RE: Formal Appeal of Prior Authorization Denial
Patient ID: {patient_id}
Medication: {medication}
Diagnosis: {diagnosis}
Original Denial Reason: {denial_reason}

To Whom It May Concern,

I am writing to formally appeal the denial of prior authorization for the above-named patient
for {medication}, prescribed for {diagnosis}.

CLINICAL JUSTIFICATION:
{clinical_justification}

PRIOR THERAPY HISTORY:
{prior_therapies or "See attached medication history."}

Based on the clinical evidence and current treatment guidelines, we believe {medication} is
medically necessary for this patient. The denial reason cited ("{denial_reason}") does not
adequately consider the patient's clinical context as documented above.

We respectfully request that this appeal be reviewed by a licensed practitioner with relevant
specialty expertise. We are also requesting a peer-to-peer review with the prescribing
physician at the payer's earliest convenience.

Supporting documentation is attached. Please contact our pharmacy at [Pharmacy Phone] with
any questions or to schedule the peer-to-peer review.

Sincerely,

{prescriber_name}
[Prescriber Credentials and NPI]

— Letter prepared by ScriptFlow AI assistant. Pharmacist review and prescriber signature required prior to submission. —
""".strip()

    return {
        "appeal_letter_draft": letter,
        "review_required": True,
        "next_steps": [
            "Pharmacist reviews and edits the draft for clinical accuracy.",
            "Prescriber signs the letter.",
            "Submit via the payer's appeals channel within the appeal deadline.",
            "Request a peer-to-peer review.",
        ],
    }
