# Support Ticket Triage Agent

## Project Overview

This project provides a production-ready AI support ticket triage service built with FastAPI and Groq. It accepts support tickets, classifies them into a category, urgency, confidence score, team assignment, and a short explanation, and can process both single and batch requests.

## Features

- Single-ticket and batch classification endpoints
- Groq-powered LLM classification with a safe heuristic fallback
- Strict JSON output validation
- JSON and CSV export for batch results
- Automatic persistence of each classified ticket to output/results.json and output/results.csv
- A ticket history endpoint and UI section for reviewing previous classifications
- Health endpoint and Swagger documentation
- Environment variable validation and clear HTTP error handling
- Clean modular architecture with separate concerns

## Architecture

- app.py: FastAPI application and API routes
- agent.py: classification orchestration, Groq integration, and error handling
- prompts.py: system prompt for the LLM
- models.py: Pydantic request/response schemas
- utils.py: JSON/CSV export and output validation helpers

## Folder Structure

```text
support-ticket-agent/
app.py
agent.py
prompts.py
models.py
utils.py
requirements.txt
README.md
.env.example
.gitignore
sample_data/
tickets.json
output/
results.json
results.csv
```

## Installation

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate   # Windows
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Get a Groq API key

Sign up at https://console.groq.com/ and create an API key.

### 4. Create a .env file

Copy the example file and update it:

```bash
cp .env.example .env
```

Then edit .env with your API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

## Run the Server

```bash
uvicorn app:app --reload
```

The API will be available at:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs for Swagger UI

## Example Requests

### Single ticket

```bash
curl -X POST "http://127.0.0.1:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{"subject":"Cannot login","body":"I reset my password several times."}'
```

### Batch tickets

```bash
curl -X POST "http://127.0.0.1:8000/classify-batch" \
  -H "Content-Type: application/json" \
  -d '[{"subject":"Cannot login","body":"I reset my password several times."},{"subject":"Billing issue","body":"I was charged twice."}]'
```

### Review stored tickets

```bash
curl "http://127.0.0.1:8000/tickets"
```

## Example Response

```json
{
  "category": "Authentication",
  "urgency": "High",
  "confidence": 0.97,
  "team": "Technical Support",
  "reason": "Customer cannot access account."
}
```

## Persistence

- Every single-ticket or batch classification is automatically stored after classification.
- Ticket history is persisted to output/results.json and output/results.csv.
- Reviewers can inspect previous classifications through the GET /tickets endpoint or the Previous Tickets section in the UI.

## Tradeoffs

- The application uses a heuristic fallback when the Groq API is unavailable so the service remains useful in development and demo scenarios.
- The current prompt is strong but intentionally simple to keep the project understandable and easy to extend.

## Future Improvements

- Add persistent storage with PostgreSQL or SQLite.
- Add webhook or queue-based processing.
- Add more sophisticated routing rules and human-in-the-loop review.
- Add authentication for the API endpoints.
