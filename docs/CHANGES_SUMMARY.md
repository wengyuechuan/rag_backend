# 异步文档处理功能 - 更新摘要

## 🎯 实现目标

✅ **非阻塞返回**：创建文档后立即返回文档 ID，不等待处理完成
✅ **后台异步处理**：使用线程池在后台执行分块、向量化、NER 等操作
✅ **实体关系抽取**：集成 LangGraph 和 OpenAI 进行实体识别和关系提取
✅ **知识图谱存储**：自动将提取的三元组存储到 Neo4j
✅ **状态监控**：提供 API 查询文档处理进度

## 📝 主要变更

### 1. 文档处理服务 (`api/services/document_service.py`)

**完全重写**，新增功能：

- **线程池管理**：使用 `ThreadPoolExecutor` 实现真正的异步处理
- **资源缓存**：缓存 `FaissVectorStore`、`EntityRelationExtractor`、`Neo4jKnowledgeGraph` 实例
- **四步处理流程**：
  1. 文档分块
  2. 向量化（可选）
  3. 实体关系提取（可选）
  4. 知识图谱存储（可选）

**新增方法**：
```python
process_document_async()        # 提交异步任务
get_processing_status()         # 查询处理状态
get_vector_store()             # 获取向量存储
get_ner_extractor()            # 获取 NER 提取器
get_neo4j_client()             # 获取 Neo4j 客户端
_process_document_worker()     # 后台工作线程
_chunk_document_step()         # 分块步骤
_vectorize_chunks_step()       # 向量化步骤
_extract_entities_relations_step()  # NER 步骤
_store_to_knowledge_graph_step()    # 知识图谱步骤
```

**关键特性**：
- 使用独立的数据库 session，避免跨线程问题
- 详细的日志输出，便于调试
- 优雅的错误处理，不会因单个步骤失败而中断
- 自动更新文档和知识库统计信息

### 2. 文档路由 (`api/routers/document.py`)

**修改**：

- 移除 `BackgroundTasks` 依赖（不再需要）
- 使用 `process_document_async()` 替代原来的同步处理
- **新增端点**：`GET /api/v1/documents/{doc_id}/status` - 查询处理状态

**路由变更**：
```python
# 创建文档 - 立即返回
POST /api/v1/documents
- 调用 process_document_async() 提交任务
- 立即返回文档 ID 和初始状态

# 手动触发处理
POST /api/v1/documents/{doc_id}/process
- 使用 process_document_async() 提交任务
- 立即返回，不等待完成

# 查询处理状态（新增）
GET /api/v1/documents/{doc_id}/status
- 返回数据库状态
- 返回队列状态（是否在处理中）
- 返回处理结果（分块数、向量化状态等）
```

### 3. 新增文件

#### `config.example.env`
环境变量配置示例：
- OpenAI API 配置（NER）
- Neo4j 配置（知识图谱）
- Ollama 配置（向量化）
- 处理线程数配置

#### `test_async_processing.py`
完整的异步处理测试脚本：
- 创建知识库
- 创建文档（立即返回）
- 监控处理进度
- 查看分块结果
- 执行搜索测试

#### `ASYNC_PROCESSING.md`
详细的功能文档：
- 功能概述和架构
- 配置说明
- API 使用示例
- Python 代码示例
- 性能说明
- 错误处理
- 监控和调试
- 最佳实践
- 故障排查

#### `QUICKSTART_ASYNC.md`
快速开始指南：
- 环境准备步骤
- 服务启动命令
- API 使用示例
- 功能开关说明
- 常见问题解答

#### `CHANGES_SUMMARY.md`（本文件）
更新摘要和技术说明

## 🔧 技术细节

### 异步处理架构

```
用户请求
   ↓
创建文档记录（status = PENDING）
   ↓
提交到线程池 ← 立即返回文档 ID
   ↓
后台工作线程启动
   ↓
创建新的 DB Session
   ↓
更新状态（status = PROCESSING）
   ↓
┌─────────────────────────────┐
│ 步骤1：文档分块             │
│ - 根据策略分块              │
│ - 创建 DocumentChunk 记录   │
└─────────────────────────────┘
   ↓
┌─────────────────────────────┐
│ 步骤2：向量化（可选）       │
│ - 调用 Ollama API          │
│ - 存储到 FAISS             │
│ - 更新 chunk.has_embedding │
└─────────────────────────────┘
   ↓
┌─────────────────────────────┐
│ 步骤3：NER（可选）          │
│ - 调用 OpenAI API          │
│ - 提取实体和关系           │
│ - 更新 chunk.entities      │
└─────────────────────────────┘
   ↓
┌─────────────────────────────┐
│ 步骤4：知识图谱（可选）     │
│ - 收集三元组               │
│ - 批量插入 Neo4j           │
│ - 更新 graph_stored        │
└─────────────────────────────┘
   ↓
更新统计信息
   ↓
更新状态（status = COMPLETED）
   ↓
关闭 DB Session
```

### 线程安全

- ✅ 每个工作线程使用独立的数据库 session
- ✅ 使用 `threading.Lock` 保护共享状态（任务队列）
- ✅ 任务完成后自动清理

### 错误处理

```python
try:
    # 处理步骤
except Exception as e:
    # 1. 记录错误日志
    # 2. 更新文档状态为 FAILED
    # 3. 保存错误信息到 error_message
    # 4. 不影响其他文档的处理
finally:
    # 关闭 DB session
    # 清理任务记录
```

### 资源管理

**缓存策略**：
- 每个知识库一个 `FaissVectorStore` 实例
- 每个知识库一个 `EntityRelationExtractor` 实例
- 每个知识库一个 `Neo4jKnowledgeGraph` 实例

**优点**：
- 避免重复创建连接
- 提高处理效率
- 减少资源消耗

## 📊 性能对比

### 之前（同步处理）
```
请求 → 处理（阻塞 30-60秒）→ 返回结果
```
- 用户需要等待处理完成
- 长时间请求可能超时
- 无法处理并发请求

### 现在（异步处理）
```
请求 → 立即返回（< 100ms）
        ↓
      后台处理（30-60秒）
        ↓
      查询状态（随时）
```
- 用户立即得到响应
- 不会超时
- 支持多文档并发处理（线程池）

## 🎨 使用示例

### 基础用法（仅向量化）

```python
# 1. 创建知识库
kb = requests.post(f"{BASE_URL}/api/v1/knowledge-bases", json={
    "name": "基础知识库",
    "enable_vector_store": True,
    "enable_ner": False,
    "enable_knowledge_graph": False
}).json()

# 2. 创建文档（立即返回）
doc = requests.post(f"{BASE_URL}/api/v1/documents", json={
    "knowledge_base_id": kb["id"],
    "title": "测试文档",
    "content": "文档内容...",
    "auto_process": True
}).json()

print(f"文档 ID: {doc['id']}")  # 立即获得 ID

# 3. 等待处理完成
while True:
    status = requests.get(
        f"{BASE_URL}/api/v1/documents/{doc['id']}/status"
    ).json()["data"]
    
    if status["db_status"] == "completed":
        break
    time.sleep(2)

# 4. 搜索
results = requests.post(f"{BASE_URL}/api/v1/search", json={
    "query": "关键词",
    "knowledge_base_id": kb["id"]
}).json()
```

### 高级用法（全功能）

```python
# 创建完整功能的知识库
kb = requests.post(f"{BASE_URL}/api/v1/knowledge-bases", json={
    "name": "高级知识库",
    "enable_vector_store": True,      # ✅ 向量检索
    "enable_ner": True,                # ✅ 实体关系提取
    "enable_knowledge_graph": True,    # ✅ 知识图谱
    "embedding_model": "nomic-embed-text"
}).json()

# 批量创建多个文档（并发处理）
doc_ids = []
for i in range(10):
    doc = requests.post(f"{BASE_URL}/api/v1/documents", json={
        "knowledge_base_id": kb["id"],
        "title": f"文档 {i}",
        "content": f"内容 {i}...",
        "auto_process": True
    }).json()
    doc_ids.append(doc["id"])
    print(f"提交文档 {i}")

print(f"所有文档已提交，系统正在后台处理...")

# 等待所有文档完成
# （线程池会自动管理并发）
```

## 🔍 调试和监控

### 服务器日志示例

```
✅ 文档处理服务已初始化 (最大工作线程: 4)
📋 文档 1 已提交到处理队列

============================================================
🚀 开始处理文档 1
============================================================

[步骤 1/4] 文档分块...
✅ 生成 8 个分块

[步骤 2/4] 向量化...
✅ 向量化完成

[步骤 3/4] 实体关系提取...
🔍 [步骤1] 实体提取...
  ✅ 提取到 12 个实体
🔗 [步骤2] 关系提取...
  ✅ 提取到 6 个关系
✅ 提取了 12 个实体，6 个关系

[步骤 4/4] 知识图谱存储...
   插入三元组: 成功 6, 失败 0
✅ 知识图谱存储完成

============================================================
✅ 文档 1 处理完成
   耗时: 25.3秒
   分块数: 8
   向量化: 是
   知识图谱: 是
============================================================
```

### 状态 API 响应示例

```json
{
  "message": "文档状态查询成功",
  "data": {
    "document_id": 1,
    "db_status": "completed",
    "in_processing_queue": false,
    "is_running": false,
    "chunk_count": 8,
    "vector_stored": true,
    "graph_stored": true,
    "error_message": null,
    "processing_time": 25.3,
    "processed_at": "2024-01-15T10:30:45.123456"
  }
}
```

## ⚙️ 配置建议

### 开发环境
```python
# 快速测试，最小配置
enable_vector_store = True       # ✅
enable_ner = False               # ❌
enable_knowledge_graph = False   # ❌
MAX_PROCESSING_WORKERS = 2
```

### 生产环境（小规模）
```python
# 平衡性能和功能
enable_vector_store = True       # ✅
enable_ner = True                # ✅
enable_knowledge_graph = False   # ❌
MAX_PROCESSING_WORKERS = 4
```

### 生产环境（大规模）
```python
# 完整功能
enable_vector_store = True       # ✅
enable_ner = True                # ✅
enable_knowledge_graph = True    # ✅
MAX_PROCESSING_WORKERS = 8
```

## 📚 相关文档

1. **[ASYNC_PROCESSING.md](ASYNC_PROCESSING.md)** - 完整的功能文档
2. **[QUICKSTART_ASYNC.md](QUICKSTART_ASYNC.md)** - 快速开始指南
3. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API 参考文档
4. **[config.example.env](config.example.env)** - 环境变量配置

## 🧪 测试

运行完整测试：
```bash
# 启动服务器
python main.py

# 运行异步处理测试
python test_async_processing.py

# 运行原有的 API 测试
python test_api.py
```

## ✨ 核心优势

1. **用户体验**：立即响应，不用等待
2. **系统稳定**：不会因长时间处理导致超时
3. **并发处理**：支持多文档同时处理
4. **灵活配置**：可选择启用的功能
5. **错误隔离**：单个文档失败不影响其他
6. **实时监控**：随时查询处理进度
7. **资源高效**：复用连接，减少开销
8. **扩展性好**：易于添加新的处理步骤

## 🎯 下一步建议

1. **性能优化**：
   - 考虑使用 Celery 替代线程池（更强大的任务队列）
   - 添加 Redis 缓存查询结果
   - 实现分布式处理

2. **功能增强**：
   - 添加批量上传 API
   - 支持文件上传（PDF、Word 等）
   - 实现处理优先级
   - 添加进度百分比显示

3. **监控和告警**：
   - 集成 Prometheus 指标
   - 添加处理失败告警
   - 实现队列深度监控

4. **安全性**：
   - 添加用户认证
   - 实现权限控制
   - API 限流

---

**完成日期**：2024
**版本**：1.0.0
**作者**：AI Assistant

