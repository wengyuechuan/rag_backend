"""
API 数据模型（Pydantic schemas）
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚举类型 ====================

class ChunkStrategy(str, Enum):
    """分块策略"""
    SEMANTIC = "semantic"
    FIXED = "fixed"
    RECURSIVE = "recursive"
    PARAGRAPH = "paragraph"


class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== 知识库相关 ====================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库的请求模型"""
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    
    # 默认配置
    default_chunk_strategy: ChunkStrategy = Field(ChunkStrategy.SEMANTIC, description="默认分块策略")
    default_chunk_size: int = Field(500, ge=100, le=2000, description="默认分块大小")
    default_chunk_overlap: int = Field(100, ge=0, le=500, description="默认分块重叠")
    
    # 功能开关
    enable_vector_store: bool = Field(True, description="是否启用向量存储")
    enable_knowledge_graph: bool = Field(False, description="是否启用知识图谱")
    enable_ner: bool = Field(False, description="是否启用实体关系提取")
    
    # 向量配置
    embedding_model: str = Field("nomic-embed-text", description="嵌入模型")
    
    @validator('default_chunk_overlap')
    def validate_overlap(cls, v, values):
        if 'default_chunk_size' in values and v >= values['default_chunk_size']:
            raise ValueError('chunk_overlap 必须小于 chunk_size')
        return v


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库的请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    default_chunk_strategy: Optional[ChunkStrategy] = None
    default_chunk_size: Optional[int] = Field(None, ge=100, le=2000)
    default_chunk_overlap: Optional[int] = Field(None, ge=0, le=500)
    enable_vector_store: Optional[bool] = None
    enable_knowledge_graph: Optional[bool] = None
    enable_ner: Optional[bool] = None
    embedding_model: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    """知识库响应模型"""
    id: int
    name: str
    description: Optional[str]
    default_chunk_strategy: str
    default_chunk_size: int
    default_chunk_overlap: int
    enable_vector_store: bool
    enable_knowledge_graph: bool
    enable_ner: bool
    embedding_model: str
    document_count: int
    total_chunks: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 文档相关 ====================

class DocumentCreate(BaseModel):
    """创建文档的请求模型"""
    knowledge_base_id: int = Field(..., description="知识库ID")
    title: str = Field(..., min_length=1, max_length=500, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    source: Optional[str] = Field(None, max_length=500, description="文档来源")
    
    # 元数据
    author: Optional[str] = Field(None, max_length=200, description="作者")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    
    # 处理配置（可选，不填则使用知识库默认值）
    chunk_strategy: Optional[ChunkStrategy] = Field(None, description="分块策略")
    chunk_size: Optional[int] = Field(None, ge=100, le=2000, description="分块大小")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500, description="分块重叠")
    
    # 是否自动处理
    auto_process: bool = Field(True, description="是否自动处理（分块、向量化等）")


class DocumentUpdate(BaseModel):
    """更新文档的请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    source: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    status: Optional[DocumentStatus] = None


class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: int
    knowledge_base_id: int
    title: str
    source: Optional[str]
    author: Optional[str]
    category: Optional[str]
    tags: List[str]
    status: str
    char_count: int
    word_count: int
    chunk_count: int
    entity_count: int
    relation_count: int
    vector_stored: bool
    graph_stored: bool
    processing_time: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应模型（包含内容）"""
    content: str
    chunk_strategy: Optional[str]
    chunk_size: Optional[int]
    chunk_overlap: Optional[int]
    error_message: Optional[str]
    processed_at: Optional[datetime]


# ==================== 分块相关 ====================

class ChunkResponse(BaseModel):
    """分块响应模型"""
    id: int
    document_id: int
    content: str
    chunk_index: int
    char_count: int
    has_embedding: bool
    entities: List[str]
    keywords: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 搜索相关 ====================

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., min_length=1, description="搜索查询")
    knowledge_base_id: Optional[int] = Field(None, description="限定知识库")
    top_k: int = Field(5, ge=1, le=50, description="返回结果数量")
    use_vector: bool = Field(True, description="是否使用向量检索")
    use_graph: bool = Field(False, description="是否使用图谱检索")


class SearchResult(BaseModel):
    """搜索结果项"""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    score: float
    chunk_index: int
    
    # 图谱增强信息（当 use_graph=true 时）
    entities: Optional[List[str]] = None
    relations: Optional[List[Dict[str, Any]]] = None
    graph_context: Optional[Dict[str, Any]] = None  # 图谱上下文


class GraphSearchResult(BaseModel):
    """图谱搜索结果"""
    entity_name: str
    entity_type: str
    related_entities: List[Dict[str, str]]  # 相关实体
    relations: List[Dict[str, Any]]  # 关系列表
    chunk_ids: List[str]  # 相关文本块
    relevance_score: float


class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str
    results: List[SearchResult]
    total: int
    processing_time: float
    
    # 图谱搜索结果（当 use_graph=true 时）
    graph_results: Optional[List[GraphSearchResult]] = None
    search_type: str = "vector"  # "vector", "graph", "hybrid"


# ==================== 统计相关 ====================

class StatisticsResponse(BaseModel):
    """统计信息响应"""
    total_knowledge_bases: int
    total_documents: int
    total_chunks: int
    documents_by_status: Dict[str, int]
    storage_info: Dict[str, Any]


# ==================== 通用响应 ====================

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    error_code: Optional[str] = None


# ==================== 对话相关 ====================

class ChatSessionCreate(BaseModel):
    """创建会话请求"""
    knowledge_base_id: int = Field(..., description="知识库ID")
    title: Optional[str] = Field(None, max_length=500, description="会话标题")
    use_vector_search: bool = Field(True, description="是否使用向量搜索")
    use_graph_search: bool = Field(False, description="是否使用图谱搜索")
    search_top_k: int = Field(5, ge=1, le=20, description="检索数量")


class ChatSessionUpdate(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(None, max_length=500, description="会话标题")
    use_vector_search: Optional[bool] = Field(None, description="是否使用向量搜索")
    use_graph_search: Optional[bool] = Field(None, description="是否使用图谱搜索")
    search_top_k: Optional[int] = Field(None, ge=1, le=20, description="检索数量")


class ChatSessionResponse(BaseModel):
    """会话响应"""
    id: int
    knowledge_base_id: int
    title: Optional[str]
    summary: Optional[str]
    use_vector_search: bool
    use_graph_search: bool
    search_top_k: int
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """消息响应"""
    id: int
    session_id: int
    role: str
    content: str
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    retrieved_entities: Optional[List[Dict[str, Any]]] = None
    context_used: Optional[str] = None
    token_count: int
    processing_time: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """对话请求"""
    session_id: int = Field(..., description="会话ID")
    message: str = Field(..., min_length=1, description="用户消息")
    stream: bool = Field(True, description="是否流式返回")
    temperature: float = Field(0.7, ge=0, le=2, description="生成温度")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="最大生成长度")


class ChatHistoryResponse(BaseModel):
    """会话历史响应"""
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
    total: int

