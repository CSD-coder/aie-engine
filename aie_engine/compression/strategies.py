from abc import ABC, abstractmethod
from .quantization import QuantizedTensor, quantize
class CompressionStrategy(ABC):
 name: str
 @abstractmethod
 def transform(self, tensor, sensitivity: float=0) -> QuantizedTensor: ...
class UniformStrategy(CompressionStrategy):
 def __init__(self,bits:int): self.bits=bits; self.name=f"int{bits}"
 def transform(self,tensor,sensitivity=0): return quantize(tensor,self.bits)
class Int8Strategy(UniformStrategy):
 def __init__(self): super().__init__(8)
class Int6Strategy(UniformStrategy):
 def __init__(self): super().__init__(6)
class Int5Strategy(UniformStrategy):
 def __init__(self): super().__init__(5)
class Int4Strategy(UniformStrategy):
 def __init__(self): super().__init__(4)
class MixedPrecisionStrategy(CompressionStrategy):
 name="mixed_precision"
 def transform(self,tensor,sensitivity=0): return quantize(tensor, 8 if sensitivity>.8 else 6 if sensitivity>.5 else 4)
