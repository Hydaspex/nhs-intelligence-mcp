"""Data-source adapters behind the source protocols."""

from nhs_intel.sources.cqc import CqcRatingSource, UrllibHttpClient
from nhs_intel.sources.identity import TrustIdentityMap
from nhs_intel.sources.identity_db import TrustIdentityDbMap
from nhs_intel.sources.planned_care import PlannedCareCsvSource
from nhs_intel.sources.planned_care_db import PlannedCareDbSource
from nhs_intel.sources.protocol import (
    CurrentWaitSource,
    HttpClient,
    RatingSource,
    WaitTimeSource,
)
from nhs_intel.sources.rtt import RttCsvSource
from nhs_intel.sources.rtt_db import RttDbSource

__all__ = [
    "CqcRatingSource",
    "CurrentWaitSource",
    "HttpClient",
    "PlannedCareCsvSource",
    "PlannedCareDbSource",
    "RatingSource",
    "RttCsvSource",
    "RttDbSource",
    "TrustIdentityDbMap",
    "TrustIdentityMap",
    "UrllibHttpClient",
    "WaitTimeSource",
]
