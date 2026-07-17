import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_CATEGORIES = {
    "Authentication",
    "Billing",
    "Technical Issue",
    "Feature Request",
    "Bug Report",
    "Account Management",
    "General Inquiry",
    "Refund",
    "Subscription",
    "Security",
}
ALLOWED_URGENCIES = {"Low", "Medium", "High"}
ALLOWED_TEAMS = {
    "Technical Support",
    "Billing Team",
    "Security Team",
    "Customer Success",
    "Product Team",
    "Engineering",
}

CSV_FIELDS = ["id", "timestamp", "subject", "body", "category", "urgency", "confidence", "team", "reason"]


def _serialize_payload(payload: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    return [item.model_dump() if hasattr(item, "model_dump") else item for item in payload]


def _ensure_output_file(path: str, *, is_json: bool) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if is_json:
        if not output_path.exists():
            output_path.write_text("[]", encoding="utf-8")
    else:
        if not output_path.exists():
            with output_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
                writer.writeheader()

    return output_path


def build_ticket_record(ticket: Any, classification: Any) -> dict[str, Any]:
    """Create a storage-ready ticket record from the original request and classification result."""
    subject = getattr(ticket, "subject", None) if not isinstance(ticket, dict) else ticket.get("subject", "")
    body = getattr(ticket, "body", None) if not isinstance(ticket, dict) else ticket.get("body", "")
    if isinstance(classification, dict):
        category = classification.get("category", "")
        urgency = classification.get("urgency", "")
        confidence = classification.get("confidence", 0.0)
        team = classification.get("team", "")
        reason = classification.get("reason", "")
        timestamp = classification.get("timestamp", datetime.now(timezone.utc).isoformat())
    else:
        category = getattr(classification, "category", "")
        urgency = getattr(classification, "urgency", "")
        confidence = getattr(classification, "confidence", 0.0)
        team = getattr(classification, "team", "")
        reason = getattr(classification, "reason", "")
        timestamp = getattr(classification, "timestamp", datetime.now(timezone.utc).isoformat())

    return {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "subject": str(subject or "").strip(),
        "body": str(body or "").strip(),
        "category": str(category or "").strip(),
        "urgency": str(urgency or "").strip(),
        "confidence": round(float(confidence or 0.0), 2),
        "team": str(team or "").strip(),
        "reason": str(reason or "").strip(),
    }


def initialize_output_files() -> None:
    """Create the output directory and initialize the JSON/CSV files if needed."""
    _ensure_output_file("output/results.json", is_json=True)
    _ensure_output_file("output/results.csv", is_json=False)


def load_ticket_history(path: str = "output/results.json") -> list[dict[str, Any]]:
    """Load all stored tickets from the JSON archive."""
    output_path = _ensure_output_file(path, is_json=True)
    try:
        with output_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError("Stored ticket history file is corrupted") from exc

    if not isinstance(payload, list):
        raise ValueError("Stored ticket history must be a JSON array")

    return [item for item in payload if isinstance(item, dict)]


def save_ticket_json(ticket_record: dict[str, Any], path: str = "output/results.json") -> None:
    """Append a single ticket record to the JSON archive."""
    records = load_ticket_history(path)
    records.append(ticket_record)
    _write_json_records(path, records)


def save_ticket_csv(ticket_record: dict[str, Any], path: str = "output/results.csv") -> None:
    """Append a single ticket record to the CSV archive."""
    output_path = _ensure_output_file(path, is_json=False)
    with output_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writerow(ticket_record)


def save_batch_json(ticket_records: list[dict[str, Any]], path: str = "output/results.json") -> None:
    """Append multiple ticket records to the JSON archive."""
    records = load_ticket_history(path)
    records.extend(ticket_records)
    _write_json_records(path, records)


def save_batch_csv(ticket_records: list[dict[str, Any]], path: str = "output/results.csv") -> None:
    """Append multiple ticket records to the CSV archive."""
    output_path = _ensure_output_file(path, is_json=False)
    with output_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        for record in ticket_records:
            writer.writerow(record)


def _write_json_records(path: str, records: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def save_json_output(path: str, payload: list[dict[str, Any]] | list[Any]) -> None:
    """Backward-compatible JSON export helper for batch results."""
    serializable_payload = _serialize_payload(payload)
    save_batch_json(serializable_payload, path=path)


def save_csv_output(path: str, payload: list[dict[str, Any]] | list[Any]) -> None:
    """Backward-compatible CSV export helper for batch results."""
    rows = _serialize_payload(payload)
    save_batch_csv(rows, path=path)


def validate_output(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Model output must be a JSON object")

    category = str(payload.get("category", "")).strip()
    urgency = str(payload.get("urgency", "")).strip()
    team = str(payload.get("team", "")).strip()
    reason = str(payload.get("reason", "")).strip()

    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")
    if urgency not in ALLOWED_URGENCIES:
        raise ValueError(f"Invalid urgency: {urgency}")
    if team not in ALLOWED_TEAMS:
        raise ValueError(f"Invalid team: {team}")
    if not reason:
        reason = "Customer issue routed based on ticket content."

    try:
        confidence_value = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence_value = 0.0
    confidence_value = round(max(0.0, min(1.0, confidence_value)), 2)

    return {
        "category": category,
        "urgency": urgency,
        "confidence": confidence_value,
        "team": team,
        "reason": reason,
    }
