from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class AuditMixin(SQLModel):
    __abstract__ = True
    created_by: str = Field(max_length=55, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_by: Optional[str] = Field(default=None, max_length=55, nullable=True)
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
    version: int = Field(default=1, nullable=False)
