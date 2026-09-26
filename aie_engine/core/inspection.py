import hashlib
from pathlib import Path
from safetensors import safe_open
from .errors import ErrorCode
SUPPORTED={"llama":"llama","mistral":"mistral","qwen":"qwen","gemma":"gemma","phi":"phi"}
def inspect_safetensors(path:Path, architecture_hint:str|None=None)->dict:
 if path.suffix != ".safetensors": raise ValueError(ErrorCode.UNSUPPORTED_FORMAT)
 total=0; params=0; dtypes=set(); shapes={}
 with safe_open(path,framework="numpy") as handle:
  for name in handle.keys():
   tensor=handle.get_tensor(name); total+=tensor.nbytes; params+=tensor.size; dtypes.add(str(tensor.dtype)); shapes[name]=list(tensor.shape)
 architecture=(architecture_hint or "").lower()
 if not architecture: architecture=next((a for a in SUPPORTED if a in path.name.lower()), "")
 if architecture not in SUPPORTED: raise ValueError(ErrorCode.UNSUPPORTED_ARCHITECTURE)
 layers=max((int(part) for name in shapes for part in name.split(".") if part.isdigit()),default=-1)+1 or None
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 return {"architecture":architecture,"parameters":params,"layers":layers,"tensor_count":len(shapes),"original_size_bytes":total,"dtype":",".join(sorted(dtypes)),"format":"safetensors","model_hash":digest,"tensor_shapes":shapes}
