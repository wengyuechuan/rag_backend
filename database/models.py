"""
数据库模型定义
使用 SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class DocumentStatusEnum(str, enum.Enum):
    """文档状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkStrategyEnum(str, enum.Enum):
    """分块策略枚举"""
    SEMANTIC = "semantic"
    FIXED = "fixed"
    RECURSIVE = "recursive"
    PARAGRAPH = "paragraph"


class MessageRoleEnum(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # 默认配置
    default_chunk_strategy = Column(SQLEnum(ChunkStrategyEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=ChunkStrategyEnum.SEMANTIC)
    default_chunk_size = Column(Integer, default=500)
    default_chunk_overlap = Column(Integer, default=100)
    
    # 是否启用功能
    enable_vector_store = Column(Boolean, default=True)
    enable_knowledge_graph = Column(Boolean, default=False)
    enable_ner = Column(Boolean, default=False)
    
    # 向量配置
    embedding_model = Column(String(100), default="nomic-embed-text")
    
    # 统计信息
    document_count = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name='{self.name}')>"


class Document(Base):
    """文档模型"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    
    # 基本信息
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(500), nullable=True)
    file_path = Column(String(1000), nullable=True)
    
    # 文档元数据
    author = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)  # 存储为 JSON 数组
    
    # 处理配置
    chunk_strategy = Column(SQLEnum(ChunkStrategyEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=True)  # None 表示使用知识库默认值
    chunk_size = Column(Integer, nullable=True)
    chunk_overlap = Column(Integer, nullable=True)
    
    # 状态
    status = Column(SQLEnum(DocumentStatusEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=DocumentStatusEnum.PENDING)
    error_message = Column(Text, nullable=True)
    
    # 统计信息
    char_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    entity_count = Column(Integer, default=0)
    relation_count = Column(Integer, default=0)
    
    # 存储标记
    vector_stored = Column(Boolean, default=False)
    graph_stored = Column(Boolean, default=False)
    
    # 处理指标
    processing_time = Column(Float, default=0.0)
    api_cost = Column(Float, default=0.0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', status='{self.status.value}')>"


class DocumentChunk(Base):
    """文档分块模型"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # 分块信息
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(50), nullable=True)
    
    # 位置信息
    start_pos = Column(Integer, default=0)
    end_pos = Column(Integer, default=0)
    
    # 统计
    char_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    
    # 向量信息
    vector_id = Column(String(200), nullable=True)  # FAISS 中的 ID
    embedding_model = Column(String(100), nullable=True)
    has_embedding = Column(Boolean, default=False)
    
    # 知识图谱信息
    entities = Column(JSON, default=list)  # 实体列表
    relations = Column(JSON, default=list)  # 关系列表
    keywords = Column(JSON, default=list)  # 关键词列表
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"


class ProcessingJob(Base):
    """处理任务模型"""
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    job_type = Column(String(50), nullable=False)  # chunking, embedding, ner
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"


class ChatSession(Base):
    """对话会话模型"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    
    # 会话信息
    title = Column(String(500), nullable=True)  # 会话标题（可从第一条消息生成）
    summary = Column(Text, nullable=True)  # 会话摘要
    
    # 配置
    use_vector_search = Column(Boolean, default=True)  # 是否使用向量搜索
    use_graph_search = Column(Boolean, default=False)  # 是否使用图谱搜索
    search_top_k = Column(Integer, default=5)  # 检索数量
    
    # 统计
    message_count = Column(Integer, default=0)  # 消息数量
    total_tokens = Column(Integer, default=0)  # 总 token 数
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    knowledge_base = relationship("KnowledgeBase")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, kb_id={self.knowledge_base_id}, msgs={self.message_count})>"


class ChatMessage(Base):
    """对话消息模型"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    
    # 消息内容
    role = Column(SQLEnum(MessageRoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    content = Column(Text, nullable=False)
    
    # RAG 相关
    retrieved_chunks = Column(JSON, default=list)  # 检索到的文本块
    retrieved_entities = Column(JSON, default=list)  # 检索到的实体（图谱搜索）
    context_used = Column(Text, nullable=True)  # 实际使用的上下文
    
    # 统计
    token_count = Column(Integer, default=0)  # token 数量
    processing_time = Column(Float, nullable=True)  # 处理时间（秒）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"

