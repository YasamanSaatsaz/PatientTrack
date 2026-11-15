import re
from datetime import datetime
from typing import Optional

from models import PatientReport, SymptomObservation


# ---------------------------------------------------------------------
# 1. SYMPTOM VOCABULARY
# Map common patient phrases to a consistent symptom name.
# ---------------------------------------------------------------------

SYMPTOM_PATTERNS = {
    "dry lips": [
        r"\bdry lips?\b",
        r"\bchapped lips?\b",
        # Also recognize descriptions where the adjective comes after "lips",
        # e.g. "my lips have been very dry".
        r"\blips?\b(?:\W+\w+){0,5}\W+dry\b",
    ],
    "dry skin": [
        r"\bdry skin\b",
        r"\bskin feels dry\b",
    ],
    "skin irritation": [
        r"\bskin irritation\b",
        r"\birritated skin\b",
        r"\bskin is irritated\b",
        # Recognize natural wording such as "my skin is a little irritated".
        r"\bskin\b(?:\W+\w+){0,4}\W+irritat(?:ed|ion|ing)\b",
    ],
    "facial redness": [
        r"\bfacial redness\b",
        r"\bredness on (?:my )?face\b",
        r"\bface is red\b",
        r"\bred face\b",
    ],
    "skin redness": [
        r"\bskin redness\b",
        r"\bred skin\b",
        r"\bskin is red\b",
    ],
    "skin sensitivity": [
        r"\bskin sensitivity\b",
        r"\bsensitive skin\b",
        r"\bskin feels sensitive\b",
    ],
    "itching": [
        r"\bitch(?:y|ing)?\b",
        r"\bitchiness\b",
    ],
    "rash": [
        r"\brashes?\b",
    ],
    "swelling": [
        r"\bswell(?:ing|ed)?\b",
        r"\bpuffiness\b",
    ],
    "peeling skin": [
        r"\bpeeling skin\b",
        r"\bskin is peeling\b",
        r"\bpeeling\b",
    ],
    "skin pain": [
        r"\bskin pain\b",
        r"\bskin hurts\b",
        r"\bpainful skin\b",
    ],
}


# ---------------------------------------------------------------------
# 2. SIMPLE LANGUAGE CUES
# ---------------------------------------------------------------------

SEVERITY_CUES = {
    1: [
        "very mild",
        "barely noticeable",
        "slight",
        "slightly",
        "a little",
        "mildly",
        "mild",
    ],
    2: [
        "mild discomfort",
        "some discomfort",
        "noticeable",
    ],
    3: [
        "moderate",
        "uncomfortable",
        "bothersome",
    ],
    4: [
        "very uncomfortable",
        "quite severe",
        "very painful",
        "severe",
        "bad",
    ],
    5: [
        "extremely uncomfortable",
        "unbearable",
        "worst",
        "extreme",
    ],
}

MEDICATION_NAMES = [
    "isotretinoin",
    "tretinoin",
    "benzoyl peroxide",
    "topical treatment",
    "antibiotic",
]


# ---------------------------------------------------------------------
# 3. EXTRACTION HELPERS
# ---------------------------------------------------------------------

def find_symptoms(text: str) -> list[str]:
    """Return unique normalized symptoms found in the report."""
    found = []

    for symptom_name, patterns in SYMPTOM_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            found.append(symptom_name)

    return found


def extract_severity(text: str) -> tuple[Optional[int], Optional[str], bool]:
    """
    Extract an explicit 1–5 score or a cautious language-based estimate.

    Returns:
        (severity_score, severity_description, needs_review)
    """
    lower_text = text.lower()

    numeric_scores = re.findall(
        r"\b([1-5])\s*(?:/|out of)\s*5\b",
        lower_text,
        flags=re.IGNORECASE,
    )
    distinct_numeric_scores = {int(score) for score in numeric_scores}

    if len(distinct_numeric_scores) > 1:
        return None, "Conflicting severity scores in report", True

    # Match whole phrases. If a longer phrase contains a shorter cue
    # (for example, "very uncomfortable" contains "uncomfortable"),
    # keep the longer, more specific phrase.
    matched_phrases = []
    for level, phrases in SEVERITY_CUES.items():
        for phrase in phrases:
            if re.search(rf"\b{re.escape(phrase)}\b", lower_text):
                matched_phrases.append((level, phrase))

    specific_matches = [
        item for item in matched_phrases
        if not any(
            item[1] != other[1] and item[1] in other[1]
            for other in matched_phrases
        )
    ]
    language_levels = {level for level, _ in specific_matches}

    if len(distinct_numeric_scores) == 1:
        score = distinct_numeric_scores.pop()
        if language_levels and score not in language_levels:
            return None, "Numeric score conflicts with severity wording", True
        return score, f"Patient-reported severity: {score}/5", False

    if len(language_levels) > 1:
        return None, "Conflicting severity language; score not inferred", True

    if len(language_levels) == 1:
        level = language_levels.pop()
        matched_phrase = next(
            phrase for found_level, phrase in specific_matches
            if found_level == level
        )
        return level, f"Language-based estimate: {matched_phrase}", False

    return None, None, True


def extract_frequency(text: str) -> tuple[Optional[int], Optional[str]]:
    """Extract a simple occurrence count and the stated time period."""
    lower_text = text.lower()

    number_words = {
        "once": 1,
        "twice": 2,
        "three times": 3,
        "four times": 4,
        "five times": 5,
    }

    count = None

    digit_match = re.search(
        r"\b(\d+)\s+times?\b",
        lower_text,
    )
    if digit_match:
        count = int(digit_match.group(1))
    else:
        for phrase, value in number_words.items():
            if re.search(rf"\b{re.escape(phrase)}\b", lower_text):
                count = value
                break

    period = None
    period_patterns = [
        (r"\btoday\b", "today"),
        (r"\byesterday\b", "yesterday"),
        (r"\bthis morning\b", "this morning"),
        (r"\bthis week\b", "this week"),
        (r"\blast night\b", "last night"),
        (r"\bfor the past (\d+) days?\b", None),
        (r"\bfor (\d+) days?\b", None),
    ]

    for pattern, fixed_period in period_patterns:
        match = re.search(pattern, lower_text)
        if match:
            if fixed_period:
                period = fixed_period
            else:
                period = f"{match.group(1)} days"
            break

    return count, period


def extract_medication_context(text: str) -> Optional[str]:
    """Find a medication or treatment name explicitly mentioned in the report."""
    lower_text = text.lower()

    for medication in MEDICATION_NAMES:
        if medication in lower_text:
            return medication.title()

    return None


def detect_suspected_medication_link(
    text: str,
    medication_context: Optional[str],
) -> Optional[bool]:
    """
    Identify whether the patient explicitly suggests a medication relationship.

    Mentioning a medication alone is not treated as evidence of a link.
    """
    if medication_context is None:
        return None

    lower_text = text.lower()

    negative_phrases = [
        "not related to",
        "unrelated to",
        "not caused by",
        "don't think",
        "do not think",
    ]
    if any(phrase in lower_text for phrase in negative_phrases):
        return False

    link_phrases = [
        "after starting",
        "since starting",
        "after taking",
        "since taking",
        "because of",
        "caused by",
        "might be from",
        "may be from",
        "think it is from",
    ]

    if any(phrase in lower_text for phrase in link_phrases):
        return True

    return None


# ---------------------------------------------------------------------
# 4. MAIN PARSER
# ---------------------------------------------------------------------

def parse_patient_report(
    patient_id: str,
    raw_text: str,
    submitted_at: Optional[datetime] = None,
) -> PatientReport:
    """
    Convert a free-text dermatology report into a validated PatientReport.

    The original text is preserved. Unclear or conflicting information is
    left unknown and flagged for review rather than guessed.

    Args:
        patient_id: Existing synthetic patient ID.
        raw_text: Patient's original report.
        submitted_at: Optional report timestamp; defaults to now.

    Returns:
        A validated PatientReport instance.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("The patient report cannot be empty.")

    report_time = submitted_at or datetime.now()
    cleaned_text = raw_text.strip()

    symptoms = find_symptoms(cleaned_text)
    severity, severity_description, severity_needs_review = (
        extract_severity(cleaned_text)
    )
    frequency_count, frequency_period = extract_frequency(cleaned_text)
    medication_context = extract_medication_context(cleaned_text)
    suspected_medication_link = detect_suspected_medication_link(
        cleaned_text,
        medication_context,
    )

    observations = []

    for symptom in symptoms:
        review_reasons = []

        if severity_needs_review:
            review_reasons.append("Severity is missing or ambiguous")

        if frequency_count is None:
            review_reasons.append("Frequency count was not identified")

        # A medication mention is not assumed to be causal.
        if medication_context and suspected_medication_link is None:
            pass

        needs_review = bool(review_reasons)

        # Confidence is a simple rule-based indicator, not a calibrated
        # probability. It is lower when key fields are uncertain.
        confidence = 1.0
        if severity is None:
            confidence -= 0.25
        if frequency_count is None:
            confidence -= 0.15
        if not medication_context:
            confidence -= 0.05

        observation = SymptomObservation(
            symptom_name=symptom,
            severity=severity,
            severity_description=severity_description,
            frequency_count=frequency_count,
            frequency_period=frequency_period,
            reported_at=report_time,
            medication_context=medication_context,
            patient_suspected_medication_link=suspected_medication_link,
            extraction_confidence=max(0.0, confidence),
            needs_review=needs_review,
            review_reason="; ".join(review_reasons) or None,
        )
        observations.append(observation)

    # If no supported symptom phrase was found, preserve the report and
    # request review instead of inventing a symptom.
    if not observations:
        requires_review = True
        review_status = "pending"
    else:
        requires_review = any(item.needs_review for item in observations)
        review_status = "pending" if requires_review else "not_required"

    return PatientReport(
        patient_id=patient_id,
        submitted_at=report_time,
        raw_text=cleaned_text,
        observations=observations,
        extraction_method="rule_based",
        requires_review=requires_review,
        review_status=review_status,
    )


# ---------------------------------------------------------------------
# 5. BASIC TESTS
# ---------------------------------------------------------------------

if __name__ == "__main__":
    examples = [
        (
            "P001",
            "My lips have been very dry for the past 3 days. "
            "It happened twice today after starting isotretinoin.",
        ),
        (
            "P002",
            "My skin is a little irritated today.",
        ),
        (
            "P003",
            "My face is red and very uncomfortable. "
            "I am not sure whether it is related to my topical treatment.",
        ),
        (
            "P004",
            "My skin feels mildly irritated but also extremely uncomfortable.",
        ),
        (
            "P005",
            "I have a problem with my skin but I cannot describe it clearly.",
        ),
    ]

    for patient_id, report_text in examples:
        parsed_report = parse_patient_report(
            patient_id=patient_id,
            raw_text=report_text,
        )

        print("\n" + "=" * 70)
        print(f"Patient: {patient_id}")
        print(f"Original report: {parsed_report.raw_text}")
        print(f"Review required: {parsed_report.requires_review}")

        for observation in parsed_report.observations:
            print(observation.model_dump())

        if not parsed_report.observations:
            print("No supported symptom was extracted; manual review required.")
