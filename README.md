# PatientTrack

PatientTrack is a small prototype for organizing synthetic patient-reported dermatology updates over time. It demonstrates how free-text symptom reports can be represented as structured data, stored in a relational database, analyzed for simple trends, and presented in a provider-facing dashboard with a downloadable pre-visit summary.

**Prototype and data notice:** This project uses synthetic demonstration data only. It is not a production clinical system, does not provide diagnoses, and should not be used to make treatment decisions.

## Features

- **Patient and clinical data models** using Pydantic.
- **SQLite storage** for patients, medications, symptom reports and observations, bloodwork reminders, and progress-photo metadata.
- **Synthetic sample dataset** with five fictional patients and longitudinal dermatology reports.
- **Rule-based text parser** that extracts supported symptom details and flags ambiguous or incomplete reports for review.
- **Report-processing service** that validates patient and report input, connects the parser to the database, and saves original reports alongside extracted observations and review flags.
- **Patient analytics** that summarize observation counts, severity, and descriptive symptom trends.
- **Streamlit dashboard** with patient and symptom selection, severity trend charts, summary metrics, and an underlying-report table.
- **Symptom report submission form** that allows reports to be entered directly through the dashboard and saved to SQLite.
- **Review indicators** that identify observations with incomplete or ambiguous extracted information.
- **Pre-visit summary generation** that consolidates patient information into a Markdown document that can be previewed and downloaded.

## Project structure

```text
PatientTrack/
├── data/
│   └── patienttrack.db
├── summaries/
│   └── P001_pre_visit_summary.md
├── models.py
├── database.py
├── sample_data.py
├── queries.py
├── charts.py
├── parser.py
├── report_service.py
├── analytics.py
├── visit_summary.py
├── requirements.txt
├── .gitignore
└── README.md
```

The `data/` and `summaries/` directories are created or populated when the relevant scripts run. The SQLite database is generated locally; it does not need to be committed to the repository.

## Requirements

- Python 3.10 or later
- pip

The dependencies are listed in `requirements.txt`:

- Streamlit
- pandas
- Plotly
- Pydantic

## Setup

Run these commands from the project directory.

### 1. Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Initialize and populate the sample database

```bash
python sample_data.py
```

This loads the fictional sample patients and related demonstration records. Run it only when you intend to initialize or reset the sample dataset, and check the script's behavior before rerunning it against an existing database.

### 4. Launch the dashboard

```bash
streamlit run charts.py
```

Streamlit prints a local URL in the terminal, usually `http://localhost:8501`. Open that address in your browser.

## How to use the prototype

1. Choose a fictional patient from the patient selector.
2. Enter a symptom update in the **Submit a Symptom Report** section.
3. Select **Submit Symptom Report**.
4. Review the submission confirmation and any manual-review warning.
5. Review the patient's symptom history and severity trend.
6. Expand the underlying symptom reports table to inspect all observations, including those without severity scores.
7. Scroll to **Pre-Visit Summary** and select **Generate Pre-Visit Summary**.
8. Review the generated Markdown preview and download the summary.

### Report submission workflow

The report submission form connects the Streamlit dashboard to the report-processing service.

When a report is submitted:

1. The dashboard validates that the report text is not empty.
2. `report_service.py` verifies that the selected patient exists.
3. `parser.py` attempts to extract supported symptom details from the original text.
4. The original report and extracted observations are passed to `database.py`.
5. The report and its observations are saved in SQLite.
6. The dashboard refreshes and displays a confirmation, including the database report ID and whether the report requires review.

*Example:*
```text
My lips have been very dry for the past 3 days. It happened twice today after starting isotretinoin. It feels very uncomfortable.
```

The original patient wording is preserved alongside the structured observations. This allows a reviewer to compare extracted information with the source report.

### Missing or ambiguous information

The parser does not invent information that it cannot confidently extract.

For example, a report describing dry lips and symptom frequency may not contain enough information to determine severity. In that case:

- The symptom and supported frequency details can still be saved.
- The severity field remains empty.
- The observation is flagged for review.
- The original report remains available for inspection.

The dashboard displays all observations in the underlying symptom log. However, the severity trend chart only includes observations with numeric severity scores.

This keeps incomplete information visible without introducing invented severity values.

## Data flow and module responsibilities

| Module | Responsibility |
|---|---|
| `models.py` | Defines and validates the Pydantic data models. |
| `database.py` | Creates the SQLite schema and provides database operations. |
| `sample_data.py` | Adds the fictional demonstration patients and related records. |
| `parser.py` | Demonstrates rule-based extraction from free-text symptom reports. |
| `report_service.py` | Connects the parser to the database by processing patient-submitted reports and saving extracted observations and review flags. |
| `queries.py` | Provides reusable queries for patient histories and symptom observations. |
| `analytics.py` | Calculates descriptive patient-level symptom statistics and trends. |
| `visit_summary.py` | Generates a provider-facing pre-visit summary in Markdown. |
| `charts.py` | Runs the Streamlit dashboard and connects report submission, symptom charts, report history, and summary generation. |

At a high level, patient reports are submitted as free text, processed by the rule-based parser, and passed through the report-processing service. The service validates the patient, preserves the original report, and saves the structured observations and review flags in SQLite. The stored data can then be retrieved through database and query functions and used by the analytics and presentation layers.

## Design decisions and trade-offs

### Relational storage with SQLite

SQLite keeps the prototype easy to run locally and provides relational tables and foreign-key relationships without requiring a separate database server. A managed PostgreSQL database would be a more suitable option for a multi-user production deployment.

### Preserve the original patient wording

The original report text is retained alongside structured observations. This makes extracted fields traceable to the source wording and gives a reviewer context when an extraction is incomplete or uncertain.

### Conservative rule-based extraction

The parser extracts only details supported by its rules. Missing or conflicting information can be left unknown and flagged for human review rather than silently guessed. Rule-based parsing is explainable and lightweight, but it is less flexible than a validated language-model extraction pipeline and may not recognize varied phrasing.

### Separate report processing from presentation

The report-processing service separates parsing and database operations from the Streamlit interface. This makes the processing workflow reusable and easier to test independently of the dashboard.

### Descriptive analytics, not clinical conclusions

Severity trends use numeric scores that are present in the stored observations. A higher or lower score is described as a worsening or improving trend in the reported data; it is not a diagnosis or an automated clinical alert. Missing scores are not invented.

### Markdown pre-visit summary

A Markdown summary is portable, simple to generate, easy to inspect, and straightforward to download. It demonstrates a delivery path without requiring access to a real EHR. It is not a secure EHR integration and would need appropriate identity matching, access controls, audit logging, and clinician review before any real-world use.

## Limitations and next steps

- The parser is a rule-based demonstration and does not understand every way a patient might describe a symptom.
- Extracted information may be incomplete or ambiguous and requires human review when flagged.
- The dashboard displays the original report and review information, but it does not currently provide a dedicated workflow for editing or approving extracted observations.
- Severity charts only include observations with numeric severity scores.
- Progress-photo entries represent metadata and file references; the summary does not embed or clinically assess images.
- The prototype has no authentication, authorization, encryption-at-rest configuration, audit trail, EHR connection, or production deployment controls.
- Synthetic data is used throughout the demonstration.

Potential extensions include adding a dedicated review and correction workflow, adding tests for extraction edge cases, and comparing document delivery with standards-based options such as FHIR resources.

## Delivery options comparison

PatientTrack uses a generated Markdown pre-visit summary as its demonstration delivery path.

| Delivery option | Advantages | Limitations |
|---|---|---|
| Markdown pre-visit summary | Easy to generate, read, inspect, and download. | Not a standardized EHR integration format. |
| FHIR JSON | Supports structured healthcare data exchange and interoperability. | Requires appropriate resource mapping and implementation of a FHIR interface. |
| HL7 messaging | Supports exchange of healthcare information between systems. | Requires message specifications, integration infrastructure, and receiving-system compatibility. |

### Recommendation

For this prototype, a generated Markdown pre-visit summary is the most practical delivery option. It demonstrates how structured patient-reported information can be consolidated into a clinician-readable document without requiring access to an external EHR.

FHIR JSON would be a logical next step if the project were extended to support standards-based healthcare data exchange.

## Running individual modules

From the project directory, you can run selected modules to inspect their output:

```bash
python parser.py
python analytics.py
python visit_summary.py
```

The dashboard is launched separately:

```bash
streamlit run charts.py
```

The report-processing service can also be tested independently:

```bash
python -c "from report_service import process_and_save_report; result = process_and_save_report(patient_id='P001', raw_text='My lips feel dry today. It happened twice today after starting isotretinoin.'); print(result)"
```

**Note:** Each successful execution of this command creates a new database report. Avoid running it repeatedly unless you intend to add additional demonstration records.

## Disclaimer

PatientTrack is an educational prototype built with fictional data. It is not intended for clinical use, diagnosis, treatment recommendations, or storage of real patient information.
