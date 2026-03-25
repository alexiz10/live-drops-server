import uuid
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from decimal import Decimal

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

    # This tells Pydantic to read the data even if it's coming from a SQLAlchemy model
    model_config = {"from_attributes": True}
