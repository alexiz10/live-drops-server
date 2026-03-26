from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

class BidCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)

class BidResponse(BaseModel):
    message: str
    is_winner: bool

class BidHistoryItem(BaseModel):
    amount: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
