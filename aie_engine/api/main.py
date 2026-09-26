from datetime import timedelta
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.auth import require_api_key
from ..core.config import get_settings
from ..db.models import Job,JobStatus,Result,TERMINAL
from ..db.session import get_session,init_db
from ..workers.tasks import process_job
from .schemas import AnalyseRequest,CreateJobRequest,Feasibility,InspectRequest,Inspection,JobCreated,JobView
settings=get_settings()
app=FastAPI(title="ai.Encrypt Engine",version="1.0.0",docs_url="/v1/docs",openapi_url="/v1/openapi.json")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["GET","POST"],allow_headers=["Authorization","Content-Type","Idempotency-Key"])
@app.on_event("startup")
def startup(): init_db()
@app.get("/health")
def health(): return {"status":"ok","engine_version":"1.0.0"}
@app.get("/ready")
def ready(session:Session=Depends(get_session)):
 try: session.execute(select(Job.id).limit(1)); return {"status":"ready","dependencies":{"database":True,"queue":True,"object_storage":bool(settings.object_storage_endpoint)}}
 except Exception: raise HTTPException(503,"Dependencies are not ready")
@app.get("/version")
def version(): return {"engine_version":"1.0.0","aie_format_version":"1.0","runtime_version":"1.0.0"}
@app.get("/v1/capabilities",dependencies=[Depends(require_api_key)])
def capabilities(): return {"engine_version":"1.0.0","architectures":["llama","mistral","qwen","gemma","phi"],"source_formats":["safetensors"],"output_formats":["aie"],"quantisation":["int8","int6","int5","int4"],"features":{"mixed_precision":False,"pruning":False,"calibration":False,"quality_evaluation":{"reconstruction_metrics":True,"language_inference":False},"gpu":False}}
def job_view(job:Job): return JobView(job_id=job.id,status=job.status,progress=job.progress,stage=job.stage,message=job.message,updated_at=job.updated_at)
@app.post("/v1/jobs",response_model=JobCreated,dependencies=[Depends(require_api_key)])
def create_job(payload:CreateJobRequest,idempotency_key:str|None=Header(default=None),session:Session=Depends(get_session)):
 if idempotency_key:
  previous=session.scalar(select(Job).where(Job.idempotency_key==idempotency_key))
  if previous:return JobCreated(job_id=previous.id,status=previous.status)
 job=Job(request=payload.model_dump(mode="json"),idempotency_key=idempotency_key);session.add(job);session.commit();process_job.delay(job.id);return JobCreated(job_id=job.id,status=job.status)
@app.get("/v1/jobs/{job_id}",response_model=JobView,dependencies=[Depends(require_api_key)])
def get_job(job_id:str,session:Session=Depends(get_session)):
 job=session.get(Job,job_id)
 if not job:raise HTTPException(404,"Job not found")
 return job_view(job)
@app.post("/v1/jobs/{job_id}/cancel",response_model=JobView,dependencies=[Depends(require_api_key)])
def cancel(job_id:str,session:Session=Depends(get_session)):
 job=session.get(Job,job_id)
 if not job:raise HTTPException(404,"Job not found")
 if job.status not in TERMINAL:job.status=JobStatus.CANCELLED;job.message="Cancellation requested";session.commit()
 return job_view(job)
def result_response(result:Result):
 response={"result_id":result.id,"job_id":result.job_id,"status":"complete",**result.metadata_}
 try: from ..storage.s3 import S3Storage; response["download_url"]=S3Storage().signed_url(result.object_key,timedelta(hours=1))
 except Exception: response["download_url"]=None
 return response
@app.get("/v1/jobs/{job_id}/result",dependencies=[Depends(require_api_key)])
def get_result(job_id:str,session:Session=Depends(get_session)):
 result=session.scalar(select(Result).where(Result.job_id==job_id))
 if not result:raise HTTPException(404,"No completed result for this job")
 return result_response(result)
@app.get("/v1/results/{result_id}",dependencies=[Depends(require_api_key)])
def get_result_by_id(result_id:str,session:Session=Depends(get_session)):
 result=session.get(Result,result_id)
 if not result:raise HTTPException(404,"Result not found")
 return result_response(result)
@app.post("/v1/models/analyse",response_model=Feasibility,dependencies=[Depends(require_api_key)])
def analyse(payload:AnalyseRequest):
 # Feasibility is an explicitly labelled analytical estimate, never a validated result.
 estimated=int(payload.target_size_bytes*.98);return Feasibility(original_size_bytes=0,target_size_bytes=payload.target_size_bytes,feasible=payload.target_size_bytes>0,estimated_candidates=[{"size_bytes":estimated,"method":"requires_inspection"}],recommended_target_bytes=payload.target_size_bytes)
@app.post("/v1/models/inspect",dependencies=[Depends(require_api_key)])
def inspect(_:InspectRequest): raise HTTPException(501,"Inspection is performed by a worker; submit a job for untrusted remote models")
