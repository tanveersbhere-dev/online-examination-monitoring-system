import numpy as np
from typing import Callable, Dict, Any, TypeVar, Union

# Image represented as a numpy array
FrameImage = np.ndarray

# Callback signature for event subscribers
EventCallback = Callable[[Any], None]

# Generic payload/metadata structures
JSONDict = Dict[str, Any]

# Custom generic types if needed
T = TypeVar('T')
