"""
分块数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import numpy as np

from .base import BaseModel


class ChunkType(Enum):
    """分块类型"""
    FIXED = "fixed"              # 固定大小分块
    SEMANTIC = "semantic"        # 语义分块
    RECURSIVE = "recursive"      # 递归分块
    PARAGRAPH = "paragraph"      # 段落分块
    SENTENCE = "sentence"        # 句子分块
    CUSTOM = "custom"           # 自定义分块


@dataclass
class Chunk(BaseModel):
    """
    分块模型
    
    表示文档的一个分块，包含文本内容、向量、实体等信息
    """
    
    # 基本信息
    content: str = ""
    chunk_type: ChunkType = ChunkType.SEMANTIC
    
    # 关联信息
    document_id: str = ""  # 所属文档 ID
    parent_chunk_id: Optional[str] = None  # 父分块 ID（如果是子分块）
    child_chunk_ids: List[str] = field(default_factory=list)  # 子分块 ID 列表
    
    # 位置信息
    chunk_index: int = 0  # 在文档中的顺序
    start_pos: int = 0    # 在文档中的起始位置
    end_pos: int = 0      # 在文档中的结束位置
    
    # 内容统计
    char_count: int = 0
    word_count: int = 0
    sentence_count: int = 0
    
    # 向量信息
    embedding: Optional[np.ndarray] = None
    embedding_model: Optional[str] = None
    vector_id: Optional[str] = None  # 在向量数据库中的 ID
    
    # 知识图谱信息
    entities: List[str] = field(default_factory=list)      # 实体列表
    entity_count: int = 0
    relations: List[Dict[str, str]] = field(default_factory=list)  # 关系列表
    relation_count: int = 0
    
    # 语义信息
    keywords: List[str] = field(default_factory=list)      # 关键词
    summary: Optional[str] = None                          # 摘要
    language: str = "zh"
    
    # 质量评分
    quality_score: float = 0.0      # 0-1 之间，表示分块质量
    importance_score: float = 0.0   # 0-1 之间，表示重要性
    
    # 上下文信息
    prev_chunk_id: Optional[str] = None  # 前一个分块 ID
    next_chunk_id: Optional[str] = None  # 后一个分块 ID
    
    def __post_init__(self):
        """初始化后处理"""
        # 自动计算统计信息
        if self.content:
            if self.char_count == 0:
                self.char_count = len(self.content)
            if self.word_count == 0:
                self.word_count = len(self.content.split())
            if self.sentence_count == 0:
                # 简单的句子计数（中文）
                self.sentence_count = sum(1 for c in self.content if c in '。！？;')
        
        # 更新位置信息
        if self.start_pos == 0 and self.end_pos == 0 and self.content:
            self.end_pos = len(self.content)
    
    def set_embedding(
        self,
        embedding: np.ndarray,
        model: str,
        vector_id: Optional[str] = None
    ):
        """
        设置嵌入向量
        
        Args:
            embedding: 嵌入向量
            model: 模型名称
            vector_id: 向量数据库 ID
        """
        self.embedding = embedding
        self.embedding_model = model
        self.vector_id = vector_id
    
    def add_entity(self, entity: str):
        """
        添加实体
        
        Args:
            entity: 实体名称
        """
        if entity not in self.entities:
            self.entities.append(entity)
            self.entity_count = len(self.entities)
    
    def add_relation(self, subject: str, predicate: str, object_: str):
        """
        添加关系
        
        Args:
            subject: 主体
            predicate: 谓语
            object_: 客体
        """
        relation = {
            'subject': subject,
            'predicate': predicate,
            'object': object_
        }
        self.relations.append(relation)
        self.relation_count = len(self.relations)
    
    def add_keyword(self, keyword: str):
        """
        添加关键词
        
        Args:
            keyword: 关键词
        """
        if keyword not in self.keywords:
            self.keywords.append(keyword)
    
    def has_embedding(self) -> bool:
        """
        检查是否有嵌入向量
        
        Returns:
            是否有嵌入
        """
        return self.embedding is not None
    
    def has_entities(self) -> bool:
        """
        检查是否有实体
        
        Returns:
            是否有实体
        """
        return len(self.entities) > 0
    
    def get_text_preview(self, length: int = 100) -> str:
        """
        获取文本预览
        
        Args:
            length: 预览长度
            
        Returns:
            预览文本
        """
        if len(self.content) <= length:
            return self.content
        return self.content[:length] + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（覆盖基类方法以处理特殊字段）
        
        Returns:
            字典表示
        """
        data = super().to_dict()
        
        # 处理 numpy 数组
        if self.embedding is not None:
            data['embedding'] = self.embedding.tolist()
        
        # 处理枚举
        data['chunk_type'] = self.chunk_type.value
        
        return data
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取分块摘要信息
        
        Returns:
            摘要字典
        """
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'chunk_type': self.chunk_type.value,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'entity_count': self.entity_count,
            'relation_count': self.relation_count,
            'has_embedding': self.has_embedding(),
            'preview': self.get_text_preview(50)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        preview = self.get_text_preview(30)
        return f"Chunk(id={self.id[:8]}..., doc={self.document_id[:8]}..., idx={self.chunk_index}, text='{preview}')"


@dataclass
class ChunkRelation:
    """
    分块关系模型
    用于表示分块之间的关系
    """
    source_chunk_id: str
    target_chunk_id: str
    relation_type: str  # "next", "parent", "similar", "reference" 等
    weight: float = 1.0  # 关系权重
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_chunk_id': self.source_chunk_id,
            'target_chunk_id': self.target_chunk_id,
            'relation_type': self.relation_type,
            'weight': self.weight,
            'metadata': self.metadata
        }

