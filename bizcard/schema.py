"""The lead record: one row per business card."""
from __future__ import annotations

from dataclasses import dataclass, fields

# Keys we ask the model to return (see prompts.py).
MODEL_KEYS = ("first_name", "last_name", "position", "company", "location", "phone", "email")

# Column headers shown in the UI and in the Excel file, in order.
LEAD_COLUMNS = [
    "First Name",
    "Last Name",
    "Position / Job Title",
    "Company",
    "Location",
    "Phone Number",
    "Email Address",
    "Source File",
]


@dataclass(frozen=True)
class Lead:
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    company: str = ""
    location: str = ""
    phone: str = ""
    email: str = ""
    source_file: str = ""

    def as_row(self) -> list[str]:
        """Values in the same order as LEAD_COLUMNS."""
        return [getattr(self, f.name) for f in fields(self)]

    def has_contact_info(self) -> bool:
        """False for blank cards / images where nothing useful was read."""
        return any([self.first_name, self.last_name, self.company, self.phone, self.email])
