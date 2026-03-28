import uuid
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "Anonymous"
    name, domain = email.split("@")
    masked_name = name[:2] + "***" if len(name) > 2 else name + "***"
    parts = domain.split(".")
    masked_domain = parts[0][:2] + "***." + ".".join(parts[1:]) if len(parts[0]) > 4 else domain
    return f"{masked_name}@{masked_domain}"

class AuctionBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str
    starting_price: Decimal = Field(..., gt=0, decimal_places=2)
    end_time: datetime

class AuctionCreate(AuctionBase):
    @field_validator('end_time')
    @classmethod
    def check_future_date(cls, v: datetime) -> datetime:
        # Ensure the date is timezone-aware and in the future
        if v.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise ValueError("Auction end time must be in the future.")
        return v

class AuctionResponse(AuctionBase):
    id: uuid.UUID
    current_price: Decimal
    owner_id: uuid.UUID
    highest_bidder_id: uuid.UUID | None = None
    highest_bidder_email: str | None = None
    user_has_participated: bool = False
    user_max_bid: Decimal | None = None

    # This tells Pydantic to read the data even if it's coming from a SQLAlchemy model
    model_config = {"from_attributes": True}

class PaginatedAuctions(BaseModel):
    items: List[AuctionResponse]
    total: int
    page: int
    size: int
    total_pages: int
