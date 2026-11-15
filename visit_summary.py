from datetime import date, datetime
from pathlib import Path

from database import (
    get_connection,
    get_patients,
    get_patient_observations,
    get_patient_reports,
)
from analytics import get_patient_analytics_summary


def _format_date(value):
    """Format an ISO date or datetime value for display."""
    
    if not value:
        return "Not recorded"

    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.strftime("%b %d, %Y")
    except ValueError:
        try:
            parsed_date = date.fromisoformat(str(value))
            return parsed_date.strftime("%b %d, %Y")
        except ValueError:
            return str(value)


def _get_patient_record(patient_id):
    """Retrieve the basic patient record."""
    
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT patient_id, name, age, treatment_start_date
            FROM patients
            WHERE patient_id = ?
            """,
            (patient_id,),
        ).fetchone()

    return dict(row) if row else None


def _get_patient_medications(patient_id):
    """Retrieve medication records for one patient."""
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT medication_name, dosage, start_date, end_date
            FROM medications
            WHERE patient_id = ?
            ORDER BY start_date ASC
            """,
            (patient_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def _get_patient_reminders(patient_id):
    """Retrieve bloodwork reminders for one patient."""
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT reminder_date, reminder_type, status, notes
            FROM bloodwork_reminders
            WHERE patient_id = ?
            ORDER BY reminder_date ASC
            """,
            (patient_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def _get_patient_photos(patient_id):
    """Retrieve progress-photo metadata, not the image files themselves."""
    
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT photo_date, photo_reference, notes
            FROM progress_photos
            WHERE patient_id = ?
            ORDER BY photo_date DESC
            """,
            (patient_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def generate_pre_visit_summary(patient_id, output_path=None):
    """
    Generate a pre-visit summary for one patient.

    Args:
        patient_id: The ID of the patient to summarize.
        output_path: Optional file path. If provided, the summary is saved
            as a Markdown (.md) file.

    Returns:
        The completed summary as a Markdown-formatted string.

    Raises:
        ValueError: If the patient ID is not present in the database.
    """
    
    patient = _get_patient_record(patient_id)

    if patient is None:
        raise ValueError(
            f"No patient found with ID '{patient_id}'. "
            "Check the patient ID and try again."
        )

    observations = get_patient_observations(patient_id)
    reports = get_patient_reports(patient_id)
    medications = _get_patient_medications(patient_id)
    reminders = _get_patient_reminders(patient_id)
    photos = _get_patient_photos(patient_id)
    analytics = get_patient_analytics_summary(patient_id)

    generated_at = datetime.now().strftime("%b %d, %Y at %I:%M %p")

    lines = [
        f"# Pre-Visit Summary: {patient['name']}",
        "",
        f"**Patient ID:** {patient['patient_id']}  ",
        f"**Age:** {patient['age']}  ",
        f"**Treatment start date:** "
        f"{_format_date(patient['treatment_start_date'])}  ",
        f"**Summary generated:** {generated_at}",
        "",
        "> **Prototype notice:** This summary is generated from synthetic "
        "demonstration data. It is an organizational aid, not a diagnosis, "
        "treatment recommendation, or substitute for clinician review.",
        "",
        "## 1. Overview",
        "",
        f"- Symptom observations recorded: {analytics['total_observations']}",
        f"- Unique symptoms recorded: {analytics['unique_symptoms']}",
        f"- Average reported severity: "
        f"{analytics['average_reported_severity'] if analytics['average_reported_severity'] is not None else 'Not available'} "
        f"(1–5 scale)",
        f"- High-severity observations (4–5): "
        f"{analytics['high_severity_observations']}",
        "",
        "## 2. Symptom History and Trends",
        "",
    ]

    if not observations:
        lines.append("No symptom observations are currently recorded.")
    else:
        for item in observations:
            symptom = item.get("symptom_name") or "Unspecified symptom"
            severity = (
                str(item["severity"])
                if item.get("severity") is not None
                else "Not recorded"
            )
            lines.extend([
                f"### {symptom.title()}",
                "",
                f"- Reported: {_format_date(item.get('reported_at'))}",
                f"- Severity: {severity}/5"
                if severity != "Not recorded"
                else "- Severity: Not recorded",
                f"- Severity description: "
                f"{item.get('severity_description') or 'Not recorded'}",
                f"- Reported frequency: "
                f"{item.get('frequency_count') if item.get('frequency_count') is not None else 'Not recorded'} "
                f"{item.get('frequency_period') or ''}".rstrip(),
                f"- Medication context: "
                f"{item.get('medication_context') or 'Not mentioned'}",
            ])

            suspected_link = item.get("patient_suspected_medication_link")
            if suspected_link is True or suspected_link == 1:
                link_text = "Patient suspects a relationship"
            elif suspected_link is False or suspected_link == 0:
                link_text = "Patient did not report a suspected relationship"
            else:
                link_text = "Relationship not specified or uncertain"

            lines.append(f"- Medication relationship: {link_text}")

            if item.get("needs_review"):
                lines.append(
                    f"- **Review required:** "
                    f"{item.get('review_reason') or 'Reason not specified'}"
                )

            raw_text = item.get("raw_text")
            if raw_text:
                lines.extend([
                    "",
                    f"> Patient's original wording: “{raw_text}”",
                ])

            lines.append("")

    lines.extend([
        "### Trend Summary",
        "",
    ])

    if not analytics["trends"]:
        lines.append("No symptom trends can be calculated.")
    else:
        for trend in analytics["trends"]:
            first = (
                trend["first_severity"]
                if trend["first_severity"] is not None
                else "Not recorded"
            )
            latest = (
                trend["latest_severity"]
                if trend["latest_severity"] is not None
                else "Not recorded"
            )
            lines.append(
                f"- **{trend['symptom_name'].title()}:** "
                f"{trend['trend'].replace('_', ' ')} "
                f"(first: {first}; latest: {latest}; "
                f"observations: {trend['observation_count']})"
            )

    lines.extend(["", "## 3. Medication Records", ""])

    if not medications:
        lines.append("No medication records are currently stored.")
    else:
        for medication in medications:
            medication_line = (
                f"- **{medication['medication_name']}**"
                f" — {medication.get('dosage') or 'Dosage not recorded'}"
                f"; started {_format_date(medication.get('start_date'))}"
            )
            if medication.get("end_date"):
                medication_line += (
                    f"; ended {_format_date(medication['end_date'])}"
                )
            else:
                medication_line += "; no end date recorded"
            lines.append(medication_line)

    lines.extend(["", "## 4. Bloodwork Reminders", ""])

    if not reminders:
        lines.append("No bloodwork reminders are currently recorded.")
    else:
        for reminder in reminders:
            reminder_line = (
                f"- **{reminder['reminder_type']}** — "
                f"{_format_date(reminder['reminder_date'])}; "
                f"status: {reminder['status']}"
            )
            if reminder.get("notes"):
                reminder_line += f"; notes: {reminder['notes']}"
            lines.append(reminder_line)

    lines.extend(["", "## 5. Progress Photo Records", ""])

    if not photos:
        lines.append("No progress-photo records are currently stored.")
    else:
        lines.append(
            "The following entries are photo metadata references; "
            "the image files are not embedded in this summary."
        )
        for photo in photos:
            photo_line = f"- {_format_date(photo['photo_date'])}"
            if photo.get("photo_reference"):
                photo_line += f" — reference: {photo['photo_reference']}"
            if photo.get("notes"):
                photo_line += f" — {photo['notes']}"
            lines.append(photo_line)

    review_items = [
        item for item in observations if item.get("needs_review")
    ]
    report_review_items = [
        report for report in reports
        if report.get("requires_review")
        or report.get("review_status") == "pending"
    ]

    lines.extend([
        "",
        "## 6. Items Requiring Review",
        "",
    ])

    if not review_items and not report_review_items:
        lines.append("No report-level or observation-level review flags are recorded.")
    else:
        if report_review_items:
            lines.append(f"{len(report_review_items)} report(s) require review:")
            for report in report_review_items:
                lines.append(
                    f"- Report #{report['report_id']} — "
                    f"status: {report.get('review_status', 'not specified')}"
                )
        if review_items:
            lines.append(f"{len(review_items)} observation(s) are flagged for review:")
            for item in review_items:
                lines.append(
                    f"- {item.get('symptom_name', 'Unspecified symptom')}: "
                    f"{item.get('review_reason') or 'Reason not specified'}"
                )

    lines.extend([
        "",
        "---",
        "",
        "*This summary organizes recorded patient-reported information. "
        "Trend labels describe changes in recorded numeric severity only. "
        "They are not clinical assessments or alerts.*",
        "",
    ])

    summary = "\n".join(lines)

    if output_path is not None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(summary, encoding="utf-8")

    return summary


if __name__ == "__main__":
    patients = get_patients()

    if not patients:
        print(
            "No patients found. Run `python sample_data.py` "
            "to initialize the database and add synthetic records."
        )
    else:
        # Generate a sample summary for the first patient in the database.
        selected_patient = patients[0]
        summary = generate_pre_visit_summary(
            patient_id=selected_patient["patient_id"],
            output_path=(
                Path("summaries")
                / f"{selected_patient['patient_id']}_pre_visit_summary.md"
            ),
        )

        print(summary)
        print(
            "\nSummary saved to: "
            f"summaries/{selected_patient['patient_id']}_pre_visit_summary.md"
        )
