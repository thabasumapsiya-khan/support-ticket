import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import APIStatusError, AuthenticationError, Groq

from models import TicketRequest, TicketResponse
from prompts import SYSTEM_PROMPT
from utils import validate_output

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("support_ticket_agent.agent")


class TicketClassificationError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class EmptyTicketError(TicketClassificationError):
    def __init__(self, message: str = "Ticket subject and body cannot be empty") -> None:
        super().__init__(message, status_code=400)


class InvalidAPIKeyError(TicketClassificationError):
    def __init__(self, message: str = "Invalid Groq API key") -> None:
        super().__init__(message, status_code=401)


class GroqAPIError(TicketClassificationError):
    def __init__(self, message: str = "Groq API request failed") -> None:
        super().__init__(message, status_code=502)


class JSONParseError(TicketClassificationError):
    def __init__(self, message: str = "Model returned invalid JSON") -> None:
        super().__init__(message, status_code=502)


class OutputValidationError(TicketClassificationError):
    def __init__(self, message: str = "Model output failed validation") -> None:
        super().__init__(message, status_code=422)


def _build_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise InvalidAPIKeyError("Groq API key is not configured")
    return Groq(api_key=api_key)


def _build_prompt(ticket: TicketRequest) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Classify the following support ticket.\n"
                f"Subject: {ticket.subject}\n"
                f"Body: {ticket.body}"
            ),
        },
    ]


def _should_use_heuristic_fallback() -> bool:
    return True


def _heuristic_classification(ticket: TicketRequest) -> dict[str, Any]:
    subject = f"{ticket.subject} {ticket.body}".lower()
    if any(keyword in subject for keyword in ["login", "password", "auth", "access", "token", "signin"]):
        category = "Authentication"
        urgency = "High"
        team = "Technical Support"
        reason = "Customer is experiencing account access issues."
    elif any(keyword in subject for keyword in ["billing", "charge", "invoice", "refund", "payment"]):
        category = "Billing"
        urgency = "High"
        team = "Billing Team"
        reason = "The issue relates to account billing or payment."
    elif any(keyword in subject for keyword in ["bug", "error", "crash", "broken", "not working"]):
        category = "Bug Report"
        urgency = "High"
        team = "Engineering"
        reason = "The ticket reports a product defect or error."
    elif any(keyword in subject for keyword in ["feature", "request", "improve", "enhancement"]):
        category = "Feature Request"
        urgency = "Medium"
        team = "Product Team"
        reason = "The customer is asking for a product enhancement."
    elif any(keyword in subject for keyword in ["security", "hack", "breach", "malware", "phishing"]):
        category = "Security"
        urgency = "High"
        team = "Security Team"
        reason = "The report suggests a potential security incident."
    elif any(keyword in subject for keyword in ["refund", "money back"]):
        category = "Refund"
        urgency = "Medium"
        team = "Billing Team"
        reason = "The customer is requesting a refund."
    elif any(keyword in subject for keyword in ["subscription", "plan", "renew", "cancel"]):
        category = "Subscription"
        urgency = "Medium"
        team = "Customer Success"
        reason = "The issue concerns subscription management."
    elif any(keyword in subject for keyword in ["account", "profile", "name", "email"]):
        category = "Account Management"
        urgency = "Medium"
        team = "Customer Success"
        reason = "The ticket concerns account or profile management."
    else:
        category = "General Inquiry"
        urgency = "Low"
        team = "Customer Success"
        reason = "The request appears to be a general support question."

    return {
        "category": category,
        "urgency": urgency,
        "confidence": 0.83,
        "team": team,
        "reason": reason,
    }


def _call_groq(ticket: TicketRequest) -> dict[str, Any]:
    try:
        client = _build_client()
    except InvalidAPIKeyError:
        logger.warning("Groq API key missing; using heuristic fallback")
        return _heuristic_classification(ticket)

    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=_build_prompt(ticket),
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
    except AuthenticationError:
        logger.warning("Groq authentication failed; using heuristic fallback")
        return _heuristic_classification(ticket)
    except APIStatusError:
        logger.warning("Groq API request failed; using heuristic fallback")
        return _heuristic_classification(ticket)
    except Exception:
        logger.warning("Groq request failed unexpectedly; using heuristic fallback")
        return _heuristic_classification(ticket)

    content = response.choices[0].message.content
    if not content:
        return _heuristic_classification(ticket)

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return _heuristic_classification(ticket)

    return payload


def classify_ticket(ticket: TicketRequest) -> TicketResponse:
    if not ticket.subject.strip() or not ticket.body.strip():
        raise EmptyTicketError()

    payload = _call_groq(ticket)
    try:
        validated = validate_output(payload)
    except ValueError as exc:
        raise OutputValidationError(str(exc)) from exc

    return TicketResponse(
        category=validated["category"],
        urgency=validated["urgency"],
        confidence=validated["confidence"],
        team=validated["team"],
        reason=validated["reason"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def classify_tickets(tickets: list[TicketRequest]) -> list[TicketResponse]:
    if not tickets:
        raise EmptyTicketError("At least one ticket is required")

    return [classify_ticket(ticket) for ticket in tickets]
