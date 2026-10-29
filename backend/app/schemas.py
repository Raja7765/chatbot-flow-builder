"""
Pydantic schemas for data validation and serialization in Chatbot Flow Builder.
Defines models for flow creation, updating, deletion, and responses.
"""

from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatbotStatus(str, Enum):
    """Permitted operational statuses for a chatbot."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class ChatbotCreate(BaseModel):
    """
    Schema for validating requests to create a new chatbot.
    """
    name: str = Field(..., min_length=1, description="Display name for the chatbot (required, non-empty)")
    description: Optional[str] = Field(None, description="Optional description of the chatbot")
    status: ChatbotStatus = Field(default=ChatbotStatus.ACTIVE, description="Status of the chatbot ('active' or 'inactive')")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Chatbot name cannot be empty or contain only whitespace.")
        return trimmed


class ChatbotUpdate(BaseModel):
    """
    Schema for validating requests to update an existing chatbot.
    """
    name: str = Field(..., min_length=1, description="Updated display name (required, non-empty)")
    description: Optional[str] = Field(None, description="Optional description of the chatbot")
    status: ChatbotStatus = Field(default=ChatbotStatus.ACTIVE, description="Updated status ('active' or 'inactive')")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Chatbot name cannot be empty or contain only whitespace.")
        return trimmed


class ChatbotResponse(BaseModel):
    """
    Schema for returning chatbot details to clients.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique identifier for the chatbot")
    name: str = Field(..., description="Display name of the chatbot")
    description: Optional[str] = Field(None, description="Optional description")
    status: str = Field(..., description="Chatbot status ('active' or 'inactive')")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC last updated timestamp")


class ChatbotDeleteResponse(BaseModel):
    """
    Schema for returning confirmation when a chatbot is successfully deleted.
    """
    message: str = Field(..., description="Success confirmation message")
    id: str = Field(..., description="The ID of the deleted chatbot")


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
    chatbot_id: Optional[str] = Field(None, description="ID of the chatbot this flow belongs to (defaults to system default chatbot)")
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
    chatbot_id: Optional[str] = Field(None, description="ID of the associated chatbot")
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


class NodeSource(str, Enum):
    """Permitted node origins in the flow builder system."""
    PREBUILT = "prebuilt"
    CUSTOM = "custom"


class NodeDefinitionCreate(BaseModel):
    """
    Schema for validating requests to create a new custom node definition.
    Backend strictly enforces node_source='custom' for this endpoint.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the node (e.g. 'Slack Alert')")
    node_type: str = Field(..., min_length=2, max_length=50, description="Unique stable node type slug (e.g. 'slack_alert')")
    category: str = Field(..., min_length=1, max_length=50, description="Node category (e.g. 'AI', 'Integration', 'Logic')")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the node function")
    input_schema: Optional[Dict[str, Any]] = Field(default_factory=dict, description="JSON schema describing expected node inputs")
    output_schema: Optional[Dict[str, Any]] = Field(default_factory=dict, description="JSON schema describing node outputs")
    config_schema: Optional[Dict[str, Any]] = Field(default_factory=dict, description="JSON schema describing configurable fields")
    executor_type: Optional[str] = Field(None, max_length=50, description="Optional execution handler identifier")
    executor_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional execution configuration")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Node name cannot be empty or contain only whitespace.")
        return trimmed

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Node category cannot be empty or contain only whitespace.")
        return trimmed

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, value: str) -> str:
        slug = value.strip().lower()
        if not slug:
            raise ValueError("Node type identifier cannot be empty.")
        if not re.match(r"^[a-z0-9_-]+$", slug):
            raise ValueError("Node type must only contain lowercase letters, numbers, underscores, and hyphens.")
        return slug


class NodeDefinitionUpdate(BaseModel):
    """
    Schema for validating requests to update an existing custom node definition.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated display name")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="Updated category")
    description: Optional[str] = Field(None, max_length=500, description="Updated description")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Updated input schema")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Updated output schema")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="Updated config schema")
    executor_type: Optional[str] = Field(None, max_length=50, description="Updated executor type")
    executor_config: Optional[Dict[str, Any]] = Field(None, description="Updated executor config")
    is_active: Optional[bool] = Field(None, description="Active status flag")

    @field_validator("name")
    @classmethod
    def validate_optional_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Node name cannot be empty or contain only whitespace.")
            return trimmed
        return None

    @field_validator("category")
    @classmethod
    def validate_optional_category(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Node category cannot be empty or contain only whitespace.")
            return trimmed
        return None


class NodeDefinitionResponse(BaseModel):
    """
    Schema for returning full node definition details to clients.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique identifier for the node definition")
    name: str = Field(..., description="Display name for the node")
    node_type: str = Field(..., description="Unique stable node type")
    category: str = Field(..., description="Category of the node")
    description: Optional[str] = Field(None, description="Description of the node purpose")
    node_source: str = Field(..., description="'prebuilt' or 'custom'")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Parsed input schema object")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Parsed output schema object")
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="Parsed config schema object")
    executor_type: Optional[str] = Field(None, description="Optional executor identifier")
    executor_config: Dict[str, Any] = Field(default_factory=dict, description="Parsed executor configuration")
    is_active: bool = Field(..., description="Whether the node is active and available in library")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC last update timestamp")


class NodeDefinitionDeleteResponse(BaseModel):
    """
    Schema for confirming node definition deletion or deactivation.
    """
    message: str = Field(..., description="Status explanation message")
    id: str = Field(..., description="The ID of the deleted or deactivated node")
    deactivated: bool = Field(default=False, description="True if safely deactivated instead of deleted")

