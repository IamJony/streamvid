"""Extractores de video por plataforma."""

from .filemoon import FileMoonExtractor
from .mp4upload import MP4UploadExtractor
from .okru import OkRuExtractor
from .streamtape import StreamtapeExtractor
from .universal import UniversalExtractor
from .voe import VoeExtractor

EXTRACTORS = [
    FileMoonExtractor,
    MP4UploadExtractor,
    OkRuExtractor,
    StreamtapeExtractor,
    VoeExtractor,
    UniversalExtractor,
]


__all__ = [
    "FileMoonExtractor",
    "MP4UploadExtractor",
    "OkRuExtractor",
    "StreamtapeExtractor",
    "UniversalExtractor",
    "VoeExtractor",
    "EXTRACTORS",
]
