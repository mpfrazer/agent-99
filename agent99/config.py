"""Pydantic models for YAML-defined agent configuration."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class MemoryConfig(BaseModel):
    type: Literal["none", "sqlite", "chromadb"] = "none"
    path: str | None = None


class AgentConfig(BaseModel):
    name: str
    description: str = ""
    model: str
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    max_iterations: int = 20
    temperature: float = 0.7
    api_base: str | None = None
    stream_output: bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v

    @field_validator("model")
    @classmethod
    def model_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model must not be empty")
        return v

    @field_validator("max_iterations")
    @classmethod
    def max_iterations_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_iterations must be >= 1")
        return v

    @field_validator("temperature")
    @classmethod
    def temperature_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AgentConfig":
        path = Path(path)
        try:
            raw = yaml.safe_load(path.read_text())
        except FileNotFoundError:
            raise ValueError(f"Agent config file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")
        try:
            return cls.model_validate(raw)
        except ValidationError as e:
            raise ValueError(f"Invalid agent config in {path}:\n{e}") from e
