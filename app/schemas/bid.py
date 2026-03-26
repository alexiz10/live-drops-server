from pydantic import BaseModel, Field
from decimal import Decimal

class BidCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)

class BidResponse(BaseModel):
    message: str
    is_winner: bool