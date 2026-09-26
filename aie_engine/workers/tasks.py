import shutil, tempfile
from pathlib import Path
from celery import Celery
from sqlalchemy import select
from safetensors import safe_open
from ..core.config import get_settings
from ..compression.strategies import Int4Strategy,Int5Strategy,Int6Strategy,Int8Strategy
from ..compression.quantization import dequantize,mse,sqnr_db
from ..db.models import Job,JobStatus,Result,TERMINAL
from ..db.session import SessionLocal
from ..runtime.aie import package_aie,load_aie
from ..storage.s3 import S3Storage
celery=Celery("aie_engine",broker=get_settings().redis_url,backend=get_settings().redis_url)
celery.conf.task_acks_late=True; celery.conf.worker_prefetch_multiplier=1
STAGES=[(JobStatus.DOWNLOADING,5),(JobStatus.INSPECTING,15),(JobStatus.GENERATING_CANDIDATES,25),(JobStatus.OPTIMISING,40),(JobStatus.EVALUATING,65),(JobStatus.PACKAGING,80),(JobStatus.VALIDATING,90),(JobStatus.UPLOADING,95)]
def update(session,job,status,progress,stage,message):
 job.status=status;job.progress=progress;job.stage=stage;job.message=message;session.commit()
def cancelled(session,job): return session.get(Job,job.id).status==JobStatus.CANCELLED
@celery.task(bind=True,autoretry_for=(OSError,),retry_backoff=True,retry_kwargs={"max_retries":3})
def process_job(self,job_id:str):
 with SessionLocal() as session:
  job=session.get(Job,job_id)
  if not job or job.status in TERMINAL:return
  root=Path(tempfile.mkdtemp(prefix=f"aie-{job_id}-"))
  try:
   request=job.request; model=request["model"]; update(session,job,*STAGES[0],"Acquiring model weights")
   input_path=root/"model.safetensors"
   if model["source"]=="object_storage": S3Storage().download(model["id"],input_path)
   else:
    from huggingface_hub import hf_hub_download
    downloaded=hf_hub_download(repo_id=model["id"],filename="model.safetensors",revision=model.get("revision"),token=get_settings().hf_token,local_dir=root)
    input_path=Path(downloaded)
   if cancelled(session,job):return
   update(session,job,*STAGES[1],"Inspecting safe tensor weights")
   from ..core.inspection import inspect_safetensors
   inspection=inspect_safetensors(input_path,model["id"].split("/")[-1])
   update(session,job,*STAGES[2],"Generating measured quantisation candidates")
   requested=request["settings"]["quantisation"]; candidates=[Int8Strategy(),Int6Strategy(),Int5Strategy(),Int4Strategy()] if requested=="automatic" else [{"int8":Int8Strategy(),"int6":Int6Strategy(),"int5":Int5Strategy(),"int4":Int4Strategy()}[requested]]
   selected=None
   # Candidate packages are measured after packaging; no estimated size is accepted.
   for strategy in candidates:
    if cancelled(session,job):return
    update(session,job,JobStatus.OPTIMISING,40,"quantisation",f"Transforming weights with {strategy.name}")
    quantized={}; original={}
    with safe_open(input_path,framework="numpy") as handle:
     for name in handle.keys(): original[name]=handle.get_tensor(name);quantized[name]=strategy.transform(original[name])
    candidate=root/f"{strategy.name}.aie"; package_aie(candidate,quantized,{"engine_version":"1.0.0","architecture":inspection["architecture"],"source_model":model["id"],"source_revision":model.get("revision"),"compression":{"strategy":strategy.name}})
    if candidate.stat().st_size<=request["target_size_bytes"]: selected=(strategy,candidate,original,quantized);break
   if not selected: raise ValueError("TARGET_UNACHIEVABLE")
   strategy,candidate,original,quantized=selected; update(session,job,*STAGES[4],f"Measuring reconstruction quality for {strategy.name}")
   errors=[];scores=[]
   for name,tensor in quantized.items(): errors.append(mse(original[name],dequantize(tensor)));scores.append(sqnr_db(original[name],dequantize(tensor)))
   update(session,job,*STAGES[5],"Writing versioned package with hashes")
   manifest,tensors=load_aie(candidate)
   if set(tensors)!=set(original):raise ValueError("VALIDATION_FAILED")
   update(session,job,*STAGES[6],"Verified package hashes and decoded all tensors")
   key=f"results/{job.id}/{candidate.name}"; S3Storage().upload(key,candidate)
   update(session,job,*STAGES[7],"Uploaded validated package")
   result=Result(job_id=job.id,object_key=key,metadata_={"original_size_bytes":inspection["original_size_bytes"],"result_size_bytes":candidate.stat().st_size,"target_size_bytes":request["target_size_bytes"],"compression_ratio":inspection["original_size_bytes"]/candidate.stat().st_size,"format":"aie","quality":{"weight_reconstruction_mse":sum(errors)/len(errors),"sqnr_db":sum(scores)/len(scores)},"engine_version":"1.0.0","aie_format_version":manifest["aie_format_version"],"runtime_version":"1.0.0","validation":{"integrity_verified":True,"decoded_tensor_count":len(tensors),"inference_executed":False}})
   session.add(result);session.flush();job.result_id=result.id;update(session,job,JobStatus.COMPLETE,100,"complete","Validated package is ready")
  except Exception as exc:
   job.status=JobStatus.FAILED;job.error_code=str(exc) if str(exc).isupper() else "INTERNAL_ERROR";job.error_message=str(exc);job.message="Processing failed";session.commit()
  finally: shutil.rmtree(root,ignore_errors=True)
