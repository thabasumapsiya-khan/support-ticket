from pydantic import BaseModel, Field, field_validator


class TicketRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)

    @field_validator("subject", "body", mode="before")
    @classmethod
    def validate_non_empty(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Value is required")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Value cannot be empty")
            return value
        return str(value)


BatchTicketRequest = list[TicketRequest]


class TicketResponse(BaseModel):
    category: str
    urgency: str
    confidence: float = Field(ge=0.0, le=1.0)
    team: str
    reason: str
    timestamp: str
