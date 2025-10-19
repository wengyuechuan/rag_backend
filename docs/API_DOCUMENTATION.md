## RAG 文档管理系统 - API 文档

## 📋 概述

这是一个基于 FastAPI 和 SQLite 的文档管理和检索系统，提供知识库管理、文档上传、自动分块、向量化和语义搜索功能。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn sqlalchemy pydantic python-multipart
```

### 2. 启动服务器

```bash
python main.py
```

服务器将在 `http://localhost:8000` 启动。

### 3. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📡 API 端点

### 根端点

#### GET `/`
获取 API 信息

#### GET `/health`
健康检查

---

## 📚 知识库管理

### POST `/api/v1/knowledge-bases/`
创建知识库

**请求体:**
```json
{
  "name": "AI 知识库",
  "description": "人工智能相关文档",
  "default_chunk_strategy": "semantic",
  "default_chunk_size": 500,
  "default_chunk_overlap": 100,
  "enable_vector_store": true,
  "enable_knowledge_graph": false,
  "enable_ner": false,
  "embedding_model": "nomic-embed-text"
}
```

**参数说明:**
- `name` (必填): 知识库名称，必须唯一
- `description`: 描述信息
- `default_chunk_strategy`: 默认分块策略
  - `semantic`: 语义分块（推荐）
  - `fixed`: 固定大小分块
  - `recursive`: 递归分块
  - `paragraph`: 段落分块
- `default_chunk_size`: 默认分块大小（100-2000）
- `default_chunk_overlap`: 默认分块重叠（0-500）
- `enable_vector_store`: 是否启用向量存储
- `enable_knowledge_graph`: 是否启用知识图谱
- `enable_ner`: 是否启用实体关系提取

**响应:**
```json
{
  "id": 1,
  "name": "AI 知识库",
  "description": "人工智能相关文档",
  "default_chunk_strategy": "semantic",
  "default_chunk_size": 500,
  "default_chunk_overlap": 100,
  "enable_vector_store": true,
  "enable_knowledge_graph": false,
  "enable_ner": false,
  "embedding_model": "nomic-embed-text",
  "document_count": 0,
  "total_chunks": 0,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### GET `/api/v1/knowledge-bases/`
获取知识库列表

**查询参数:**
- `skip`: 跳过的记录数（默认0）
- `limit`: 返回的最大记录数（默认100）

### GET `/api/v1/knowledge-bases/{kb_id}`
获取指定知识库详情

### PUT `/api/v1/knowledge-bases/{kb_id}`
更新知识库配置

**请求体:**（所有字段可选）
```json
{
  "name": "新名称",
  "description": "新描述",
  "default_chunk_size": 600
}
```

### DELETE `/api/v1/knowledge-bases/{kb_id}`
删除知识库

**查询参数:**
- `force`: 是否强制删除（即使包含文档）

---

## 📄 文档管理

### POST `/api/v1/documents/`
创建文档并添加到知识库

**请求体:**
```json
{
  "knowledge_base_id": 1,
  "title": "人工智能简介",
  "content": "人工智能是计算机科学的一个分支...",
  "source": "AI 教程",
  "author": "张三",
  "category": "技术",
  "tags": ["AI", "机器学习"],
  "chunk_strategy": "semantic",
  "chunk_size": 500,
  "chunk_overlap": 100,
  "auto_process": true
}
```

**参数说明:**
- `knowledge_base_id` (必填): 所属知识库ID
- `title` (必填): 文档标题
- `content` (必填): 文档内容
- `source`: 文档来源
- `author`: 作者
- `category`: 分类
- `tags`: 标签数组
- `chunk_strategy`: 分块策略（可选，不填则使用知识库默认值）
- `chunk_size`: 分块大小（可选）
- `chunk_overlap`: 分块重叠（可选）
- `auto_process`: 是否自动处理（默认true）

**分块策略详解:**

1. **semantic（语义分块）**：根据句子边界智能分块，保持语义完整性
   - 适用场景：一般文本、文章、教程
   - 优点：不会在句子中间截断

2. **fixed（固定大小分块）**：按固定字符数分块
   - 适用场景：需要严格控制块大小
   - 优点：块大小均匀

3. **recursive（递归分块）**：使用层级分隔符递归分块
   - 适用场景：结构化文档
   - 优点：保持文档结构

4. **paragraph（段落分块）**：按段落分块
   - 适用场景：段落清晰的文档
   - 优点：保持段落完整性

**响应:**
```json
{
  "id": 1,
  "knowledge_base_id": 1,
  "title": "人工智能简介",
  "source": "AI 教程",
  "author": "张三",
  "category": "技术",
  "tags": ["AI", "机器学习"],
  "status": "processing",
  "char_count": 0,
  "word_count": 0,
  "chunk_count": 0,
  "entity_count": 0,
  "relation_count": 0,
  "vector_stored": false,
  "graph_stored": false,
  "processing_time": 0.0,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### GET `/api/v1/documents/`
获取文档列表

**查询参数:**
- `knowledge_base_id`: 过滤知识库
- `status`: 过滤状态（pending/processing/completed/failed）
- `category`: 过滤分类
- `skip`: 跳过的记录数
- `limit`: 返回的最大记录数

**示例:**
```
GET /api/v1/documents/?knowledge_base_id=1&status=completed&limit=10
```

### GET `/api/v1/documents/{doc_id}`
获取文档详情（包含完整内容）

### PUT `/api/v1/documents/{doc_id}`
更新文档信息

**请求体:**（所有字段可选）
```json
{
  "title": "新标题",
  "category": "新分类",
  "tags": ["新标签1", "新标签2"],
  "status": "completed"
}
```

### DELETE `/api/v1/documents/{doc_id}`
删除文档及其所有分块

### POST `/api/v1/documents/{doc_id}/process`
手动触发文档处理

**查询参数:**
- `reprocess`: 是否重新处理（会删除现有分块）

**示例:**
```
POST /api/v1/documents/1/process?reprocess=true
```

### GET `/api/v1/documents/{doc_id}/chunks`
获取文档的所有分块

**查询参数:**
- `skip`: 跳过的记录数
- `limit`: 返回的最大记录数

**响应:**
```json
[
  {
    "id": 1,
    "document_id": 1,
    "content": "人工智能是计算机科学的一个分支...",
    "chunk_index": 0,
    "char_count": 150,
    "has_embedding": true,
    "entities": ["人工智能", "计算机科学"],
    "keywords": ["AI", "计算机"],
    "created_at": "2025-01-01T00:00:00"
  }
]
```

---

## 🔍 搜索功能

### POST `/api/v1/search/`
搜索文档

**请求体:**
```json
{
  "query": "什么是深度学习？",
  "knowledge_base_id": 1,
  "top_k": 5,
  "use_vector": true,
  "use_graph": false
}
```

**参数说明:**
- `query` (必填): 搜索查询文本
- `knowledge_base_id` (必填): 限定搜索的知识库
- `top_k`: 返回结果数量（1-50，默认5）
- `use_vector`: 是否使用向量检索（默认true）
- `use_graph`: 是否使用图谱检索（默认false）

**响应:**
```json
{
  "query": "什么是深度学习？",
  "results": [
    {
      "chunk_id": 3,
      "document_id": 1,
      "document_title": "人工智能简介",
      "content": "深度学习是机器学习的一个分支...",
      "score": 0.95,
      "chunk_index": 2
    }
  ],
  "total": 1,
  "processing_time": 0.123
}
```

---

## 🔄 完整工作流示例

### 1. 创建知识库

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术文档库",
    "description": "存储技术相关文档",
    "default_chunk_strategy": "semantic",
    "enable_vector_store": true
  }'
```

### 2. 上传文档

```bash
curl -X POST "http://localhost:8000/api/v1/documents/" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "title": "Python 教程",
    "content": "Python 是一种高级编程语言...",
    "category": "编程",
    "tags": ["Python", "编程"],
    "auto_process": true
  }'
```

### 3. 等待处理完成

文档会在后台自动处理（分块、向量化），状态会从 `pending` → `processing` → `completed`

### 4. 查询文档状态

```bash
curl "http://localhost:8000/api/v1/documents/1"
```

### 5. 搜索文档

```bash
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何学习 Python？",
    "knowledge_base_id": 1,
    "top_k": 3
  }'
```

---

## 📊 数据模型

### 知识库状态
- 存储配置：分块策略、向量化设置
- 统计信息：文档数、分块数
- 功能开关：向量存储、知识图谱、NER

### 文档状态
- `pending`: 待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败

### 分块信息
- 内容和位置
- 向量ID和嵌入状态
- 实体和关键词

---

## 🎯 最佳实践

### 1. 选择合适的分块策略

```python
# 一般文本 - 使用语义分块
{
  "chunk_strategy": "semantic",
  "chunk_size": 500,
  "chunk_overlap": 100
}

# 代码文档 - 使用递归分块
{
  "chunk_strategy": "recursive",
  "chunk_size": 800,
  "chunk_overlap": 150
}

# 长文章 - 使用段落分块
{
  "chunk_strategy": "paragraph",
  "chunk_size": 1000,
  "chunk_overlap": 0
}
```

### 2. 批量上传文档

```python
import requests

documents = [
    {"title": "文档1", "content": "..."},
    {"title": "文档2", "content": "..."},
    {"title": "文档3", "content": "..."},
]

for doc in documents:
    requests.post(
        "http://localhost:8000/api/v1/documents/",
        json={
            "knowledge_base_id": 1,
            **doc,
            "auto_process": True
        }
    )
```

### 3. 监控处理状态

```python
import time

doc_id = 1

while True:
    response = requests.get(f"http://localhost:8000/api/v1/documents/{doc_id}")
    status = response.json()["status"]
    
    if status == "completed":
        print("处理完成！")
        break
    elif status == "failed":
        print("处理失败！")
        break
    
    print(f"当前状态: {status}")
    time.sleep(1)
```

---

## 🐛 错误处理

### 常见错误码

- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误信息描述"
}
```

---

## 🔧 配置说明

### 环境变量

- `DATABASE_URL`: 数据库连接字符串（默认 SQLite）
- `OLLAMA_BASE_URL`: Ollama API 地址（默认 http://localhost:11434）

### 数据存储

- 数据库文件: `./data/rag_system.db`
- 向量索引: 内存中（可扩展到持久化）

---

## 📝 测试

运行测试脚本：

```bash
# 确保服务器正在运行
python main.py

# 在另一个终端运行测试
python test_api.py
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

