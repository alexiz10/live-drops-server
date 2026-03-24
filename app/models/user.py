from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    supertokens_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)

    auctions: Mapped[list["Auction"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    bids: Mapped[list["Bid"]] = relationship(back_populates="bidder", cascade="all, delete-orphan")
