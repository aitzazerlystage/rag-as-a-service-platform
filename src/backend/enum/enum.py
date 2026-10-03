import enum


class PlanEnum(str, enum.Enum):
    """Single tier: default org quota bucket (no plan upgrades in product)."""
    free_trial = "free_trial"


class StatusEnum(str, enum.Enum):
    active = "active"
    expired = "expired"
    canceled = "canceled"
