import enum


class AccountingMode(str, enum.Enum):
    MANUAL = 'manual'
    SQL = 'sql'


class AssignmentSource(str, enum.Enum):
    MANUAL = 'manual'
    SQL = 'sql'


class QueryRunStatus(str, enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
