"""Confirmed profile versions and their freshness for personalised advice."""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import AwareDatetime

from .investable_capital import CapitalAssessment, FinancialProfile
from .models import ContractModel

RECONFIRM_AFTER = timedelta(days=31)
REMIND_AFTER = timedelta(days=24)


class ProfileFreshness(ContractModel):
    status: Literal["current", "refresh_soon", "reconfirm_required"]
    allows_new_recommendations: bool
    allows_asset_report: bool = True


class ConfirmedProfile(ContractModel):
    """Payload of one profile_versions revision; the owner reviewed this exact breakdown."""

    schema_version: Literal["1"] = "1"
    profile: FinancialProfile
    assessment: CapitalAssessment
    confirmed_at: AwareDatetime


def profile_freshness(confirmed_at: datetime, now: datetime) -> ProfileFreshness:
    if confirmed_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps require timezone")
    age = now - confirmed_at
    if age < timedelta(0) or age > RECONFIRM_AFTER:
        # A confirmation from the future signals clock skew; do not trust it.
        return ProfileFreshness(status="reconfirm_required", allows_new_recommendations=False)
    if age >= REMIND_AFTER:
        return ProfileFreshness(status="refresh_soon", allows_new_recommendations=True)
    return ProfileFreshness(status="current", allows_new_recommendations=True)
