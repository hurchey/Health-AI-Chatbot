from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class PatientInfo:
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None


@dataclass
class InsuranceInfo:
    payer_name: Optional[str] = None 


@dataclass
class MedicalInfo:
    chief_complaint: Optional[str] = None


@dataclass
class DemographicsInfo:
    raw_address_line: Optional[str] = None

    formatted: Optional[str] = None
    place_id: Optional[str] = None
    is_valid: bool = False
    missing_fields: List[str] = field(default_factory=list)

    awaiting_confirmation: bool = False
    pending_formatted: Optional[str] = None
    pending_place_id: Optional[str] = None


@dataclass
class AppointmentInfo:
    provider: Optional[str] = None
    datetime: Optional[str] = None


@dataclass
class AgentState:
    current_step: str = "patient"

    patient: PatientInfo = field(default_factory=PatientInfo)
    insurance: InsuranceInfo = field(default_factory=InsuranceInfo)
    medical: MedicalInfo = field(default_factory=MedicalInfo)
    demographics: DemographicsInfo = field(default_factory=DemographicsInfo)
    appointment: AppointmentInfo = field(default_factory=AppointmentInfo)

    def to_public_dict(self) -> Dict[str, Any]:
        return asdict(self)
