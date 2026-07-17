import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from agent import (
    EmptyTicketError,
    GroqAPIError,
    InvalidAPIKeyError,
    JSONParseError,
    OutputValidationError,
    classify_ticket,
    classify_tickets,
)
from models import BatchTicketRequest, TicketRequest, TicketResponse
from utils import (
    build_ticket_record,
    initialize_output_files,
    load_ticket_history,
    save_batch_csv,
    save_batch_json,
    save_ticket_csv,
    save_ticket_json,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("support_ticket_agent")

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Support Ticket Triage Agent",
    description="Classify support tickets into categories, urgency levels, and team routing.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

initialize_output_files()


def load_index_page() -> str:
    return (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/", tags=["General"], response_model=None)
def root(request: Request) -> HTMLResponse | dict[str, str]:
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(load_index_page())
    return {"message": "Support Ticket Triage Agent Running"}


@app.get("/health", tags=["General"])
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "environment": "development",
    }


@app.post("/classify", response_model=TicketResponse, tags=["Classification"])
def classify_single_ticket(ticket: TicketRequest) -> TicketResponse:
    try:
        result = classify_ticket(ticket)
    except EmptyTicketError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidAPIKeyError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except GroqAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except JSONParseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except OutputValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    record = build_ticket_record(ticket, result)
    save_ticket_json(record)
    save_ticket_csv(record)
    logger.info("Persisted single ticket to output files")
    return result


@app.post("/classify-batch", response_model=list[TicketResponse], tags=["Classification"])
def classify_batch_tickets(tickets: BatchTicketRequest) -> list[TicketResponse]:
    if not tickets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one ticket is required")

    try:
        results = classify_tickets(list(tickets))
    except EmptyTicketError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidAPIKeyError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except GroqAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except JSONParseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except OutputValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    ticket_records = [build_ticket_record(original_ticket, result) for original_ticket, result in zip(list(tickets), results)]
    save_batch_json(ticket_records)
    save_batch_csv(ticket_records)
    logger.info("Persisted %s classified tickets to output files", len(results))
    return results


@app.get("/tickets", tags=["Tickets"])
def list_tickets() -> list[dict[str, Any]]:
    try:
        return load_ticket_history()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
