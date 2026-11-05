"""The bug record and the column layout every backend shares."""
from dataclasses import dataclass, field
from datetime import datetime

HEADERS = [
    "Bug ID", "Project", "Module", "Severity", "Priority",
    "Title", "Description", "Steps to Reproduce",
    "Expected Result", "Actual Result",
    "Status", "Reporter", "Date Logged",
    "Evidence", "Retest Date", "Retest Result", "Retest Notes",
]

SEVERITIES = ["Critical", "High", "Medium", "Low"]
PRIORITIES = ["P1", "P2", "P3", "P4"]


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@dataclass
class Bug:
    bug_id: str
    project: str
    module: str
    severity: str
    priority: str
    title: str
    description: str
    steps: str
    expected: str
    actual: str
    reporter: str = "QA Team"
    status: str = "Open"
    evidence: list = field(default_factory=list)

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}, got {self.severity!r}")
        if self.priority not in PRIORITIES:
            raise ValueError(f"priority must be one of {PRIORITIES}, got {self.priority!r}")
        if not self.bug_id.strip():
            raise ValueError("bug_id is required")

    def to_row(self) -> list:
        return [
            self.bug_id, self.project, self.module, self.severity, self.priority,
            self.title, self.description, self.steps, self.expected, self.actual,
            self.status, self.reporter, now(), "\n".join(self.evidence), "", "", "",
        ]
