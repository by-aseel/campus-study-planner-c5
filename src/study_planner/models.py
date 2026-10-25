"""Explicit output contracts shared by the service layer and MCP server."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StudyResource(BaseModel):
    """One record from the bundled, explicitly fictional demonstration catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_id: str = Field(description="Stable identifier in the sample catalog.")
    topic: str = Field(description="Canonical topic name.")
    title: str = Field(description="Title to use when creating a study task.")
    summary: str = Field(description="What this sample learning resource covers.")
    location: str = Field(description="Fictional campus location, not a real reservation or URL.")
    focus_points: list[str] = Field(description="Suggested learning objectives.")
    is_sample: Literal[True] = Field(default=True, description="Always true: this is fictional sample data.")


class StudyTask(BaseModel):
    """A durably saved study intention; it is not a calendar appointment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(description="Unique identifier generated once and persisted.")
    resource_title: str = Field(min_length=1, max_length=160, description="Normalized study resource title.")
    minutes: int = Field(ge=5, le=180, description="Planned study duration in whole minutes.")
    request_id: str = Field(min_length=1, max_length=100, description="Idempotency key supplied by the caller.")
    status: Literal["planned"] = Field(default="planned", description="New tasks are planned, not completed.")
    created_at: str = Field(description="Original creation timestamp in UTC ISO 8601 format.")


class StudyPlan(BaseModel):
    """The lookup result together with the task saved for that exact resource."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource: StudyResource
    task: StudyTask
