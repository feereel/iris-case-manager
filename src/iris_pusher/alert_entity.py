from dataclasses import dataclass
from typing import List

@dataclass
class AlertData:
    case_name: str
    case_description: str
    case_customer: str | int
    case_classification: str | int
    soc_id: str
    custom_attributes: dict = None