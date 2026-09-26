from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
class ModelSource(BaseModel):
    source: Literal["huggingface", "object_storage"]
    id: str = Field(min_length=1, max_length=512); revision: str | None = None
    sha256: str | None = None
class Settings(BaseModel):
    quantisation: Literal["automatic", "int8", "int6", "int5", "int4"]="automatic"
    mixed_precision: bool=True; pruning: Literal["off", "automatic"]="off"; tensor_compression: bool=True
    quality_evaluation: Literal["quick", "standard", "thorough"]="standard"
    output_format: Literal["aie"]="aie"
class CreateJobRequest(BaseModel):
    model: ModelSource; target_size_bytes: int=Field(gt=0); profile: Literal["maximum_quality", "balanced", "maximum_compression"]="balanced"; settings: Settings=Field(default_factory=Settings)
class JobCreated(BaseModel): job_id: str; status: str
class JobView(BaseModel):
    job_id: str; status: str; progress: int; stage: str; message: str; updated_at: datetime | None
class InspectRequest(BaseModel): model: ModelSource
class AnalyseRequest(CreateJobRequest): pass
class Inspection(BaseModel):
    architecture: str; parameters: int; layers: int | None; tensor_count: int; original_size_bytes: int; dtype: str; format: str; model_hash: str
class Feasibility(BaseModel):
    original_size_bytes: int; target_size_bytes: int; feasible: bool; estimated_candidates: list[dict[str, Any]]; recommended_target_bytes: int; estimate_only: bool=True
