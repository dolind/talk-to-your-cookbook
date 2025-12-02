from typing import Dict, Literal, Optional, Sequence

from pydantic import BaseModel, Field

EmbeddingPipelineTargets = Literal["local_bge", "mistralai"]


class EmbeddingJob(BaseModel):
    recipe_id: str
    user_id: str
    # which pipelines to (re)embed into; None → default to all configured
    targets: Optional[Sequence[EmbeddingPipelineTargets]] = Field(default=None)
    # if True, delete any existing chunks in the *target collection(s)* first
    reindex: bool = False
    # optional override of version label (see versioning section)
    version: Optional[str] = None


class TargetConfig(BaseModel):
    target: str
    active_version: str = "v1"
    staged_version: Optional[str] = None


class EmbeddingsConfig(BaseModel):
    targets: Dict[str, TargetConfig] = Field(
        default_factory=lambda: {
            "local_bge": TargetConfig(target="local_bge"),
            "mistralai": TargetConfig(target="mistralai"),
        }
    )
