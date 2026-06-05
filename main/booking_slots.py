"""Двухчасовые окна записи и выравнивание времени к :00 / :30."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

BOOKING_SLOT_MINUTES = 120


def align_start_datetime(work_date, t: time) -> Optional[datetime]:
    """Округляет время начала вверх до ближайших :00 или :30."""
    dt = datetime.combine(work_date, t)
    if dt.second or dt.microsecond:
        dt = dt.replace(second=0, microsecond=0)
    total_m = dt.hour * 60 + dt.minute
    if total_m % 30 != 0:
        total_m = ((total_m // 30) + 1) * 30
    h, m = divmod(total_m, 60)
    if h >= 24:
        return None
    return datetime.combine(work_date, time(h, m))


def intervals_overlap(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> bool:
    return not (a1 <= b0 or a0 >= b1)


def is_half_hour_time(t: time | None) -> bool:
    if not t:
        return True
    return t.minute in (0, 30) and t.second == 0 and t.microsecond == 0
