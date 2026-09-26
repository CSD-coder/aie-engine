import numpy as np
from aie_engine.compression.quantization import dequantize,quantize
from aie_engine.runtime.aie import load_aie,package_aie
def test_quantization_is_compact_and_round_trips(tmp_path):
 values=np.array([[-1.0,-.25,0,.5,1]],dtype=np.float32); encoded=quantize(values,4)
 assert len(encoded.packed)==2
 assert np.max(np.abs(dequantize(encoded)-values))<.2
def test_aie_integrity_and_decode(tmp_path):
 target=tmp_path/'model.aie'; package_aie(target,{'x':quantize(np.arange(8,dtype=np.float32),4)},{'architecture':'llama'})
 manifest,tensors=load_aie(target)
 assert manifest['metadata']['architecture']=='llama';assert tensors['x'].shape==(8,)
