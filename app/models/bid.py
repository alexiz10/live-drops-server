import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Numeric, DateTime, ForeignKey

from app.models.base import Base

class Bid(Base):
    __tablename__ = "bids"

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    auction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auctions.id"))
    bidder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    auction: Mapped["Auction"] = relationship(back_populates="bids")
    bidder: Mapped["User"] = relationship(back_populates="bids")
