import hashlib, json, zipfile
from pathlib import Path
import numpy as np
from ..compression.quantization import QuantizedTensor, dequantize
AIE_FORMAT_VERSION="1.0"; RUNTIME_VERSION="1.0.0"
def package_aie(output:Path, tensors:dict[str,QuantizedTensor], metadata:dict) -> dict:
    entries={}; hashes={}
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_STORED) as archive:
      for index,(name,tensor) in enumerate(tensors.items()):
        path=f"weights/{index}.bin"; archive.writestr(path,tensor.packed); digest=hashlib.sha256(tensor.packed).hexdigest(); hashes[path]=digest
        entries[name]={"path":path,"shape":list(tensor.shape),"bits":tensor.bits,"scale":tensor.scale,"sha256":digest}
      manifest={"aie_format_version":AIE_FORMAT_VERSION,"runtime_min_version":"1.0.0","tensors":entries,"metadata":metadata,"hashes":hashes}
      payload=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode(); archive.writestr("manifest.json",payload); archive.writestr("manifest.sha256",hashlib.sha256(payload).hexdigest())
    return manifest
def load_aie(path:Path) -> tuple[dict,dict[str,np.ndarray]]:
 with zipfile.ZipFile(path) as archive:
  manifest_bytes=archive.read("manifest.json")
  if hashlib.sha256(manifest_bytes).hexdigest()!=archive.read("manifest.sha256").decode(): raise ValueError("manifest integrity check failed")
  manifest=json.loads(manifest_bytes)
  if not manifest["aie_format_version"].startswith("1."): raise ValueError("unsupported aie format")
  tensors={}
  for name,entry in manifest["tensors"].items():
   packed=archive.read(entry["path"])
   if hashlib.sha256(packed).hexdigest()!=entry["sha256"]: raise ValueError(f"tensor hash mismatch: {name}")
   tensors[name]=dequantize(QuantizedTensor(tuple(entry["shape"]),entry["bits"],entry["scale"],packed))
  return manifest,tensors
