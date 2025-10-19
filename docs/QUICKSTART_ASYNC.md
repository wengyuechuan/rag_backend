# 快速开始：异步文档处理

## 1. 环境准备

### 必需服务
```bash
# 启动 Ollama（用于向量化）
ollama serve

# 下载嵌入模型
ollama pull nomic-embed-text
```

### 可选服务

**启用实体关系提取（NER）**
```bash
# 设置 OpenAI API Key
export OPENAI_API_KEY="your-api-key"
```

**启用知识图谱**
```bash
# 启动 Neo4j
# 使用 Docker:
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# 设置环境变量
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
```

## 2. 启动应用

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python main.py
```

服务器将在 `http://localhost:8000` 启动

## 3. 测试异步处理

```bash
# 运行测试脚本
python test_async_processing.py
```

## 4. 使用 API

### 创建知识库
```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试知识库",
    "enable_vector_store": true,
    "enable_ner": false,
    "enable_knowledge_graph": false
  }'
```

### 创建文档（异步处理）
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "title": "测试文档",
    "content": "这是一个测试文档的内容...",
    "auto_process": true
  }'

# 立即返回文档 ID
```

### 查询处理状态
```bash
curl "http://localhost:8000/api/v1/documents/1/status"
```

### 搜索文档
```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试",
    "knowledge_base_id": 1,
    "top_k": 5
  }'
```

## 5. 功能开关

在创建知识库时控制启用的功能：

| 参数 | 说明 | 依赖 |
|------|------|------|
| `enable_vector_store` | 向量检索 | Ollama |
| `enable_ner` | 实体关系提取 | OpenAI API |
| `enable_knowledge_graph` | 知识图谱 | Neo4j |

**建议配置：**
- **快速开始**：只启用 `enable_vector_store`
- **生产环境**：全部启用（性能最佳）

## 6. 查看文档

- API 文档：http://localhost:8000/docs
- ReDoc 文档：http://localhost:8000/redoc
- 详细说明：[ASYNC_PROCESSING.md](ASYNC_PROCESSING.md)

## 常见问题

**Q: 文档创建后多久能完成处理？**
- 只分块 + 向量化：2-10 秒
- 包含 NER：10-60 秒
- 全部功能：15-90 秒

**Q: 如何知道文档处理完成？**
- 轮询 `/api/v1/documents/{id}/status` 接口
- 检查 `db_status` 字段是否为 `completed`

**Q: 可以同时处理多少个文档？**
- 默认 4 个并发处理
- 更多文档会在队列中等待

**Q: 如果不需要 NER 和知识图谱怎么办？**
- 创建知识库时设置 `enable_ner: false` 和 `enable_knowledge_graph: false`
- 只进行分块和向量化，速度更快

