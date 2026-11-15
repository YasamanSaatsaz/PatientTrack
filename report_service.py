"""
report_service.py

Connects PatientTrack's rule-based parser to its SQLite database.

This module provides one application-level function for processing and saving
a patient-submitted free-text symptom report.
"""

from datetime import datetime
from typing import Optional

from database import add_report, get_patients
from parser import parse_patient_report


def process_and_save_report(
    patient_id: str,
    raw_text: str,
    submitted_at: Optional[datetime] = None,
) -> dict:
    """
    Parse a patient's free-text report and save it with its observations.

    The patient must already exist in the database. The original report text,
    extraction results, and review flags are saved together through
    database.add_report(), which stores the report and observations in one
    database transaction.

    Args:
        patient_id: ID of an existing patient.
        raw_text: Original text submitted by the patient.
        submitted_at: Optional report timestamp; defaults to the current time.

    Returns:
        A dictionary containing the new database report ID, the parsed report,
        and a compact status summary.

    Raises:
        ValueError: If the patient does not exist or the report text is empty.
    """
    if not patient_id or not patient_id.strip():
        raise ValueError("A patient ID is required.")

    if not raw_text or not raw_text.strip():
        raise ValueError("The patient report cannot be empty.")

    known_patient_ids = {
        patient["patient_id"]
        for patient in get_patients()
    }

    if patient_id not in known_patient_ids:
        raise ValueError(
            f"Patient '{patient_id}' was not found. "
            "Choose an existing patient before submitting a report."
        )

    parsed_report = parse_patient_report(
        patient_id=patient_id,
        raw_text=raw_text,
        submitted_at=submitted_at,
    )

    # add_report saves the parent report and all extracted observations
    # together. If an insert fails, the database transaction is rolled back.
    report_id = add_report(parsed_report)

    return {
        "report_id": report_id,
        "patient_id": parsed_report.patient_id,
        "submitted_at": parsed_report.submitted_at,
        "raw_text": parsed_report.raw_text,
        "observation_count": len(parsed_report.observations),
        "requires_review": parsed_report.requires_review,
        "review_status": parsed_report.review_status,
        "observations": [
            observation.model_dump()
            for observation in parsed_report.observations
        ],
    }
