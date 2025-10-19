"""
工具模块
包含文档分块、向量存储、知识图谱、实体关系提取等工具
"""

from .chunk import TextChunker
from .faiss import FaissVectorStore, OllamaEmbedding, DocumentMetadata
from .file_parser import FileParser

__all__ = [
    "TextChunker",
    "FaissVectorStore",
    "OllamaEmbedding",
    "DocumentMetadata",
    "FileParser",
]

# 可选导入（需要额外依赖）
try:
    from .neo4j import Neo4jKnowledgeGraph
    __all__.append("Neo4jKnowledgeGraph")
except ImportError:
    pass

try:
    from .chunk_to_ner import EntityRelationExtractor, Entity, Relation
    __all__.extend(["EntityRelationExtractor", "Entity", "Relation"])
except ImportError:
    pass

