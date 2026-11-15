from database import get_connection


def get_patient_overview():
    """
    Retrieve each patient and their most recent symptom report.

    Returns:
        A list of dictionaries containing patient and symptom information.
    """

    query = """
        SELECT
            p.patient_id,
            p.name,
            p.age,
            o.symptom_name,
            o.severity,
            o.reported_at

        FROM patients AS p

        LEFT JOIN observations AS o
            ON o.observation_id = (
                SELECT o2.observation_id
                FROM observations AS o2
                JOIN reports AS r2
                    ON o2.report_id = r2.report_id
                WHERE r2.patient_id = p.patient_id
                ORDER BY o2.reported_at DESC
                LIMIT 1
            )

        ORDER BY p.name;
    """

    # open a connection and get each patient and their most recent symptom report
    with get_connection() as connection:
        results = connection.execute(query).fetchall()

    return [dict(row) for row in results]   # return a dictionary


# get the complete symptom history of one patient
def get_patient_symptom_history(patient_id):
    """
    Retrieve all symptom observations for a specific patient.

    Args:
        patient_id: The ID of the patient to look up.

    Returns:
        A list of dictionaries containing the patient's symptom history.
    """

    query = """
        SELECT
            p.patient_id,
            p.name,
            o.symptom_name,
            o.severity,
            o.severity_description,
            o.frequency_count,
            o.reported_at,
            o.medication_context

        FROM observations AS o

        JOIN reports AS r
            ON o.report_id = r.report_id

        JOIN patients AS p
            ON r.patient_id = p.patient_id

        WHERE p.patient_id = ?

        ORDER BY o.reported_at ASC;
    """

    # open a connection and get the symptom history of patients
    with get_connection() as connection:
        results = connection.execute(query, (patient_id,)).fetchall()

    return [dict(row) for row in results]


# high severity is a score of 4 or higher
def get_high_severity_reports(minimum_severity = 4):
    """
    Retrieve symptom observations at or above a severity threshold.

    Args:
        minimum_severity: Minimum severity score to include (1 to 5).

    Returns:
        A list of dictionaries containing high-severity observations.
    """

    query = """
        SELECT
            p.patient_id,
            p.name,
            o.symptom_name,
            o.severity,
            o.severity_description,
            o.reported_at

        FROM observations AS o

        JOIN reports AS r
            ON o.report_id = r.report_id

        JOIN patients AS p
            ON r.patient_id = p.patient_id

        WHERE o.severity >= ?

        ORDER BY o.severity DESC, o.reported_at DESC;
    """

    # open a connection and get all high severity reports
    with get_connection() as connection:
        results = connection.execute(
            query,
            (minimum_severity,)
        ).fetchall()

    return [dict(row) for row in results]


if __name__ == "__main__":

    print("\nPATIENT OVERVIEW")
    print("= " * 60)

    patients = get_patient_overview()

    for patient in patients:
        print(
            f"{patient['name']} | "
            f"Age: {patient['age']} | "
            f"Latest symptom: {patient['symptom_name']} | "
            f"Severity: {patient['severity']}"
        )

    print("\nSYMPTOM HISTORY: EMMA CLARKE")
    print("= " * 60)

    history = get_patient_symptom_history("P001")

    for report in history:
        print(
            f"{report['reported_at']} | "
            f"{report['symptom_name']} | "
            f"Severity: {report['severity']}"
        )

    print("\nHIGH-SEVERITY REPORTS")
    print("= " * 60)

    flagged_reports = get_high_severity_reports()

    for report in flagged_reports:
        print(
            f"{report['name']} | "
            f"{report['symptom_name']} | "
            f"Severity: {report['severity']} | "
            f"{report['reported_at']}"
        )
