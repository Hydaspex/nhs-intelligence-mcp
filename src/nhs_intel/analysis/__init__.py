"""Pure analysis functions over domain objects."""

from nhs_intel.analysis.ranking import rank_by_wait
from nhs_intel.analysis.trend import DEFAULT_DEAD_BAND, compute_trend

__all__ = ["DEFAULT_DEAD_BAND", "compute_trend", "rank_by_wait"]
