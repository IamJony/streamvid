"""
Streamvid - Video extractor from multiple streaming platforms by IamJony
"""

from .extractors import (
    FileMoonExtractor,
    MP4UploadExtractor,
    OkRuExtractor,
    StreamtapeExtractor,
    UniversalExtractor,
    VoeExtractor,
    MixdropExtractor,
    EXTRACTORS,
)

__version__ = "1.0.0"

__all__ = [
    "FileMoonExtractor",
    "MP4UploadExtractor",
    "OkRuExtractor",
    "StreamtapeExtractor",
    "UniversalExtractor",
    "VoeExtractor",
    "MixdropExtractor",
    "EXTRACTORS",
]
