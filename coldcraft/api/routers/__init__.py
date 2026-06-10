"""Versioned API routers for /api/v1."""
from .campaigns import get_campaigns_router
from .config import get_config_router
from .drafts import get_drafts_router
from .features import get_features_router
from .health import health_router
from .policies import get_policies_router
from .profile import get_profile_router
from .tracking import tracking_router

__all__ = [
    "health_router",
    "get_drafts_router",
    "get_campaigns_router",
    "get_config_router",
    "get_features_router",
    "get_policies_router",
    "get_profile_router",
    "tracking_router",
]
