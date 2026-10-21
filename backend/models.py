from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ModuleConfigRecord(Base):
    __tablename__ = "module_configs"
    __table_args__ = (
        CheckConstraint(
            "refresh_interval_seconds IS NULL OR "
            "(refresh_interval_seconds >= 1 AND refresh_interval_seconds <= 86400)",
            name="ck_module_configs_refresh_interval",
        ),
    )

    module_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    show_in_navigation: Mapped[bool] = mapped_column(Boolean, server_default=true())
    refresh_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
