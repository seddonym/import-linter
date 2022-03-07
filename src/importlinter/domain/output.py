import enum


@enum.unique
class AlertLevel(enum.Enum):
    NONE = "none"
    WARN = "warn"
    ERROR = "error"
