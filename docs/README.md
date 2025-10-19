# 数据模型文档

## 📋 概述

本模块提供了 RAG 系统的核心数据模型，包括文档（Document）和分块（Chunk）的数据结构及其关联关系。

## 🏗️ 模型架构

```
BaseModel (基础模型)
    ↓
    ├── Document (文档模型)
    └── Chunk (分块模型)

DocumentRepository (数据仓库)
    ├── 管理 Documents
    ├── 管理 Chunks
    └── 管理 ChunkRelations
```

## 📦 核心模型

### 1. BaseModel (基础模型)

所有数据模型的基类，提供通用功能。

**核心字段**:
- `id`: 唯一标识符 (UUID)
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `metadata`: 元数据字典

**核心方法**:
- `to_dict()`: 转换为字典
- `to_json()`: 转换为 JSON
- `from_dict()`: 从字典创建
- `from_json()`: 从 JSON 创建

### 2. Document (文档模型)

表示一个完整的文档。

**核心字段**:
```python
@dataclass
class Document(BaseModel):
    # 基本信息
    title: str              # 标题
    content: str            # 内容
    source: str             # 来源
    doc_type: DocumentType  # 类型 (TEXT, PDF, WORD, etc.)
    status: DocumentStatus  # 状态 (PENDING, PROCESSING, COMPLETED, etc.)
    
    # 分类
    category: str           # 分类
    tags: List[str]         # 标签
    
    # 关联
    chunk_ids: List[str]    # 关联的分块 ID
    
    # 统计
    char_count: int         # 字符数
    word_count: int         # 词数
    chunk_count: int        # 分块数
    entity_count: int       # 实体数
    relation_count: int     # 关系数
```

**状态枚举**:
```python
class DocumentStatus(Enum):
    PENDING = "pending"         # 待处理
    PROCESSING = "processing"   # 处理中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 失败
    ARCHIVED = "archived"      # 已归档
```

**类型枚举**:
```python
class DocumentType(Enum):
    TEXT = "text"
    PDF = "pdf"
    WORD = "word"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    OTHER = "other"
```

**常用方法**:
- `add_chunk(chunk_id)`: 添加分块
- `remove_chunk(chunk_id)`: 移除分块
- `set_status(status)`: 设置状态
- `add_tag(tag)`: 添加标签
- `get_summary()`: 获取摘要
- `is_processed()`: 是否已处理
- `has_chunks()`: 是否有分块

### 3. Chunk (分块模型)

表示文档的一个分块。

**核心字段**:
```python
@dataclass
class Chunk(BaseModel):
    # 基本信息
    content: str            # 内容
    chunk_type: ChunkType   # 类型 (SEMANTIC, FIXED, etc.)
    
    # 关联
    document_id: str        # 所属文档 ID
    parent_chunk_id: str    # 父分块 ID
    child_chunk_ids: List[str]  # 子分块 ID
    
    # 位置
    chunk_index: int        # 在文档中的序号
    start_pos: int          # 起始位置
    end_pos: int            # 结束位置
    
    # 向量
    embedding: np.ndarray   # 嵌入向量
    embedding_model: str    # 模型名称
    vector_id: str          # 向量库 ID
    
    # 知识图谱
    entities: List[str]     # 实体列表
    relations: List[Dict]   # 关系列表
    
    # 语义
    keywords: List[str]     # 关键词
    summary: str            # 摘要
```

**分块类型枚举**:
```python
class ChunkType(Enum):
    FIXED = "fixed"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    CUSTOM = "custom"
```

**常用方法**:
- `set_embedding(embedding, model)`: 设置嵌入向量
- `add_entity(entity)`: 添加实体
- `add_relation(subject, predicate, object)`: 添加关系
- `add_keyword(keyword)`: 添加关键词
- `has_embedding()`: 是否有嵌入
- `has_entities()`: 是否有实体
- `get_text_preview(length)`: 获取文本预览

### 4. DocumentRepository (数据仓库)

管理文档和分块的存储、查询。

**核心功能**:

#### 文档操作
```python
# 添加文档
doc_id = repo.add_document(document)

# 获取文档
doc = repo.get_document(doc_id)

# 更新文档
repo.update_document(document)

# 删除文档
repo.delete_document(doc_id, delete_chunks=True)

# 查找文档
docs = repo.find_documents(
    status=DocumentStatus.COMPLETED,
    category="AI",
    tags=["机器学习"]
)
```

#### 分块操作
```python
# 添加分块
chunk_id = repo.add_chunk(chunk)

# 获取分块
chunk = repo.get_chunk(chunk_id)

# 获取文档的所有分块
chunks = repo.get_document_chunks(doc_id)

# 查找分块
chunks = repo.find_chunks(
    document_id=doc_id,
    has_embedding=True,
    has_entities=True
)
```

#### 关系操作
```python
# 添加分块关系
relation = ChunkRelation(
    source_chunk_id=chunk1.id,
    target_chunk_id=chunk2.id,
    relation_type="next"
)
repo.add_chunk_relation(relation)

# 获取关系
relations = repo.get_chunk_relations(
    source_chunk_id=chunk1.id,
    relation_type="next"
)
```

#### 持久化
```python
# 保存到文件
repo.save_to_file("./data/repository.json")

# 从文件加载
repo = DocumentRepository.load_from_file("./data/repository.json")
```

#### 统计分析
```python
stats = repo.get_statistics()
# {
#     'total_documents': 10,
#     'total_chunks': 50,
#     'documents_by_status': {...},
#     'documents_by_category': {...},
#     'avg_chunks_per_doc': 5.0,
#     ...
# }
```

## 💡 使用示例

### 示例 1: 创建文档和分块

```python
from models import Document, Chunk, DocumentType, ChunkType

# 创建文档
doc = Document(
    title="人工智能简介",
    content="AI 是计算机科学的一个分支...",
    source="教程",
    doc_type=DocumentType.TEXT,
    category="技术"
)

# 添加标签
doc.add_tag("AI")
doc.add_tag("机器学习")

# 创建分块
chunk = Chunk(
    content="AI 是计算机科学的一个分支...",
    document_id=doc.id,
    chunk_index=0,
    chunk_type=ChunkType.SEMANTIC
)

# 关联分块
doc.add_chunk(chunk.id)
```

### 示例 2: 使用仓库管理

```python
from models import DocumentRepository

# 创建仓库
repo = DocumentRepository()

# 添加文档和分块
repo.add_document(doc)
repo.add_chunk(chunk)

# 查找文档
ai_docs = repo.find_documents(category="技术")

# 获取文档的分块
chunks = repo.get_document_chunks(doc.id)

# 统计信息
stats = repo.get_statistics()
print(f"总文档数: {stats['total_documents']}")
```

### 示例 3: 完整工作流

```python
from models import Document, Chunk, DocumentStatus, DocumentRepository
import numpy as np

# 初始化
repo = DocumentRepository()

# 1. 创建并添加文档
doc = Document(
    title="深度学习教程",
    content="深度学习是机器学习的分支...",
    source="在线课程",
    category="AI"
)
doc.set_status(DocumentStatus.PROCESSING)
repo.add_document(doc)

# 2. 分块并添加
chunk = Chunk(
    content="深度学习是机器学习的分支...",
    document_id=doc.id,
    chunk_type=ChunkType.SEMANTIC
)

# 3. 设置嵌入向量
embedding = np.random.rand(768).astype(np.float32)
chunk.set_embedding(embedding, "nomic-embed-text")

# 4. 添加知识
chunk.add_entity("深度学习")
chunk.add_entity("机器学习")
chunk.add_relation("深度学习", "IS_PART_OF", "机器学习")

repo.add_chunk(chunk)

# 5. 完成处理
doc.set_status(DocumentStatus.COMPLETED)
doc.vector_stored = True
doc.entity_count = chunk.entity_count
repo.update_document(doc)

# 6. 保存
repo.save_to_file("./data/my_repo.json")
```

## 🔗 模型关联关系

### Document ↔ Chunk (一对多)

```python
# 文档关联分块
doc.add_chunk(chunk.id)
doc.chunk_ids  # ['chunk_1', 'chunk_2', ...]

# 分块关联文档
chunk.document_id = doc.id

# 通过仓库获取
chunks = repo.get_document_chunks(doc.id)
```

### Chunk ↔ Chunk (多对多关系)

```python
from models.repository import ChunkRelation

# 创建关系
relation = ChunkRelation(
    source_chunk_id=chunk1.id,
    target_chunk_id=chunk2.id,
    relation_type="next",  # 或 "similar", "reference" 等
    weight=1.0
)

repo.add_chunk_relation(relation)
```

### 父子分块关系

```python
# 设置父子关系
child_chunk.parent_chunk_id = parent_chunk.id
parent_chunk.child_chunk_ids.append(child_chunk.id)
```

### 前后分块关系

```python
# 设置顺序关系
chunk2.prev_chunk_id = chunk1.id
chunk1.next_chunk_id = chunk2.id
```

## 📊 数据模型 UML

```
┌─────────────────────────────────────┐
│          BaseModel                   │
├─────────────────────────────────────┤
│ + id: str                           │
│ + created_at: datetime              │
│ + updated_at: datetime              │
│ + metadata: Dict                    │
├─────────────────────────────────────┤
│ + to_dict()                         │
│ + to_json()                         │
│ + from_dict()                       │
└────────────┬────────────────────────┘
             │
    ┌────────┴──────────┐
    │                   │
    ▼                   ▼
┌─────────────┐    ┌─────────────┐
│  Document   │    │    Chunk    │
├─────────────┤    ├─────────────┤
│ title       │◄───┤ document_id │
│ content     │ 1 *│ content     │
│ chunk_ids[] │────┤ chunk_index │
│ status      │    │ embedding   │
│ category    │    │ entities[]  │
└─────────────┘    └─────────────┘
       │                  │
       └──────┬───────────┘
              │
              ▼
    ┌──────────────────┐
    │ DocumentRepository│
    ├──────────────────┤
    │ documents: Dict  │
    │ chunks: Dict     │
    │ relations: List  │
    ├──────────────────┤
    │ add_document()   │
    │ add_chunk()      │
    │ find_documents() │
    │ get_statistics() │
    └──────────────────┘
```

## 🎯 最佳实践

### 1. 文档状态管理

```python
# 创建时设置为 PENDING
doc = Document(title="...", status=DocumentStatus.PENDING)

# 开始处理时更新为 PROCESSING
doc.set_status(DocumentStatus.PROCESSING)

# 处理完成
doc.set_status(DocumentStatus.COMPLETED)

# 处理失败
doc.set_status(DocumentStatus.FAILED, error_message="...")
```

### 2. 分块索引维护

```python
# 创建分块时设置索引
for i, text in enumerate(chunk_texts):
    chunk = Chunk(
        content=text,
        document_id=doc.id,
        chunk_index=i  # 重要！维护顺序
    )
```

### 3. 元数据使用

```python
# 添加自定义元数据
doc.update_metadata("processing_version", "v1.2")
doc.update_metadata("processor", "worker-01")

# 获取元数据
version = doc.get_metadata("processing_version")
```

### 4. 查询优化

```python
# 利用索引快速查找
docs = repo.find_documents(category="AI")  # 使用索引

# 自定义过滤
docs = repo.find_documents(
    filter_func=lambda doc: doc.char_count > 1000
)
```

## 📝 注意事项

1. **ID 管理**: 所有模型的 ID 都是自动生成的 UUID，不要手动设置
2. **时间戳**: `created_at` 和 `updated_at` 会自动维护
3. **关联关系**: 添加/删除分块时，文档的 `chunk_ids` 会自动更新
4. **持久化**: 仓库支持 JSON 序列化，但 numpy 数组会转换为列表
5. **线程安全**: 当前实现不是线程安全的，多线程环境需要加锁

## 🔧 扩展建议

### 添加新字段

```python
from models import Document
from dataclasses import dataclass, field

@dataclass
class ExtendedDocument(Document):
    custom_field: str = ""
    custom_list: List[str] = field(default_factory=list)
```

### 自定义查询

```python
# 实现复杂查询逻辑
def find_large_documents(repo: DocumentRepository, min_size: int):
    return repo.find_documents(
        filter_func=lambda doc: doc.char_count >= min_size
    )
```

## 📚 更多示例

查看 `example_models_usage.py` 获取完整的使用示例。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

