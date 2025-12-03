from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import datetime


@dataclass
class DepartmentPrice:
    """Domain model representing a department price scraped from a university."""
    university: str
    faculty: Optional[str] = None
    department: str = ""
    price_text: str = ""
    price_value: Optional[float] = None
    currency: Optional[str] = None
    scraped_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
