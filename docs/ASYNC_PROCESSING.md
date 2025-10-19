# 异步文档处理说明

## 概述

RAG 后端系统现在支持完全异步的文档处理，包括：
- ✅ **非阻塞返回**：创建文档后立即返回文档 ID
- ✅ **后台处理**：文档分块、向量化、实体关系提取在后台线程中执行
- ✅ **状态监控**：可以随时查询文档处理进度
- ✅ **多任务并发**：使用线程池支持多个文档同时处理

## 处理流程

```
创建文档 → 立即返回 → 后台处理（分块 → 向量化 → NER → 知识图谱）
   ↓
 返回文档ID
   ↓
轮询状态（可选）
```

## 核心特性

### 1. 自动分块
根据知识库配置或用户指定的策略进行文档分块：
- **语义分块**（semantic）：按句子边界智能分块
- **固定大小分块**（fixed）：固定字符数分块
- **递归分块**（recursive）：递归按段落、句子分块
- **段落分块**（paragraph）：按段落分块

### 2. 向量化存储
- 使用 FAISS 进行高效向量检索
- 集成 Ollama 本地模型生成嵌入向量
- 支持多种索引类型和距离度量

### 3. 实体关系提取（可选）
- 使用 LangGraph 工作流
- 通过 OpenAI API 提取实体和关系
- 自动识别人物、地点、组织、事件等实体类型

### 4. 知识图谱存储（可选）
- 自动将提取的三元组存储到 Neo4j
- 支持图谱查询和子图提取
- 与向量检索互补，提供结构化知识

## 配置要求

### 必需配置
```bash
# Ollama 服务（用于向量化）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 可选配置（启用 NER）
```bash
# OpenAI API
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

### 可选配置（启用知识图谱）
```bash
# Neo4j 数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## API 使用示例

### 1. 创建知识库
```bash
POST /api/v1/knowledge-bases
{
  "name": "我的知识库",
  "description": "测试知识库",
  "enable_vector_store": true,    # 启用向量存储
  "enable_ner": true,              # 启用实体关系提取
  "enable_knowledge_graph": true,  # 启用知识图谱
  "default_chunk_strategy": "semantic",
  "embedding_model": "nomic-embed-text"
}
```

### 2. 创建文档（异步处理）
```bash
POST /api/v1/documents
{
  "knowledge_base_id": 1,
  "title": "文档标题",
  "content": "文档内容...",
  "auto_process": true  # 自动异步处理
}

# 响应（立即返回）
{
  "id": 123,
  "title": "文档标题",
  "status": "pending",  # 状态：pending（待处理）
  "chunk_count": 0,
  ...
}
```

### 3. 查询处理状态
```bash
GET /api/v1/documents/123/status

# 响应
{
  "message": "文档状态查询成功",
  "data": {
    "document_id": 123,
    "db_status": "processing",      # pending/processing/completed/failed
    "in_processing_queue": true,    # 是否在处理队列中
    "is_running": true,             # 是否正在运行
    "chunk_count": 5,               # 已生成的分块数
    "vector_stored": false,         # 是否已向量化
    "graph_stored": false,          # 是否已存储到图谱
    "processing_time": 12.5,        # 处理耗时（秒）
    "error_message": null           # 错误信息
  }
}
```

### 4. 获取文档分块
```bash
GET /api/v1/documents/123/chunks

# 响应
[
  {
    "id": 1,
    "content": "分块内容...",
    "chunk_index": 0,
    "has_embedding": true,
    "entities": ["实体1", "实体2"],
    "keywords": ["关键词1", "关键词2"]
  },
  ...
]
```

### 5. 搜索文档
```bash
POST /api/v1/search
{
  "query": "搜索关键词",
  "knowledge_base_id": 1,
  "top_k": 5,
  "use_vector": true,
  "use_graph": false
}

# 响应
{
  "query": "搜索关键词",
  "results": [
    {
      "chunk_id": 1,
      "document_id": 123,
      "document_title": "文档标题",
      "content": "相关内容...",
      "score": 0.85,
      "chunk_index": 0
    },
    ...
  ],
  "total": 5,
  "processing_time": 0.123
}
```

## Python 示例代码

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. 创建知识库
kb_response = requests.post(
    f"{BASE_URL}/api/v1/knowledge-bases",
    json={
        "name": "测试知识库",
        "enable_vector_store": True,
        "enable_ner": True
    }
)
kb_id = kb_response.json()["id"]

# 2. 创建文档（立即返回）
doc_response = requests.post(
    f"{BASE_URL}/api/v1/documents",
    json={
        "knowledge_base_id": kb_id,
        "title": "测试文档",
        "content": "这是一个测试文档...",
        "auto_process": True
    }
)
doc_id = doc_response.json()["id"]
print(f"文档已创建: {doc_id}")

# 3. 轮询状态直到完成
while True:
    status_response = requests.get(
        f"{BASE_URL}/api/v1/documents/{doc_id}/status"
    )
    status = status_response.json()["data"]["db_status"]
    
    print(f"当前状态: {status}")
    
    if status in ["completed", "failed"]:
        break
    
    time.sleep(2)

# 4. 搜索文档
search_response = requests.post(
    f"{BASE_URL}/api/v1/search",
    json={
        "query": "测试",
        "knowledge_base_id": kb_id,
        "top_k": 5
    }
)
results = search_response.json()["results"]
print(f"找到 {len(results)} 个结果")
```

## 测试脚本

运行完整的异步处理测试：

```bash
# 启动服务器
python main.py

# 在另一个终端运行测试
python test_async_processing.py
```

测试脚本会：
1. 创建知识库
2. 创建文档（立即返回）
3. 监控处理进度
4. 查看分块结果
5. 执行搜索测试

## 性能说明

### 非阻塞响应时间
- **创建文档请求**：< 100ms（立即返回）
- **状态查询请求**：< 50ms

### 后台处理时间（取决于文档大小和配置）
- **仅分块**：0.5 - 2秒
- **分块 + 向量化**：2 - 10秒
- **分块 + 向量化 + NER**：10 - 60秒（取决于 API 响应时间）
- **完整流程**（含知识图谱）：15 - 90秒

### 并发能力
- 默认线程池大小：4 个工作线程
- 可同时处理 4 个文档
- 更多文档会在队列中等待

## 错误处理

系统会自动处理各种错误情况：
- ✅ 分块失败 → 标记为 FAILED 状态
- ✅ 向量化失败 → 记录警告，继续其他步骤
- ✅ NER 失败 → 记录警告，继续其他步骤
- ✅ 知识图谱失败 → 记录警告，完成其他步骤

所有错误信息都会记录在文档的 `error_message` 字段中。

## 监控和调试

### 查看处理日志
服务器日志会实时显示处理进度：
```
🚀 开始处理文档 123
[步骤 1/4] 文档分块...
✅ 生成 5 个分块
[步骤 2/4] 向量化...
✅ 向量化完成
[步骤 3/4] 实体关系提取...
✅ 提取了 15 个实体，8 个关系
[步骤 4/4] 知识图谱存储...
✅ 知识图谱存储完成
✅ 文档 123 处理完成（耗时: 25.3秒）
```

### 队列状态
使用状态 API 查询文档是否在处理队列中：
- `in_processing_queue: true` - 在队列中
- `is_running: true` - 正在处理
- `is_running: false` - 队列中等待

## 最佳实践

1. **启用合适的功能**
   - 小规模应用：只启用向量存储
   - 中等规模：向量存储 + NER
   - 大规模/复杂查询：全部启用

2. **调整线程池大小**
   - 根据服务器性能调整 `MAX_PROCESSING_WORKERS`
   - CPU 密集型：workers = CPU 核心数
   - IO 密集型：workers = CPU 核心数 * 2-4

3. **监控处理进度**
   - 定期轮询状态 API
   - 设置合理的超时时间
   - 处理失败情况

4. **批量操作**
   - 一次创建多个文档
   - 让系统自动排队处理
   - 减少等待时间

## 故障排查

### 文档一直处于 PROCESSING 状态
- 检查后台线程是否崩溃
- 查看服务器日志
- 重启服务器

### 向量化失败
- 确保 Ollama 服务正在运行
- 检查 `OLLAMA_BASE_URL` 配置
- 验证模型是否已下载

### NER 失败
- 检查 `OPENAI_API_KEY` 是否设置
- 验证 API 配额是否充足
- 检查网络连接

### 知识图谱失败
- 确保 Neo4j 正在运行
- 检查连接配置
- 验证数据库权限

## 相关文档

- [API 完整文档](API_DOCUMENTATION.md)
- [项目 README](README.md)
- [环境变量配置](config.example.env)

