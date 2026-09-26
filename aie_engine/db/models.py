import uuid
from datetime import datetime
from enum import StrEnum
from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass
class JobStatus(StrEnum):
    QUEUED="QUEUED"; DOWNLOADING="DOWNLOADING"; INSPECTING="INSPECTING"; ANALYSING="ANALYSING"; CALIBRATING="CALIBRATING"; GENERATING_CANDIDATES="GENERATING_CANDIDATES"; OPTIMISING="OPTIMISING"; EVALUATING="EVALUATING"; VALIDATING="VALIDATING"; PACKAGING="PACKAGING"; UPLOADING="UPLOADING"; COMPLETE="COMPLETE"; FAILED="FAILED"; CANCELLED="CANCELLED"
TERMINAL={JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}
class Job(Base):
    __tablename__="jobs"
    id: Mapped[str]=mapped_column(String(48), primary_key=True, default=lambda: f"job_{uuid.uuid4().hex}")
    status: Mapped[str]=mapped_column(String(32), default=JobStatus.QUEUED)
    request: Mapped[dict]=mapped_column(JSON); progress: Mapped[int]=mapped_column(Integer, default=0)
    stage: Mapped[str]=mapped_column(String(80), default="queued"); message: Mapped[str]=mapped_column(Text, default="Waiting for a worker")
    idempotency_key: Mapped[str|None]=mapped_column(String(255), unique=True); result_id: Mapped[str|None]=mapped_column(String(48))
    error_code: Mapped[str|None]=mapped_column(String(64)); error_message: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
class Result(Base):
    __tablename__="results"
    id: Mapped[str]=mapped_column(String(48), primary_key=True, default=lambda: f"result_{uuid.uuid4().hex}")
    job_id: Mapped[str]=mapped_column(String(48), unique=True); metadata_: Mapped[dict]=mapped_column("metadata", JSON)
    object_key: Mapped[str]=mapped_column(String(512)); expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
