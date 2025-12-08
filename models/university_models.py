"""Domain models for university tuition price data.

This module contains data classes representing university department
prices with full type annotations for static type checking.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UniversityDepartmentPrice:
    """Domain model representing tuition price data for a university department.

    This is a data class with full type annotations for static type checking.
    Uses Python's dataclasses for automatic __init__, __repr__, __eq__ generation.

    Attributes:
        university_name: Name of the university.
        faculty_name: Optional name of the faculty.
        department_name: Name of the department/program.
        score_type: Score type (SAY, EA, SÖZ, DİL, TYT).
        quota: Quota/placement info (e.g., "34/34").
        score: Admission score (can be None if "Dolmadı").
        ranking: Admission ranking (can be None if "Dolmadı").
        price_description: Original price text from source.
        price_amount: Numeric price value (can be None if not parseable).
        currency_code: ISO currency code (e.g., 'TRY', 'USD').
        last_scraped_at: Timestamp of when data was last scraped.
    """

    university_name: str
    faculty_name: Optional[str] = None
    department_name: str = ""
    score_type: Optional[str] = None
    quota: Optional[str] = None
    score: Optional[float] = None
    ranking: Optional[int] = None
    price_description: str = ""
    price_amount: Optional[float] = None
    currency_code: Optional[str] = None
    last_scraped_at: datetime.datetime = field(
        default_factory=datetime.datetime.utcnow
    )

    def get_composite_id(self) -> str:
        """Get a composite identifier for this entity.

        Returns:
            String in format "university_name::department_name".
        """
        return f"{self.university_name}::{self.department_name}"

    def get_formatted_price(self) -> str:
        """Get a human-readable formatted price string.

        Returns:
            Formatted price string with currency symbol.
        """
        if self.price_amount is None:
            return "N/A"

        currency_symbols = {
            'TRY': '₺',
            'USD': '$',
            'EUR': '€',
            'GBP': '£'
        }
        symbol = currency_symbols.get(self.currency_code or '', '')

        formatted_amount = f"{self.price_amount:,.2f}"
        return f"{symbol}{formatted_amount}"

    def apply_discount(self, discount_percentage: float) -> float:
        """Calculate price after applying a discount.

        Args:
            discount_percentage: Discount percentage (0-100).

        Returns:
            Discounted price amount.

        Raises:
            ValueError: If price_amount is None or discount is invalid.
        """
        if self.price_amount is None:
            raise ValueError("Cannot apply discount: price_amount is None")
        if not 0 <= discount_percentage <= 100:
            raise ValueError("Discount percentage must be between 0 and 100")

        return round(self.price_amount * (1 - discount_percentage / 100), 2)
