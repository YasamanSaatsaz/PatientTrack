from collections import Counter, defaultdict
from datetime import datetime

from queries import get_patient_overview, get_patient_symptom_history


def _parse_datetime(value):
    """Convert a stored ISO date/time string into a datetime object."""
    
    if isinstance(value, datetime):
        return value

    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def get_patient_symptom_trends(patient_id):
    """
    Summarize severity changes for each symptom reported by one patient.

    Only numeric severity scores are used. Missing scores are not guessed.

    Returns:
        A list of dictionaries, one per symptom, with first/latest scores
        and a direction of improving, worsening, unchanged, or insufficient_data.
    """

    history = get_patient_symptom_history(patient_id)
    grouped_observations = defaultdict(list)

    for observation in history:
        symptom_name = observation.get("symptom_name") or "Unknown symptom"
        grouped_observations[symptom_name].append(observation)

    trends = []

    for symptom_name, observations in grouped_observations.items():
        observations.sort(
            key=lambda item: _parse_datetime(item.get("reported_at"))
            or datetime.min
        )

        scored_observations = [
            item for item in observations
            if item.get("severity") is not None
        ]

        if len(scored_observations) < 2:
            direction = "insufficient_data"
            first_severity = (
                scored_observations[0]["severity"]
                if scored_observations else None
            )
            latest_severity = first_severity
            change = None
        else:
            first_severity = scored_observations[0]["severity"]
            latest_severity = scored_observations[-1]["severity"]
            change = latest_severity - first_severity

            if change > 0:
                direction = "worsening"
            elif change < 0:
                direction = "improving"
            else:
                direction = "unchanged"

        trends.append({
            "patient_id": patient_id,
            "symptom_name": symptom_name,
            "observation_count": len(observations),
            "scored_observation_count": len(scored_observations),
            "first_severity": first_severity,
            "latest_severity": latest_severity,
            "severity_change": change,
            "trend": direction,
        })

    return trends


def get_patient_symptom_frequency(patient_id):
    """
    Count how often each symptom appears in a patient's stored observations.

    This is a count of submitted observations, not the patient's reported
    number of episodes. Those are separate concepts.
    """

    history = get_patient_symptom_history(patient_id)
    counts = Counter(
        observation.get("symptom_name") or "Unknown symptom"
        for observation in history
    )

    return [
        {
            "patient_id": patient_id,
            "symptom_name": symptom_name,
            "observation_count": count,
        }
        for symptom_name, count in counts.most_common()
    ]


def get_worsening_patients():
    """
    Return patient/symptom combinations whose latest numeric severity
    is higher than their earliest numeric severity.

    A worsening trend is a descriptive data signal, not a clinical alert.
    """

    overview = get_patient_overview()
    patient_ids = [patient["patient_id"] for patient in overview]
    worsening = []

    for patient_id in patient_ids:
        patient_trends = get_patient_symptom_trends(patient_id)

        for trend in patient_trends:
            if trend["trend"] == "worsening":
                patient_name = next(
                    (
                        patient["name"]
                        for patient in overview
                        if patient["patient_id"] == patient_id
                    ),
                    "Unknown patient",
                )

                worsening.append({
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "symptom_name": trend["symptom_name"],
                    "first_severity": trend["first_severity"],
                    "latest_severity": trend["latest_severity"],
                    "severity_change": trend["severity_change"],
                })

    return worsening


def get_patient_analytics_summary(patient_id):
    """
    Return a compact analytics summary for one patient.
    """

    history = get_patient_symptom_history(patient_id)
    trends = get_patient_symptom_trends(patient_id)

    scored = [
        observation["severity"]
        for observation in history
        if observation.get("severity") is not None
    ]

    return {
        "patient_id": patient_id,
        "total_observations": len(history),
        "unique_symptoms": len({
            observation.get("symptom_name")
            for observation in history
            if observation.get("symptom_name")
        }),
        "average_reported_severity": (
            round(sum(scored) / len(scored), 1) if scored else None
        ),
        "high_severity_observations": sum(
            1 for score in scored if score >= 4
        ),
        "worsening_symptoms": sum(
            1 for trend in trends if trend["trend"] == "worsening"
        ),
        "improving_symptoms": sum(
            1 for trend in trends if trend["trend"] == "improving"
        ),
        "trends": trends,
    }


if __name__ == "__main__":
    print("\nPATIENT ANALYTICS")
    print("= " * 60)

    patients = get_patient_overview()

    if not patients:
        print("No patients found. Run sample_data.py first.")
    else:
        for patient in patients:
            summary = get_patient_analytics_summary(patient["patient_id"])

            print(f"\n{patient['name']} ({patient['patient_id']})")
            print("- " * 60)
            print(f"Total observations: {summary['total_observations']}")
            print(f"Unique symptoms: {summary['unique_symptoms']}")
            print(
                "Average reported severity: "
                f"{summary['average_reported_severity']}"
            )
            print(
                "High-severity observations (4-5): "
                f"{summary['high_severity_observations']}"
            )

            for trend in summary["trends"]:
                print(
                    f"  {trend['symptom_name']}: {trend['trend']} "
                    f"(first = {trend['first_severity']}, "
                    f"latest = {trend['latest_severity']})"
                )

    print("\nWORSENING SYMPTOM TRENDS")
    print("=" * 60)

    worsening_patients = get_worsening_patients()

    if not worsening_patients:
        print("No worsening numeric severity trends identified.")
    else:
        for item in worsening_patients:
            print(
                f"{item['patient_name']} | {item['symptom_name']} | "
                f"{item['first_severity']} -> {item['latest_severity']}"
            )
