"""
数据模型模块
定义文档、分块等核心数据结构
"""

from .document import Document, DocumentStatus, DocumentType
from .chunk import Chunk, ChunkType
from .base import BaseModel

__all__ = [
    'Document',
    'DocumentStatus',
    'DocumentType',
    'Chunk',
    'ChunkType',
    'BaseModel'
]

