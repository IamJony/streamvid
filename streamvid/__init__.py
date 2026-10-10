"""
Streamvid - Video extractor from multiple streaming platforms by IamJony
"""

from .mp4upload import MP4UploadExtractor
from .filemoon import FileMoonExtractor
from .voe import VoeExtractor
from .streamtape import StreamtapeExtractor
from .universal import UniversalExtractor
from .ok import OkRuExtractor

__version__ = "1.0.0"
__all__ = [
    'MP4UploadExtractor',
    'FileMoonExtractor',
    'VoeExtractor',
    'StreamtapeExtractor',
    'UniversalExtractor',
    'OkRuExtractor'
]
