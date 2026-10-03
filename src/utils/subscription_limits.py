"""Default quota limits for new organizations (single free_trial tier)."""

from backend.models import Subscription


def set_plan_limits(subscription: Subscription) -> None:
    """
    Apply generous default limits for every org (shared platform keys from env).
    """
    subscription.monthly_limit_tokens = 50_000_000
    subscription.monthly_limit_queries = 5_000_000
    subscription.monthly_limit_ingest = 1_000_000
    subscription.monthly_limit_storage_mb = 500_000
