"""
Pydantic schemas for data validation and serialization in Chatbot Flow Builder.
Defines models for flow creation, updating, deletion, and responses.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlowData(BaseModel):
    """
    Schema representing the structure of a chatbot flow diagram.
    Requires 'nodes' and 'edges' arrays. Allows additional canvas metadata.
    """
    model_config = ConfigDict(extra="allow")

    nodes: List[Any] = Field(..., description="List of node objects representing steps or states")
    edges: List[Any] = Field(..., description="List of edge objects connecting nodes")


class FlowCreate(BaseModel):
    """
    Schema for validating requests to create a new flow.
    """
    name: str = Field(..., min_length=1, description="Display name for the flow (required, non-empty)")
    description: Optional[str] = Field(None, description="Optional description of the flow's purpose")
    flow_data: FlowData = Field(..., description="JSON object containing nodes and edges arrays")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        """
        Ensure the name is not just whitespace.
        """
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Flow name cannot be empty or contain only whitespace.")
        return trimmed


class FlowUpdate(FlowCreate):
    """
    Schema for validating requests to update an existing flow.
    Shares the same validation constraints as FlowCreate.
    """
    pass


class FlowResponse(BaseModel):
    """
    Schema for returning flow information to clients.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique UUID identifier for the flow")
    name: str = Field(..., description="Display name of the flow")
    description: Optional[str] = Field(None, description="Optional description of the flow")
    flow_data: FlowData = Field(..., description="The flow configuration containing nodes and edges")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC last updated timestamp")


class FlowDeleteResponse(BaseModel):
    """
    Schema for returning confirmation when a flow is successfully deleted.
    """
    message: str = Field(..., description="Success message confirming deletion")
    id: str = Field(..., description="The ID of the deleted flow")
