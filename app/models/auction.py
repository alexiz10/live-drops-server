import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey

from app.models.base import Base

class Auction(Base):
    __tablename__ = "auctions"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    starting_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    owner: Mapped["User"] = relationship(back_populates="auctions")
    bids: Mapped[list["Bid"]] = relationship(back_populates="auction", cascade="all, delete-orphan")
