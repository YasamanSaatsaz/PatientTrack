from datetime import date, datetime, timedelta

# import the models and database schema
from models import (
    Patient,
    Medication,
    SymptomObservation,
    PatientReport,
    BloodworkReminder,
    ProgressPhotoRecord
)

from database import (
    init_db,
    add_patient,
    add_medication,
    add_report,
    add_bloodwork_reminder,
    add_progress_photo
)


# --------------------------------------------------
# 1. SET UP THE DATABASE
# --------------------------------------------------

init_db()

today = date.today()
now = datetime.now()


# --------------------------------------------------
# 2. CREATE SYNTHETIC PATIENTS
# --------------------------------------------------

patients = [
    Patient(
        patient_id = "P001",
        name = "Emma Clarke",
        age = 32,
        treatment_start_date = today - timedelta(days = 40)
    ),
    Patient(
        patient_id = "P002",
        name = "Olivia Hart",
        age = 27,
        treatment_start_date = today - timedelta(days = 14)
    ),
    Patient(
        patient_id = "P003",
        name = "James Fletcher",
        age = 41,
        treatment_start_date=today - timedelta(days = 30)
    ),
    Patient(
            patient_id = "P004",
            name = "Charlotte Woods",
            age = 35,
            treatment_start_date=today - timedelta(days = 51)
    ),
    Patient(
            patient_id = "P005",
            name = "Sophie Morgan",
            age = 29,
            treatment_start_date=today - timedelta(days = 10)
    )
]

for patient in patients:
    add_patient(patient)


# --------------------------------------------------
# 3. CREATE MEDICATION RECORDS
# --------------------------------------------------

medications = [
    Medication(
        medication_id = "M001",
        patient_id = "P001",
        medication_name = "Isotretinoin",
        start_date = today - timedelta(days = 40),
        dosage = "20 mg daily"
    ),
    Medication(
        medication_id = "M002",
        patient_id = "P002",
        medication_name = "Topical treatment",
        start_date = today - timedelta(days = 30),
        dosage = "Not specified"
    ),
    Medication(
        medication_id = "M003",
        patient_id = "P003",
        medication_name = "Isotretinoin",
        start_date = today - timedelta(days = 51),
        dosage = "20 mg daily"
    )
]

for medication in medications:
    add_medication(medication)


# --------------------------------------------------
# 4. CREATE A HELPER FOR PATIENT REPORTS
# --------------------------------------------------

def create_report(
    patient_id,
    days_ago,
    raw_text,
    symptom_name,
    severity,
    severity_description,
    frequency_count,
    medication_context = None,
    suspected_medication_link = None
):
    """
    Creates and saves one synthetic patient check-in.
    """

    report_time = now - timedelta(days = days_ago)

    observation = SymptomObservation(
        symptom_name = symptom_name,
        severity = severity,
        severity_description = severity_description,
        frequency_count = frequency_count,
        frequency_period = "today",
        reported_at = report_time,
        medication_context = medication_context,
        patient_suspected_medication_link = suspected_medication_link,
        extraction_confidence = 1.0,
        needs_review = False
    )

    report = PatientReport(
        patient_id = patient_id,
        submitted_at = report_time,
        raw_text = raw_text,
        observations = [observation],
        extraction_method = "manual",
        requires_review = False,
        review_status = "not_required"
    )

    add_report(report)


# --------------------------------------------------
# 5. ADD PATIENT CHECK-INS OVER SEVERAL WEEKS
# --------------------------------------------------

# Patient 1: Emma Clarke
# Acne treatment with isotretinoin
# Latest severity: 4/5

create_report(
    patient_id = "P001",
    days_ago = 21,
    raw_text = "My lips are slightly dry today.",
    symptom_name = "dry lips",
    severity = 2,
    severity_description = "Mild discomfort",
    frequency_count = 1,
    medication_context = "Isotretinoin",
    suspected_medication_link = True
)

create_report(
    patient_id = "P001",
    days_ago = 7,
    raw_text = "My lips have become very dry.",
    symptom_name = "dry lips",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 2,
    medication_context = "Isotretinoin",
    suspected_medication_link = True
)

create_report(
    patient_id = "P001",
    days_ago = 0.0083,
    raw_text = "My lips are very dry and uncomfortable today.",
    symptom_name = "dry lips",
    severity = 4,
    severity_description = "Very uncomfortable",
    frequency_count = 3,
    medication_context = "Isotretinoin",
    suspected_medication_link = True
)


# Patient 2: Olivia Hart
# Chemical peel, session 2 of 4
# Latest severity: 2/5

create_report(
    patient_id = "P002",
    days_ago = 14,
    raw_text = "My skin feels irritated after treatment.",
    symptom_name = "skin irritation",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 2
)

create_report(
    patient_id = "P002",
    days_ago = 7,
    raw_text = "My skin is looking better, but still feels dry.",
    symptom_name = "dry skin",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 1
)

create_report(
    patient_id = "P002",
    days_ago = 0.0833,
    raw_text = "My skin is improving and feels less irritated.",
    symptom_name = "skin irritation",
    severity = 2,
    severity_description = "Mild discomfort",
    frequency_count = 1
)


# Patient 3: James Fletcher
# Rosacea with topical treatment
# Latest severity: 2/5

create_report(
    patient_id = "P003",
    days_ago = 21,
    raw_text = "My facial redness is noticeable today.",
    symptom_name = "facial redness",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 2,
    medication_context = "Topical treatment",
    suspected_medication_link = False
)

create_report(
    patient_id = "P003",
    days_ago = 7,
    raw_text = "My redness has stayed about the same.",
    symptom_name = "facial redness",
    severity = 2,
    severity_description = "Mild discomfort",
    frequency_count = 1,
    medication_context = "Topical treatment",
    suspected_medication_link = False
)

create_report(
    patient_id = "P003",
    days_ago = 1,
    raw_text = "My skin looks about the same as yesterday.",
    symptom_name = "facial redness",
    severity = 2,
    severity_description = "Mild discomfort",
    frequency_count = 1,
    medication_context = "Topical treatment",
    suspected_medication_link = False
)


# Patient 4: Charlotte Woods
# Acne treatment with isotretinoin
# Latest severity: 2/5

create_report(
    patient_id = "P004",
    days_ago = 21,
    raw_text = "My lips are very dry.",
    symptom_name = "dry lips",
    severity = 4,
    severity_description = "Very uncomfortable",
    frequency_count = 3,
    medication_context = "Isotretinoin",
    suspected_medication_link = True
)

create_report(
    patient_id = "P004",
    days_ago = 7,
    raw_text = "My lips are less dry than before.",
    symptom_name = "dry lips",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 2,
    medication_context = "Isotretinoin",
    suspected_medication_link = True
)

create_report(
    patient_id = "P004",
    days_ago = 1,
    raw_text = "My lips are only slightly dry now.",
    symptom_name = "dry lips",
    severity = 2,
    severity_description = "Mild discomfort",
    frequency_count = 1,
    medication_context = "Isotretinoin",
    suspected_medication_link = True
)


# Patient 5: Sophie Morgan
# Laser resurfacing, session 1 of 3
# Latest severity: 3/5

create_report(
    patient_id = "P005",
    days_ago = 21,
    raw_text = "My skin feels a little sensitive.",
    symptom_name = "skin sensitivity",
    severity = 2,
    severity_description = "Mild discomfort",
    frequency_count = 1
)

create_report(
    patient_id = "P005",
    days_ago = 10,
    raw_text = "My skin feels more sensitive and slightly red.",
    symptom_name = "skin redness",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 2
)

create_report(
    patient_id = "P005",
    days_ago = 4,
    raw_text = "My skin is still somewhat red and sensitive.",
    symptom_name = "skin redness",
    severity = 3,
    severity_description = "Moderate discomfort",
    frequency_count = 1
)


# --------------------------------------------------
# 6. ADD BLOODWORK REMINDERS
# --------------------------------------------------

reminders = [
    BloodworkReminder(
        patient_id = "P001",
        reminder_date = today + timedelta(days = 3),
        reminder_type = "Bloodwork",
        status = "upcoming",
        notes = "Routine synthetic monitoring reminder"
    ),
    BloodworkReminder(
        patient_id = "P004",
        reminder_date = today + timedelta(days = 5),
        reminder_type = "Bloodwork",
        status = "upcoming",
        notes = "Routine synthetic monitoring reminder"
    ),
    BloodworkReminder(
        patient_id = "P003",
        reminder_date = today - timedelta(days = 2),
        reminder_type = "Bloodwork",
        status = "overdue",
        notes = "Synthetic example of an overdue reminder"
    )
]

for reminder in reminders:
    add_bloodwork_reminder(reminder)


# --------------------------------------------------
# 7. ADD PROGRESS PHOTO RECORDS
# --------------------------------------------------

photos = [
    ProgressPhotoRecord(
        patient_id = "P001",
        photo_date = today - timedelta(days = 21),
        photo_reference = "synthetic/P001/week1.jpg",
        notes = "Synthetic baseline photo reference"
    ),
    ProgressPhotoRecord(
        patient_id = "P001",
        photo_date = today - timedelta(days = 7),
        photo_reference = "synthetic/P001/week3.jpg",
        notes = "Synthetic follow-up photo reference"
    ),
    ProgressPhotoRecord(
        patient_id = "P002",
        photo_date = today - timedelta(days = 14),
        photo_reference = "synthetic/P002/session1.jpg",
        notes = "Synthetic treatment photo reference"
    ),
    ProgressPhotoRecord(
        patient_id = "P004",
        photo_date = today - timedelta(days = 21),
        photo_reference = "synthetic/P004/week1.jpg",
        notes = "Synthetic baseline photo reference"
    ),
    ProgressPhotoRecord(
        patient_id = "P005",
        photo_date = today - timedelta(days = 4),
        photo_reference = "synthetic/P005/session1.jpg",
        notes = "Synthetic treatment photo reference"
    )
]

for photo in photos:
    add_progress_photo(photo)


# --------------------------------------------------
# 8. CONFIRM THAT DATA WAS ADDED
# --------------------------------------------------

print("Synthetic data added successfully!")

print(f"\nPatients added: {len(patients)}")
print(f"Medications added: {len(medications)}")
print("Symptom reports added: 15")
print(f"Bloodwork reminders added: {len(reminders)}")
print(f"Progress photo records added: {len(photos)}")
