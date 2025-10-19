"""
文档数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from .base import BaseModel


class DocumentStatus(Enum):
    """文档状态"""
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    ARCHIVED = "archived"       # 已归档


class DocumentType(Enum):
    """文档类型"""
    TEXT = "text"               # 纯文本
    PDF = "pdf"                 # PDF 文档
    WORD = "word"               # Word 文档
    HTML = "html"               # HTML 文档
    MARKDOWN = "markdown"       # Markdown 文档
    JSON = "json"               # JSON 数据
    OTHER = "other"             # 其他类型


@dataclass
class Document(BaseModel):
    """
    文档模型
    
    表示一个完整的文档，包含原始内容、元数据和处理状态
    """
    
    # 基本信息
    title: str = ""
    content: str = ""
    source: str = ""
    doc_type: DocumentType = DocumentType.TEXT
    status: DocumentStatus = DocumentStatus.PENDING
    
    # 分类和标签
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # 文件信息
    file_path: Optional[str] = None
    file_size: Optional[int] = None  # 字节
    file_hash: Optional[str] = None  # MD5 或 SHA256
    
    # 作者和来源信息
    author: Optional[str] = None
    organization: Optional[str] = None
    publish_date: Optional[datetime] = None
    
    # 处理信息
    language: str = "zh"  # 语言代码
    encoding: str = "utf-8"
    
    # 关联的分块 ID 列表
    chunk_ids: List[str] = field(default_factory=list)
    
    # 统计信息
    char_count: int = 0
    word_count: int = 0
    chunk_count: int = 0
    
    # 向量和图谱信息
    vector_stored: bool = False
    graph_stored: bool = False
    entity_count: int = 0
    relation_count: int = 0
    
    # 错误信息
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        # 自动计算统计信息
        if self.content and self.char_count == 0:
            self.char_count = len(self.content)
            self.word_count = len(self.content.split())
    
    def add_chunk(self, chunk_id: str):
        """
        添加分块 ID
        
        Args:
            chunk_id: 分块 ID
        """
        if chunk_id not in self.chunk_ids:
            self.chunk_ids.append(chunk_id)
            self.chunk_count = len(self.chunk_ids)
            self.updated_at = datetime.now()
    
    def remove_chunk(self, chunk_id: str):
        """
        移除分块 ID
        
        Args:
            chunk_id: 分块 ID
        """
        if chunk_id in self.chunk_ids:
            self.chunk_ids.remove(chunk_id)
            self.chunk_count = len(self.chunk_ids)
            self.updated_at = datetime.now()
    
    def set_status(self, status: DocumentStatus, error_message: Optional[str] = None):
        """
        设置文档状态
        
        Args:
            status: 新状态
            error_message: 错误信息（如果状态为 FAILED）
        """
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str):
        """
        添加标签
        
        Args:
            tag: 标签
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str):
        """
        移除标签
        
        Args:
            tag: 标签
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取文档摘要信息
        
        Returns:
            摘要字典
        """
        return {
            'id': self.id,
            'title': self.title,
            'source': self.source,
            'doc_type': self.doc_type.value,
            'status': self.status.value,
            'category': self.category,
            'tags': self.tags,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'chunk_count': self.chunk_count,
            'entity_count': self.entity_count,
            'relation_count': self.relation_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def is_processed(self) -> bool:
        """
        检查文档是否已处理
        
        Returns:
            是否已处理
        """
        return self.status == DocumentStatus.COMPLETED
    
    def has_chunks(self) -> bool:
        """
        检查是否有分块
        
        Returns:
            是否有分块
        """
        return len(self.chunk_ids) > 0
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Document(id={self.id[:8]}..., title='{self.title}', status={self.status.value}, chunks={self.chunk_count})"


@dataclass
class DocumentMetrics:
    """
    文档处理指标
    用于记录文档处理的各种统计信息
    """
    document_id: str
    processing_time: float = 0.0  # 秒
    chunking_time: float = 0.0
    embedding_time: float = 0.0
    ner_time: float = 0.0
    graph_storage_time: float = 0.0
    
    chunks_created: int = 0
    entities_extracted: int = 0
    relations_extracted: int = 0
    
    api_calls: int = 0
    api_cost: float = 0.0  # 美元
    
    success: bool = True
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'document_id': self.document_id,
            'processing_time': self.processing_time,
            'chunking_time': self.chunking_time,
            'embedding_time': self.embedding_time,
            'ner_time': self.ner_time,
            'graph_storage_time': self.graph_storage_time,
            'chunks_created': self.chunks_created,
            'entities_extracted': self.entities_extracted,
            'relations_extracted': self.relations_extracted,
            'api_calls': self.api_calls,
            'api_cost': self.api_cost,
            'success': self.success,
            'error_count': self.error_count
        }

