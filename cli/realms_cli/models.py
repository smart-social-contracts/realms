"""Data models for Realms CLI configuration."""

import re
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator


class RealmMetadata(BaseModel):
    """Realm metadata configuration."""

    id: str = Field(..., description="Unique identifier for the realm")
    name: str = Field(..., description="Human-readable name of the realm")
    description: str = Field(..., description="Description of the realm's purpose")
    admin_principal: str = Field(
        ..., description="Principal ID of the realm administrator"
    )
    version: str = Field(default="1.0.0", description="Version of the realm")
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorizing the realm"
    )

    @validator("id")
    def validate_id(cls, v):
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(
                "Realm ID must contain only lowercase letters, numbers, and underscores"
            )
        return v


class DeploymentConfig(BaseModel):
    """Deployment configuration."""

    network: Literal["local", "local2", "staging", "ic"] = Field(
        ..., description="Target network for deployment"
    )
    port: Optional[int] = Field(
        None, ge=8000, le=8100, description="Port for local deployment"
    )
    identity_file: Optional[str] = Field(
        None, description="Path to identity file for deployment authentication"
    )
    clean_deploy: bool = Field(
        default=True, description="Whether to perform a clean deployment"
    )


class Extension(BaseModel):
    """Extension configuration."""

    name: str = Field(..., description="Extension name/identifier")
    version: Optional[str] = Field(None, description="Extension version")
    source: Literal["local", "package", "git"] = Field(
        default="local", description="Source type for the extension"
    )
    source_path: Optional[str] = Field(None, description="Path to extension source")
    init_params: Dict[str, Any] = Field(
        default_factory=dict, description="Initialization parameters"
    )
    enabled: bool = Field(
        default=True, description="Whether this extension should be deployed"
    )


class PostDeploymentAction(BaseModel):
    """Post-deployment action configuration."""

    type: Literal["extension_call", "script", "wait", "create_codex", "create_task"] = (
        Field(..., description="Type of post-deployment action")
    )
    name: Optional[str] = Field(None, description="Human-readable name for the action")
    extension_name: Optional[str] = Field(
        None, description="Extension to call (for extension_call type)"
    )
    function_name: Optional[str] = Field(
        None, description="Function to call (for extension_call type)"
    )
    args: Dict[str, Any] = Field(
        default_factory=dict, description="Arguments to pass to the function"
    )
    script_path: Optional[str] = Field(
        None, description="Path to script to execute (for script type)"
    )
    duration: Optional[int] = Field(
        None, description="Duration to wait in seconds (for wait type)"
    )
    codex_id: Optional[str] = Field(
        None, description="Codex ID to create (for create_codex type)"
    )
    task_id: Optional[str] = Field(
        None, description="Task ID to create (for create_task type)"
    )
    condition: Optional[str] = Field(
        None, description="Condition to check before running action"
    )
    retry_count: int = Field(default=0, description="Number of retries if action fails")
    ignore_failure: bool = Field(
        default=False, description="Whether to continue if this action fails"
    )


class SimplePostDeploymentAction(BaseModel):
    """Simple command-based post-deployment action."""

    name: str = Field(..., description="Human-readable name for the action")
    command: str = Field(..., description="Shell command to execute")
    ignore_failure: bool = Field(
        default=False, description="Whether to continue if this action fails"
    )


class PostDeploymentConfig(BaseModel):
    """Post-deployment configuration."""

    actions: List[PostDeploymentAction] = Field(
        default_factory=list, description="List of post-deployment actions"
    )


class CodexConfig(BaseModel):
    """Codex configuration."""

    name: str = Field(..., description="Human-readable name of the codex")
    description: Optional[str] = Field(
        None, description="Description of the codex's purpose"
    )
    code: Optional[str] = Field(
        None, description="Python code to execute (for inline codexes)"
    )
    url: Optional[str] = Field(
        None, description="URL to download code from (for downloadable codexes)"
    )
    checksum: Optional[str] = Field(
        None, description="SHA-256 checksum for code verification (format: sha256:hash)"
    )

    @validator("checksum")
    def validate_checksum_format(cls, v):
        if v and not v.startswith("sha256:"):
            raise ValueError('Checksum must be in format "sha256:hash"')
        return v

    def __init__(self, **data):
        super().__init__(**data)
        # Validate that either code or url is provided, but not both
        has_code = self.code is not None and self.code.strip()
        has_url = self.url is not None and self.url.strip()

        if not has_code and not has_url:
            raise ValueError("Codex must have either 'code' or 'url' specified")
        if has_code and has_url:
            raise ValueError(
                "Codex cannot have both 'code' and 'url' specified - choose one"
            )


class TaskConfig(BaseModel):
    """Task configuration."""

    name: str = Field(..., description="Human-readable name of the task")
    description: Optional[str] = Field(
        None, description="Description of the task's purpose"
    )
    codex: str = Field(..., description="ID of the codex this task should execute")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task metadata including scheduling information",
    )


class RealmConfig(BaseModel):
    """Complete realm configuration."""

    realm: RealmMetadata
    deployment: DeploymentConfig
    extensions: Dict[str, List[Extension]] = Field(
        default_factory=dict, description="Extensions organized by deployment phases"
    )
    codexes: Dict[str, CodexConfig] = Field(
        default_factory=dict, description="Codex definitions"
    )
    tasks: Dict[str, TaskConfig] = Field(
        default_factory=dict, description="Task definitions"
    )
    post_deployment: Optional[
        Union[PostDeploymentConfig, List[str], List[SimplePostDeploymentAction]]
    ] = Field(
        None,
        description="Post-deployment configuration (complex actions, simple commands, or command objects)",
    )

    @validator("extensions")
    def validate_extension_phases(cls, v):
        valid_phases = {
            "q1",
            "q2",
            "q3",
            "q4",
            "initial",
            "phase_1",
            "phase_2",
            "phase_3",
            "phase_4",
        }
        for phase in v.keys():
            if not (phase in valid_phases or re.match(r"^phase_\d+$", phase)):
                raise ValueError(
                    f"Invalid extension phase: {phase}. Must be q1-q4, initial, or phase_N"
                )
        return v
