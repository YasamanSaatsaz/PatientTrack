import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_patients, get_patient_observations
from report_service import process_and_save_report
from visit_summary import generate_pre_visit_summary


def create_symptom_trend_chart(patient_id: str, symptom_name: str):
    """
    Create a Plotly line chart for one patient's selected symptom.

    Only observations with recorded numeric severity scores are charted.

    Args:
        patient_id: Unique ID of the patient.
        symptom_name: Symptom to display.

    Returns:
        A Plotly Figure, or None if there is no chartable data.
    """
    
    history = get_patient_observations(patient_id)

    if not history:
        return None

    data = pd.DataFrame(history)

    data["severity"] = pd.to_numeric(
        data["severity"],
        errors="coerce",
    )

    data = data[
        (data["symptom_name"] == symptom_name)
        & data["severity"].notna()
    ].copy()

    if data.empty:
        return None

    data["reported_at"] = pd.to_datetime(data["reported_at"])
    data = data.sort_values("reported_at")

    figure = px.line(
        data,
        x="reported_at",
        y="severity",
        markers=True,
        title=f"{symptom_name.title()} — symptom severity over time",
        labels={
            "reported_at": "Report date",
            "severity": "Patient-reported severity (1–5)",
        },
        hover_data={
            "severity_description": True,
            "frequency_count": True,
            "medication_context": True,
        },
    )

    # Severity is measured on a fixed scale from 1 to 5.
    figure.update_yaxes(
        range=[0.5, 5.5],
        tickmode="array",
        tickvals=[1, 2, 3, 4, 5],
    )

    figure.update_layout(
        xaxis_title="Report date",
        yaxis_title="Severity",
        hovermode="x unified",
        showlegend=False,
    )

    return figure


def main():
    """Display the PatientTrack dashboard."""

    st.set_page_config(
        page_title="PatientTrack — Patient Dashboard",
        page_icon="📈",
        layout="wide",
    )

    st.title("PatientTrack")
    st.subheader("Patient-reported symptom trends")

    st.caption(
        "Synthetic dermatology data. Severity scores are patient-reported "
        "on a scale from 1 (mild) to 5 (severe)."
    )

    patients = get_patients()

    if not patients:
        st.warning(
            "No patients were found. Run `python sample_data.py` "
            "from your project directory to add the synthetic sample data."
        )
        return

    # Build a patient-name lookup while keeping patient IDs for database queries.
    patient_options = {
        f"{patient['name']} ({patient['patient_id']})": patient["patient_id"]
        for patient in patients
    }

    selected_patient_label = st.selectbox(
        "Select a patient",
        options=list(patient_options.keys()),
    )

    selected_patient_id = patient_options[selected_patient_label]

    # --------------------------------------------------
    # REPORT SUBMISSION
    # --------------------------------------------------

    st.divider()
    st.header("Submit a Symptom Report")

    st.write(
        "Enter a patient's symptom update in their own words. "
        "PatientTrack will attempt to extract supported details, "
        "save the original report, and flag incomplete information for review."
    )

    with st.form(
        key=f"report_submission_form_{selected_patient_id}",
        clear_on_submit=True,
    ):
        raw_report_text = st.text_area(
            "Patient's report",
            placeholder=(
                "Example: My lips have been very dry for the past 3 days. "
                "It happened twice today after starting isotretinoin."
            ),
            height=120,
        )

        submit_report = st.form_submit_button(
            "Submit Symptom Report",
            type="primary",
        )

    if submit_report:
        if not raw_report_text.strip():
            st.error("Please enter a symptom report before submitting.")

        else:
            try:
                result = process_and_save_report(
                    patient_id=selected_patient_id,
                    raw_text=raw_report_text,
                )

                # Save a short confirmation so it remains visible after rerunning.
                st.session_state["report_submission_notice"] = {
                    "patient_id": selected_patient_id,
                    "report_id": result["report_id"],
                    "observation_count": result["observation_count"],
                    "requires_review": result["requires_review"],
                }

                # Refresh the dashboard so the new report is retrieved.
                st.rerun()

            except (ValueError, RuntimeError, OSError) as error:
                st.error(f"Could not submit the report: {error}")

            except Exception as error:
                st.error(
                    "An unexpected error occurred while saving the report. "
                    f"Details: {error}"
                )

    # Display the submission confirmation after the dashboard refreshes.
    submission_notice = st.session_state.get("report_submission_notice")

    if submission_notice:
        if submission_notice["patient_id"] == selected_patient_id:
            st.success(
                f"Report saved successfully. "
                f"Database report ID: {submission_notice['report_id']}. "
                f"Extracted observations: "
                f"{submission_notice['observation_count']}."
            )

            if submission_notice["requires_review"]:
                st.warning(
                    "This report has been flagged for review because "
                    "some extracted information may be incomplete or ambiguous."
                )
            else:
                st.info("This report does not currently require manual review.")

            if st.button("Dismiss submission message"):
                del st.session_state["report_submission_notice"]
                st.rerun()

        else:
            st.session_state.pop("report_submission_notice", None)

    # --------------------------------------------------
    # SYMPTOM HISTORY AND CHART
    # --------------------------------------------------

    st.divider()
    st.header("Symptom History")

    # Retrieve ALL observations, including those without severity scores.
    history = get_patient_observations(selected_patient_id)

    if not history:
        st.info(
            "This patient does not have any symptom observations yet. "
            "Submit a report above to begin building their symptom history."
        )

    else:
        history_data = pd.DataFrame(history)

        history_data["reported_at"] = pd.to_datetime(
            history_data["reported_at"]
        )

        history_data["severity"] = pd.to_numeric(
            history_data["severity"],
            errors="coerce",
        )

        symptoms = sorted(
            history_data["symptom_name"].dropna().unique().tolist()
        )

        if not symptoms:
            st.info("No symptoms are available for this patient.")

        else:
            selected_symptom = st.selectbox(
                "Select a symptom",
                options=symptoms,
            )

            # Keep every observation for the selected symptom.
            symptom_data = history_data[
                history_data["symptom_name"] == selected_symptom
            ].copy()

            symptom_data = symptom_data.sort_values(
                "reported_at"
            )

            # Separately identify observations with numeric severity scores.
            chartable_data = symptom_data[
                symptom_data["severity"].notna()
            ].copy()

            total_observations = len(symptom_data)
            scored_observations = len(chartable_data)

            # Count observations flagged for manual review.
            if "needs_review" in symptom_data.columns:
                review_count = (
                    symptom_data["needs_review"]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )
            else:
                review_count = 0

            metric_one, metric_two, metric_three = st.columns(3)

            metric_one.metric(
                "Total observations",
                total_observations,
            )

            metric_two.metric(
                "Observations with severity",
                scored_observations,
            )

            metric_three.metric(
                "Flagged for review",
                int(review_count),
            )

            # ------------------------------------------
            # SEVERITY CHART
            # ------------------------------------------

            st.subheader("Symptom severity over time")

            if chartable_data.empty:
                st.info(
                    "There are no severity scores recorded for this symptom. "
                    "The symptom still appears in the underlying report history."
                )

            else:
                first_severity = int(chartable_data.iloc[0]["severity"])
                latest_severity = int(chartable_data.iloc[-1]["severity"])

                severity_change = latest_severity - first_severity

                metric_one, metric_two = st.columns(2)

                metric_one.metric(
                    "Latest severity",
                    latest_severity,
                )

                metric_two.metric(
                    "Change since first scored observation",
                    f"{severity_change:+d}",
                )

                figure = create_symptom_trend_chart(
                    patient_id=selected_patient_id,
                    symptom_name=selected_symptom,
                )

                if figure is not None:
                    st.plotly_chart(
                        figure,
                        use_container_width=True,
                    )

                st.caption(
                    "A higher score means the patient reported a more severe "
                    "symptom. Only observations with numeric severity scores "
                    "are plotted. This chart describes reported symptoms; "
                    "it does not provide a diagnosis."
                )

            # ------------------------------------------
            # COMPLETE UNDERLYING SYMPTOM LOG
            # ------------------------------------------

            with st.expander(
                "View all underlying symptom reports",
                expanded=True,
            ):
                display_data = symptom_data.copy()

                # Display severity values as consistent strings for Streamlit.
                display_data["severity"] = display_data["severity"].apply(
                    lambda value: (
                        "Not reported" if pd.isna(value) else str(int(value))
                    )
                )

                # Display review status in readable language.
                if "needs_review" in display_data.columns:
                    display_data["Review status"] = (
                        display_data["needs_review"]
                        .fillna(False)
                        .astype(bool)
                        .map({
                            True: "Needs review",
                            False: "No review flag",
                        })
                    )
                else:
                    display_data["Review status"] = "Not available"

                # Preserve the reason for review when one is recorded.
                if "review_reason" not in display_data.columns:
                    display_data["review_reason"] = None

                # Preserve the original patient-submitted wording.
                if "raw_text" not in display_data.columns:
                    display_data["raw_text"] = None

                # Add report ID when available.
                if "report_id" not in display_data.columns:
                    display_data["report_id"] = None

                # Format timestamps for display.
                display_data["reported_at"] = (
                    pd.to_datetime(display_data["reported_at"])
                    .dt.strftime("%Y-%m-%d %H:%M")
                )

                # Select and rename the fields shown in the table.
                table_columns = {
                    "reported_at": "Report date",
                    "report_id": "Report ID",
                    "symptom_name": "Symptom",
                    "severity": "Severity",
                    "severity_description": "Description",
                    "frequency_count": "Frequency",
                    "medication_context": "Medication context",
                    "Review status": "Review status",
                    "review_reason": "Review reason",
                    "raw_text": "Original patient report",
                }

                available_columns = [
                    column
                    for column in table_columns
                    if column in display_data.columns
                ]

                display_data = display_data[available_columns].rename(
                    columns=table_columns
                )

                st.dataframe(
                    display_data,
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "Observations without a numeric severity score are "
                    "included in this table but excluded from the severity chart. "
                    "Reports flagged for review should be assessed by a reviewer."
                )

    # --------------------------------------------------
    # PRE-VISIT SUMMARY
    # --------------------------------------------------

    st.divider()
    st.header("Pre-Visit Summary")

    st.write(
        "Generate a consolidated summary of this patient's reported symptoms, "
        "medications, reminders, progress-photo records, and review items."
    )

    if st.button(
        "Generate Pre-Visit Summary",
        type="primary",
        key="generate_pre_visit_summary",
    ):
        try:
            summary_text = generate_pre_visit_summary(
                patient_id=selected_patient_id
            )

            st.session_state["pre_visit_summary_text"] = summary_text
            st.session_state["pre_visit_summary_patient_id"] = (
                selected_patient_id
            )

        except (ValueError, RuntimeError, OSError) as error:
            st.error(f"Could not generate the summary: {error}")

    saved_summary = st.session_state.get("pre_visit_summary_text")
    saved_patient_id = st.session_state.get("pre_visit_summary_patient_id")

    if saved_summary and saved_patient_id == selected_patient_id:
        st.success("Pre-visit summary generated successfully.")

        st.download_button(
            label="Download Pre-Visit Summary",
            data=saved_summary,
            file_name=f"{selected_patient_id}_pre_visit_summary.md",
            mime="text/markdown",
            key=f"download_summary_{selected_patient_id}",
        )

        with st.expander("Preview the generated summary", expanded=True):
            st.markdown(saved_summary)

    elif saved_summary and saved_patient_id != selected_patient_id:
        st.info(
            "Select Generate Pre-Visit Summary to create a summary "
            "for the currently selected patient."
        )


if __name__ == "__main__":
    main()
