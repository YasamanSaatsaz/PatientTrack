# import libraries for managing SQLite databases, fikle/folder paths, and database connections
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# import necessary models for database objects
from models import (
    Patient,
    Medication,
    PatientReport,
    BloodworkReminder,
    ProgressPhotoRecord
)


# --------------------------------------------------
# 1. DATABASE LOCATION
# Stores the database file in the "data" folder in the main project folder
# --------------------------------------------------

PROJECT_FOLDER = Path(__file__).parent
DATA_FOLDER = PROJECT_FOLDER / "data"
DATABASE_PATH = DATA_FOLDER / "patienttrack.db"


# --------------------------------------------------
# 2. DATABASE CONNECTION
# --------------------------------------------------

@contextmanager
def get_connection():
    """
    Opens a database connection and closes it safely
    after the operation is complete.
    """

    # create the data folder if it doesn't already exist (no error if it does exist)
    DATA_FOLDER.mkdir(exist_ok = True)

    # open the connection
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row    # can access rows using column names

    # enforce foreign-key relationships for cross-table references
    connection.execute("PRAGMA foreign_keys = ON")

    # try opening a temporary connection
    try:
        yield connection
        connection.commit()     # save (committed) database changes

    except Exception:
        connection.rollback()   # catch uncommitted changes
        raise

    finally:
        connection.close()      # close the connection


# --------------------------------------------------
# 3. CREATE DATABASE TABLES
# --------------------------------------------------

def init_db():
    """
    Creates all PatientTrack database tables
    if they do not already exist.
    """

    with get_connection() as connection:

        connection.executescript("""

            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                treatment_start_date TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS medications (
                medication_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                medication_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                dosage TEXT,

                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            );


            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                extraction_method TEXT NOT NULL,
                requires_review INTEGER NOT NULL,
                review_status TEXT NOT NULL,

                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            );


            CREATE TABLE IF NOT EXISTS observations (
                observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                symptom_name TEXT NOT NULL,
                severity INTEGER,
                severity_description TEXT,
                frequency_count INTEGER,
                frequency_period TEXT,
                reported_at TEXT NOT NULL,
                medication_context TEXT,
                patient_suspected_medication_link INTEGER,
                extraction_confidence REAL NOT NULL,
                needs_review INTEGER NOT NULL,
                review_reason TEXT,

                FOREIGN KEY (report_id)
                    REFERENCES reports(report_id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS bloodwork_reminders (
                reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                reminder_date TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,

                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            );


            CREATE TABLE IF NOT EXISTS progress_photos (
                photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                photo_date TEXT NOT NULL,
                photo_reference TEXT,
                notes TEXT,

                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            );


            CREATE INDEX IF NOT EXISTS idx_reports_patient
            ON reports(patient_id);


            CREATE INDEX IF NOT EXISTS idx_observations_report
            ON observations(report_id);


            CREATE INDEX IF NOT EXISTS idx_observations_symptom
            ON observations(symptom_name);


        """)


# --------------------------------------------------
# 4. SAVE A PATIENT
# --------------------------------------------------

def add_patient(patient: Patient):
    """
    Saves a patient record in the database.
    """

    with get_connection() as connection:

        # NOTE: ON CONFLICT is used to handle duplicate patient IDs
        # (updates existing patient record instead of creating a new one)
        connection.execute(
            """
            INSERT INTO patients (
                patient_id,
                name,
                age,
                treatment_start_date
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                treatment_start_date = excluded.treatment_start_date
            """,
            # gets the actual values
            (
                patient.patient_id,
                patient.name,
                patient.age,
                patient.treatment_start_date.isoformat()
            )
        )


# --------------------------------------------------
# 5. SAVE A MEDICATION
# --------------------------------------------------

def add_medication(medication: Medication):
    """
    Saves a medication record for an existing patient.
    """

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO medications (
                medication_id,
                patient_id,
                medication_name,
                start_date,
                end_date,
                dosage
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(medication_id) DO UPDATE SET
                patient_id = excluded.patient_id,
                medication_name = excluded.medication_name,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                dosage = excluded.dosage
            """,
            # actual values
            (
                medication.medication_id,
                medication.patient_id,
                medication.medication_name,
                medication.start_date.isoformat(),
                medication.end_date.isoformat()
                if medication.end_date else None,
                medication.dosage
            )
        )


# --------------------------------------------------
# 6. SAVE A PATIENT REPORT AND ITS OBSERVATIONS
# --------------------------------------------------

def add_report(report: PatientReport) -> int:
    """
    Saves the original patient report and all its
    extracted symptom observations.

    Returns the database ID of the new report.
    """

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO reports (
                patient_id,
                submitted_at,
                raw_text,
                extraction_method,
                requires_review,
                review_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            # actual values
            (
                report.patient_id,
                report.submitted_at.isoformat(),
                report.raw_text,
                report.extraction_method,
                int(report.requires_review),
                report.review_status
            )
        )

        # boolean for review is converted to integer - SQLite stores Booleans as integers
        report_id = cursor.lastrowid

        for observation in report.observations:

            connection.execute(
                """
                INSERT INTO observations (
                    report_id,
                    symptom_name,
                    severity,
                    severity_description,
                    frequency_count,
                    frequency_period,
                    reported_at,
                    medication_context,
                    patient_suspected_medication_link,
                    extraction_confidence,
                    needs_review,
                    review_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                # actual values
                (
                    report_id,
                    observation.symptom_name,
                    observation.severity,
                    observation.severity_description,
                    observation.frequency_count,
                    observation.frequency_period,
                    observation.reported_at.isoformat(),
                    observation.medication_context,
                    (
                        # convert a Boolean to an integer when a value exists
                        int(observation.patient_suspected_medication_link)
                        if observation.patient_suspected_medication_link is not None
                        else None
                    ),
                    # save the confidence score, review flag, and review reason
                    observation.extraction_confidence,
                    int(observation.needs_review),
                    observation.review_reason
                )
            )

        return report_id


# --------------------------------------------------
# 7. SAVE A BLOODWORK REMINDER
# --------------------------------------------------

def add_bloodwork_reminder(reminder: BloodworkReminder):
    """
    Saves a bloodwork reminder for an existing patient.
    """

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO bloodwork_reminders (
                patient_id,
                reminder_date,
                reminder_type,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            # actual values
            (
                reminder.patient_id,
                reminder.reminder_date.isoformat(),
                reminder.reminder_type,
                reminder.status,
                reminder.notes
            )
        )


# --------------------------------------------------
# 8. SAVE A PROGRESS PHOTO RECORD
# --------------------------------------------------

def add_progress_photo(photo: ProgressPhotoRecord):
    """
    Saves progress-photo metadata for an existing patient.
    """

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO progress_photos (
                patient_id,
                photo_date,
                photo_reference,
                notes
            )
            VALUES (?, ?, ?, ?)
            """,
            # get actual values (photo metadata)
            (
                photo.patient_id,
                photo.photo_date.isoformat(),
                photo.photo_reference,
                photo.notes
            )
        )


# --------------------------------------------------
# 9. RETRIEVE PATIENTS
# --------------------------------------------------

def get_patients():
    """
    Returns all patients stored in the database.
    """

    with get_connection() as connection:

        # get a list of all patients, ordered by their ID
        rows = connection.execute(
            """
            SELECT *
            FROM patients
            ORDER BY patient_id
            """
        ).fetchall()

        return [dict(row) for row in rows]      # each row becomes a regular Python dictionary


# --------------------------------------------------
# 10. RETRIEVE REPORTS FOR ONE PATIENT
# --------------------------------------------------

def get_patient_reports(patient_id: str):
    """
    Returns all reports belonging to a patient.
    """

    with get_connection() as connection:

        # get all reports for a specific patient (can be any valid ID), ordered by newest reports first
        rows = connection.execute(
            """
            SELECT *
            FROM reports
            WHERE patient_id = ?
            ORDER BY submitted_at DESC
            """,
            (patient_id,)
        ).fetchall()

        return [dict(row) for row in rows]


# --------------------------------------------------
# 11. RETRIEVE OBSERVATIONS FOR ONE PATIENT
# --------------------------------------------------

def get_patient_observations(patient_id: str):
    """
    Returns all symptom observations belonging
    to a patient, including their original report text.
    """

    with get_connection() as connection:

        # get all symptom observations for a patient, ordered by newest observations first
        # we use a join with the reports table using the patient's ID to get the patient's wording of observations
        rows = connection.execute(
            """
            SELECT
                observations.*,
                reports.patient_id,
                reports.raw_text,
                reports.submitted_at

            FROM observations

            JOIN reports
                ON observations.report_id = reports.report_id

            WHERE reports.patient_id = ?

            ORDER BY observations.reported_at DESC
            """,
            (patient_id,)
        ).fetchall()

        return [dict(row) for row in rows]


# --------------------------------------------------
# 12. RETRIEVE BLOODWORK REMINDERS
# --------------------------------------------------

def get_patient_reminders(patient_id: str):
    """
    Returns all bloodwork reminders for a patient.
    """

    with get_connection() as connection:

        # get all reminders for a specific patient (earliest reminder first)
        rows = connection.execute(
            """
            SELECT *
            FROM bloodwork_reminders
            WHERE patient_id = ?
            ORDER BY reminder_date
            """,
            (patient_id,)
        ).fetchall()

        return [dict(row) for row in rows]


# --------------------------------------------------
# 13. LIST DATABASE TABLES
# --------------------------------------------------

def get_database_tables():
    """
    Returns the names of all tables in the database.
    """

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        return [row["name"] for row in rows]


# --------------------------------------------------
# 14. RUN DATABASE SETUP TEST
# --------------------------------------------------

if __name__ == "__main__":

    print("Initializing PatientTrack database...")

    init_db()

    print("\nDatabase created successfully!")
    print(f"Database location: {DATABASE_PATH}")

    print("\nTables created:")

    for table in get_database_tables():
        print(f"- {table}")
