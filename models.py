# import statements (necessary libraries)
from datetime import date, datetime                                     # for dates and times
from typing import Optional, Literal                                    # type of information variables can contain (can have a value, be empty, or be one of several fixed options)
from pydantic import BaseModel, Field, ConfigDict, field_validator      # define/validate structured data


# --------------------------------------------------
# 1. PATIENT
# Identifies a patient
# --------------------------------------------------

class Patient(BaseModel):
    """
    Represents a fictional patient in the dermatology clinic.
    """

    # remove unnecessary whitespace
    model_config = ConfigDict(str_strip_whitespace = True)

    # unique IDs for patients
    patient_id: str = Field(
        description = "Unique identifier for the patient"
    )

    # patient name
    name: str = Field(
        min_length = 1,
        description = "Fictional patient name"
    )

    # patient age
    age: int = Field(
        ge = 18,
        le = 120,
        description = "Patient age"
    )

    # record the date the patient's treatment started
    treatment_start_date: date = Field(
        description = "Date the patient's treatment began"
    )

    # custom validation rule for patient ID
    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value):
        # ID is empty or contains only spaces
        if not value.strip():
            raise ValueError("Patient ID cannot be empty")
        return value


# --------------------------------------------------
# 2. MEDICATION
# Records treatment information
# --------------------------------------------------

class Medication(BaseModel):
    """
    Represents a medication prescribed or recorded
    in a patient's treatment history.
    """

    # medication record and the patient it belongs to
    medication_id: str
    patient_id: str

    medication_name: str = Field(
        min_length = 1
    )

    # shows when medication started/ended (end date can be empty if treatment is ongoing)
    start_date: date
    end_date: Optional[date] = None

    dosage: Optional[str] = None    # Optional because it might not be available in sample data

    # removes unnecessary spaces from medication names
    @field_validator("medication_name")
    @classmethod
    def clean_medication_name(cls, value):
        return value.strip()


# --------------------------------------------------
# 3. SYMPTOM OBSERVATION
# Represents symptoms given by the patient
# --------------------------------------------------

class SymptomObservation(BaseModel):
    """
    Represents one symptom extracted from a patient report.

    A single report can contain multiple observations.
    """

    # each symptom observation can have an ID (generated automatically)
    observation_id: Optional[int] = None

    # stores the symptom
    symptom_name: str = Field(
        min_length = 1,
        description = "Normalized name of the reported symptom"
    )

    # symptom severity (can only be on a scale of 1 to 5)
    severity: Optional[int] = Field(
        default = None,     # severity score is left empty if not provided by the patient
        ge = 1,
        le = 5,
        description = "Patient-reported severity from 1 to 5"
    )

    # patients might imply severity in a description (non-numerical)
    severity_description: Optional[str] = None

    # how many times a symptom occurred
    frequency_count: Optional[int] = Field(
        default = None,
        ge = 0,
        description = "Number of reported occurrences"
    )

    # how long the patient has been experiencing this symotom (specific observation)
    frequency_period: Optional[str] = Field(
        default = None,
        description = "Time period, such as today or this week"
    )

    reported_at: datetime

    # medication information (if the patient mentions medication)
    medication_context: Optional[str] = Field(
        default = None,
        description = "Medication mentioned or associated in the report"
    )

    # if the patient mentions possible correlation between medication and symptoms
    patient_suspected_medication_link: Optional[bool] = Field(
        default = None,
        description = "Whether the patient suspects a medication relationship"
    )

    # confidence regarding information extraction from the patient's report
    extraction_confidence: float = Field(
        default = 1.0,
        ge = 0.0,
        le = 1.0,
        description = "Confidence in the extracted information"
    )

    # flags if human review is needed
    needs_review: bool = False

    # reason for human review
    review_reason: Optional[str] = None

    # cleans symptom names to lowercase for consistency
    @field_validator("symptom_name")
    @classmethod
    def clean_symptom_name(cls, value):
        return value.strip().lower()


# --------------------------------------------------
# 4. PATIENT REPORT
# Represents a complete report from a patient's check-in
# --------------------------------------------------

class PatientReport(BaseModel):
    """
    Represents a complete patient-submitted check-in.

    We preserve the original text so that extracted
    information can always be checked against its source.
    """

    report_id: Optional[int] = None

    patient_id: str

    submitted_at: datetime

    raw_text: str = Field(
        min_length = 1,
        description = "Original text submitted by the patient"
    )

    # list of symptoms mentioned in the report
    observations: list[SymptomObservation] = Field(
        default_factory = list
    )

    # how the report was processed (possibly via Python rules, AI, or person)
    extraction_method: Literal[
        "rule_based",
        "ai",
        "manual"
    ] = "rule_based"

    requires_review: bool = False   # flag that indicates if the report needs review

    # tracks the review process
    review_status: Literal[
        "not_required",
        "pending",
        "reviewed"
    ] = "not_required"

    # removes unnecessary spaces from the report
    @field_validator("raw_text")
    @classmethod
    def clean_report_text(cls, value):
        return value.strip()


# --------------------------------------------------
# 5. BLOODWORK REMINDER
# Tracks reminder dates
# --------------------------------------------------

class BloodworkReminder(BaseModel):
    """
    Stores bloodwork reminder information.

    This records reminder dates and status only.
    It does not interpret laboratory results.
    """

    reminder_id: Optional[int] = None

    patient_id: str

    reminder_date: date

    reminder_type: str = "Bloodwork"

    # status of the bloodwork reminder
    status: Literal[
        "upcoming",
        "due",
        "completed",
        "overdue"
    ] = "upcoming"

    notes: Optional[str] = None     # additional notes about the reminder (could be empty)


# --------------------------------------------------
# 6. PROGRESS PHOTO RECORD
# Records progress-photo metadata
# --------------------------------------------------

class ProgressPhotoRecord(BaseModel):
    """
    Stores metadata about a patient's progress photo.

    The prototype will use synthetic photo records,
    not real patient photographs.
    """

    photo_id: Optional[int] = None

    patient_id: str

    photo_date: date

    photo_reference: Optional[str] = None

    notes: Optional[str] = None


# --------------------------------------------------
# 7. BASIC VALIDATION TEST
# --------------------------------------------------

if __name__ == "__main__":

    example_observation = SymptomObservation(
        symptom_name = "  Dry Lips  ",  # extra whitespace used to test cleaning function
        severity = 4,
        severity_description = "Very uncomfortable",
        frequency_count = 1,
        frequency_period = "today",
        reported_at=datetime.now(),
        medication_context = "Isotretinoin",
        patient_suspected_medication_link = True,
        extraction_confidence = 0.95
    )

    print("Symptom observation created successfully:")
    print(example_observation.model_dump())     # print the model as a Python dictionary

    print("\nTesting invalid severity...")

    # test invalid data (ex: severity score out of range)
    try:
        SymptomObservation(
            symptom_name = "Dry skin",
            severity = 8,
            reported_at = datetime.now()
        )
    except Exception as error:
        print("Validation correctly rejected invalid data:")
        print(error)
