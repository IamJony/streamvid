"""Extractores de video por plataforma."""

from .filemoon import FileMoonExtractor
from .mp4upload import MP4UploadExtractor
from .okru import OkRuExtractor
from .streamtape import StreamtapeExtractor
from .universal import UniversalExtractor
from .voe import VoeExtractor
from .mixdrop import MixdropExtractor

EXTRACTORS = [
    FileMoonExtractor,
    MP4UploadExtractor,
    OkRuExtractor,
    StreamtapeExtractor,
    VoeExtractor,
    UniversalExtractor,
    MixdropExtractor,
]


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
