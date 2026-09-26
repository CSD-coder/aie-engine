"""Lossy, genuine affine tensor quantisation with compact 4/5/6/8-bit packing."""
from dataclasses import dataclass
import numpy as np
@dataclass(frozen=True)
class QuantizedTensor:
    shape: tuple[int,...]; bits: int; scale: float; packed: bytes

def _pack(values: np.ndarray, bits: int) -> bytes:
    output=bytearray(); accumulator=0; pending=0
    for value in values.astype(np.uint8):
        accumulator |= int(value) << pending; pending += bits
        while pending >= 8: output.append(accumulator & 255); accumulator >>= 8; pending -= 8
    if pending: output.append(accumulator)
    return bytes(output)
def _unpack(data: bytes, count: int, bits: int) -> np.ndarray:
    values=[]; accumulator=0; pending=0
    for byte in data:
        accumulator |= byte << pending; pending += 8
        while pending >= bits and len(values)<count:
            values.append(accumulator & ((1<<bits)-1)); accumulator >>= bits; pending -= bits
    if len(values)!=count: raise ValueError("truncated quantized tensor")
    return np.asarray(values, dtype=np.int16)
def quantize(tensor: np.ndarray, bits: int) -> QuantizedTensor:
    if bits not in {4,5,6,8}: raise ValueError("supported bit widths are 4, 5, 6, and 8")
    values=np.asarray(tensor,dtype=np.float32); maximum=float(np.max(np.abs(values))) if values.size else 0.0
    scale=maximum / ((1<<(bits-1))-1) if maximum else 1.0
    signed=np.clip(np.rint(values/scale), -(1<<(bits-1)), (1<<(bits-1))-1).astype(np.int16)
    return QuantizedTensor(tuple(values.shape),bits,scale,_pack(signed+(1<<(bits-1)),bits))
def dequantize(value: QuantizedTensor) -> np.ndarray:
    unsigned=_unpack(value.packed, int(np.prod(value.shape)), value.bits)
    return ((unsigned-(1<<(value.bits-1))).astype(np.float32)*value.scale).reshape(value.shape)
def mse(original: np.ndarray, decoded: np.ndarray) -> float: return float(np.mean((original.astype(np.float32)-decoded)**2))
def sqnr_db(original: np.ndarray, decoded: np.ndarray) -> float:
    noise=np.mean((original.astype(np.float32)-decoded)**2); signal=np.mean(original.astype(np.float32)**2)
    return float(10*np.log10(signal/max(noise, np.finfo(np.float32).tiny)))
