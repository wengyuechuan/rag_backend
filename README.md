# RAG Backend - 智能知识库问答系统

基于 **FastAPI + FAISS + Ollama + Neo4j + OpenAI** 的完整 RAG（检索增强生成）后端系统。

## ✨ 核心功能

### 🎯 智能对话问答 ⭐ NEW
- **会话管理**：多会话支持，自动维护上下文
- **RAG 检索**：向量搜索 + 知识图谱混合检索
- **滑动窗口**：自动召回前5条历史消息
- **SSE 流式响应**：实时生成，提升用户体验
- **OpenAI 集成**：GPT-4/3.5 智能问答

### 📚 知识库管理
- **多知识库**：支持创建和管理多个独立知识库
- **文档管理**：批量上传、自动处理、状态跟踪
- **智能分块**：语义分块、固定分块、递归分块、段落分块
- **元数据管理**：标签、分类、自定义属性

### 🔍 智能检索
- **向量搜索**：基于语义相似度的文档检索
- **图谱搜索**：基于实体关系的知识推理
- **混合搜索**：结合向量和图谱的优势
- **高性能**：FAISS 加速，支持大规模数据
- **自动持久化**：FAISS 索引自动保存，重启不丢失 ⭐ NEW

### 🧠 知识图谱
- **实体识别**：自动提取人物、组织、地点等实体
- **关系抽取**：识别实体间的语义关系
- **图谱存储**：Neo4j 图数据库
- **图谱推理**：路径查找、邻居发现、子图提取

### 🤖 AI 工作流集成 ⭐ NEW
- **Coze 集成**：调用 Coze AI 工作流
- **流式输出**：实时返回处理结果
- **灵活配置**：支持自定义参数和工作流
- **无缝集成**：与 RAG 系统完美结合

### 🔄 异步处理
- **后台任务**：文档处理不阻塞 API 响应
- **状态跟踪**：实时查询处理进度
- **线程池**：高效并发处理

## 🚀 快速开始

### 1. 安装依赖

#### 🚀 方式 1：使用 uv（推荐，极速安装）⭐ NEW

```bash
# 克隆项目
git clone https://github.com/your-repo/RAG_backend.git
cd RAG_backend

# 安装 uv（如果尚未安装）
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 快速设置（自动创建虚拟环境并安装依赖）
# Linux / macOS
chmod +x setup_uv.sh
./setup_uv.sh

# Windows (PowerShell)
.\setup_uv.ps1

# 或手动设置
uv venv --python 3.10          # 创建虚拟环境
source .venv/bin/activate      # 激活（Linux/macOS）
.venv\Scripts\activate         # 激活（Windows）
uv pip install -e .            # 安装依赖
```

#### 📦 方式 2：使用 pip（传统方式）

```bash
# 克隆项目
git clone https://github.com/your-repo/RAG_backend.git
cd RAG_backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows

# 安装依赖
pip install -r requirements.txt
```

**为什么推荐 uv？**
- ⚡ 比 pip 快 10-100 倍
- 🔒 更好的依赖解析
- 📦 统一管理虚拟环境和包
- 详见 [UV_GUIDE.md](UV_GUIDE.md)

### 2. 配置环境

创建 `.env` 文件：

```env
# OpenAI 配置（必需）
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Ollama 配置（向量搜索）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Neo4j 配置（图谱搜索，可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Coze 配置（AI 工作流，可选）⭐ NEW
COZE_API_KEY=pat_xxxxxxxxxxxxx
COZE_WORKFLOW_ID=7562785533798547507
```

### 3. 启动服务

#### 启动 Ollama（向量搜索）
```bash
# 安装 Ollama: https://ollama.ai
ollama serve

# 拉取嵌入模型
ollama pull nomic-embed-text
```

#### 启动 Neo4j（可选，图谱搜索）
```bash
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest
```

#### 启动 API 服务器
```bash
python main.py
```

访问 **API 文档**: http://localhost:8000/docs

### 4. 快速测试

#### 方式 1：使用命令行客户端（推荐）

```bash
# 交互式对话
python chat_client.py
```

#### 方式 2：使用测试脚本

```bash
# 自动化测试
python test_chat.py
```

#### 方式 3：使用 API

```bash
# 1. 创建知识库
curl -X POST "http://localhost:8000/api/v1/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI知识库",
    "description": "人工智能相关文档",
    "enable_vector_store": true,
    "enable_ner": true,
    "enable_knowledge_graph": true
  }'

# 2. 上传文档
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "title": "AI简介",
    "content": "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统...",
    "auto_process": true
  }'

# 3. 创建对话会话
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "title": "AI学习对话",
    "use_vector_search": true,
    "use_graph_search": true
  }'

# 4. 开始对话（流式）
curl -N -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "message": "什么是人工智能？",
    "stream": true
  }'
```

## 📖 完整功能演示

### 1. 知识库管理

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 创建知识库
kb_response = requests.post(
    f"{BASE_URL}/knowledge-bases",
    json={
        "name": "技术文档库",
        "description": "软件开发相关文档",
        "enable_vector_store": True,
        "enable_ner": True,
        "enable_knowledge_graph": True
    }
)
kb = kb_response.json()
print(f"知识库 ID: {kb['id']}")
```

### 2. 文档上传和处理

```python
# 上传文档
doc_response = requests.post(
    f"{BASE_URL}/documents",
    json={
        "knowledge_base_id": kb['id'],
        "title": "Python 教程",
        "content": "Python 是一种高级编程语言...",
        "auto_process": True  # 自动处理：分块 + 向量化 + NER
    }
)
doc = doc_response.json()

# 查询处理状态
status = requests.get(f"{BASE_URL}/documents/{doc['id']}/status")
print(status.json())
```

### 3. Coze 工作流调用 ⭐ NEW

```python
# 调用 Coze 工作流
response = requests.post(
    f"{BASE_URL}/coze/workflow/run",
    json={
        "workflow_id": "7562785533798547507",
        "input_text": "北京今天应该穿什么衣服"
    }
)
result = response.json()
print(f"输出: {result['output']}")
print(f"Token: {result['total_tokens']}")

# 或使用简化接口（使用默认工作流）
response = requests.post(
    f"{BASE_URL}/coze/simple",
    json={"input_text": "上海今天天气怎么样"}
)
print(response.json()['output'])
```

### 4. 智能对话

```python
# 创建会话
session = requests.post(
    f"{BASE_URL}/chat/sessions",
    json={
        "knowledge_base_id": kb['id'],
        "use_vector_search": True,
        "use_graph_search": True
    }
).json()

# 流式对话
import json

response = requests.post(
    f"{BASE_URL}/chat/completions",
    json={
        "session_id": session['id'],
        "message": "Python 有哪些特点？",
        "stream": True
    },
    stream=True
)

print("AI: ", end='', flush=True)
for line in response.iter_lines():
    if line and line.startswith(b'data: '):
        data = json.loads(line[6:])
        if data['type'] == 'chunk':
            print(data['data'], end='', flush=True)
print()
```

### 5. 混合搜索

```python
# 向量搜索 + 图谱搜索
search_response = requests.post(
    f"{BASE_URL}/search",
    json={
        "query": "Python 的创始人是谁",
        "knowledge_base_id": kb['id'],
        "top_k": 5,
        "use_vector": True,
        "use_graph": True
    }
)

result = search_response.json()

# 查看文本块结果
for r in result['results']:
    print(f"文档: {r['document_title']}")
    print(f"内容: {r['content'][:100]}...")
    print(f"评分: {r['score']:.3f}")
    if r['entities']:
        print(f"实体: {', '.join(r['entities'])}")
    print()

# 查看图谱结果
if result['graph_results']:
    for gr in result['graph_results']:
        print(f"实体: {gr['entity_name']} ({gr['entity_type']})")
        print(f"相关实体:")
        for rel in gr['related_entities']:
            print(f"  - {rel['name']} ({rel['relation']})")
```

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户/客户端                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI REST API                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ⭐NEW│
│  │知识库管理│ │ 文档管理 │ │  搜索  │ │  对话  │ │Coze│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────┘│
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    SQLite    │ │  文档处理服务  │ │  对话服务    │
│   数据库     │ │ (异步后台)    │ │ (SSE流式)   │
└──────────────┘ └───────┬──────┘ └──────┬───────┘
                         │                │
         ┌───────────────┼────────────────┘
         │               │
         ▼               ▼
┌─────────────────────────────────────────┐
│          文档分块 (TextChunker)          │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │ 语义 │ │ 固定 │ │ 递归 │ │ 段落 │  │
│  └──────┘ └──────┘ └──────┘ └──────┘  │
└────────────┬───────────────────────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
┌──────────┐   ┌──────────────┐
│  向量化   │   │  实体关系提取 │
│ Ollama   │   │  OpenAI GPT  │
└────┬─────┘   └──────┬───────┘
     │                │
     ▼                ▼
┌──────────┐   ┌──────────────┐
│  FAISS   │   │    Neo4j     │
│ 向量存储  │   │  知识图谱    │
└────┬─────┘   └──────┬───────┘
     │                │
     └────────┬───────┘
              │
              ▼
     ┌────────────────┐
     │   RAG 检索     │
     │ 向量 + 图谱    │
     └────────┬───────┘
              │
              ▼
     ┌────────────────┐
     │ OpenAI GPT-4   │
     │  智能回答      │
     └────────────────┘
```

## 🎯 核心组件

### 1. 文档分块 (`utils/chunk.py`)

支持多种分块策略：

```python
from utils.chunk import TextChunker

chunker = TextChunker(chunk_size=500, chunk_overlap=100)

# 语义分块（推荐）
chunks = chunker.semantic_chunking(text, language='zh')

# 固定大小分块
chunks = chunker.fixed_size_chunking(text)

# 递归分块
chunks = chunker.recursive_chunking(text)

# 段落分块
chunks = chunker.paragraph_chunking(text)
```

### 2. 向量存储 (`utils/faiss.py`)

基于 FAISS 的高性能向量检索：

```python
from utils.faiss import FaissVectorStore

# 初始化
store = FaissVectorStore(
    embedding_model="nomic-embed-text",
    index_type="Flat",  # Flat/IVF/HNSW
    metric="Cosine"     # L2/IP/Cosine
)

# 添加文档
store.add_texts(texts, metadatas)

# 搜索
results = store.search("查询", top_k=5)

# 保存/加载
store.save("./index")
loaded = FaissVectorStore.load("./index")
```

### 3. 知识图谱 (`utils/neo4j.py`)

基于 Neo4j 的图谱存储和查询：

```python
from utils.neo4j import Neo4jKnowledgeGraph

kg = Neo4jKnowledgeGraph(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# 插入三元组
kg.insert_triple("张三", "Person", "WORKS_AT", "公司A", "Company")

# 查询关系
relations = kg.find_relations(subject="张三")

# 查找邻居
neighbors = kg.get_neighbors("张三", direction="out")

# 查找路径
paths = kg.get_path("张三", "Python", max_depth=3)
```

### 4. 实体关系提取 (`utils/chunk_to_ner.py`)

基于 OpenAI 的智能 NER：

```python
from utils.chunk_to_ner import EntityRelationExtractor

extractor = EntityRelationExtractor(
    model="gpt-4",
    temperature=0.3
)

# 提取实体和关系
result = extractor.process_text(text, use_workflow=True)

# 实体
for entity in result['entities']:
    print(f"{entity.name} ({entity.entity_type})")

# 关系
for relation in result['relations']:
    print(f"{relation.subject} --[{relation.predicate}]--> {relation.object}")
```

### 5. 文档处理服务 (`api/services/document_service.py`)

异步文档处理：

```python
from api.services.document_service import document_service

# 异步处理文档
document_service.process_document_async(document_id, kb_id)

# 查询处理状态
status = document_service.get_processing_status(document_id)
```

## 📚 API 端点总览

### 知识库管理
- `POST /api/v1/knowledge-bases` - 创建知识库
- `GET /api/v1/knowledge-bases` - 获取知识库列表
- `GET /api/v1/knowledge-bases/{id}` - 获取知识库详情
- `PATCH /api/v1/knowledge-bases/{id}` - 更新知识库
- `DELETE /api/v1/knowledge-bases/{id}` - 删除知识库

### 文档管理
- `POST /api/v1/documents` - 创建文档
- `POST /api/v1/documents/upload` - 上传文件
- `GET /api/v1/documents` - 获取文档列表
- `GET /api/v1/documents/{id}` - 获取文档详情
- `PATCH /api/v1/documents/{id}` - 更新文档
- `DELETE /api/v1/documents/{id}` - 删除文档
- `POST /api/v1/documents/{id}/process` - 手动处理文档
- `GET /api/v1/documents/{id}/status` - 查询处理状态
- `GET /api/v1/documents/{id}/chunks` - 获取文档分块

### 搜索
- `POST /api/v1/search` - 混合搜索（向量 + 图谱）

### 对话管理 ⭐ NEW
- `POST /api/v1/chat/sessions` - 创建会话
- `GET /api/v1/chat/sessions` - 获取会话列表
- `GET /api/v1/chat/sessions/{id}` - 获取会话详情
- `PATCH /api/v1/chat/sessions/{id}` - 更新会话
- `DELETE /api/v1/chat/sessions/{id}` - 删除会话
- `GET /api/v1/chat/sessions/{id}/history` - 获取会话历史
- `POST /api/v1/chat/completions` - 发送消息（支持 SSE 流式）

完整 API 文档：http://localhost:8000/docs

## 🔧 配置说明

### 知识库配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `enable_vector_store` | 是否启用向量搜索 | true |
| `enable_ner` | 是否启用实体识别 | false |
| `enable_knowledge_graph` | 是否启用知识图谱 | false |
| `default_chunk_strategy` | 默认分块策略 | semantic |
| `default_chunk_size` | 默认分块大小 | 500 |
| `default_chunk_overlap` | 默认重叠大小 | 100 |

### 对话配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `use_vector_search` | 是否使用向量搜索 | true |
| `use_graph_search` | 是否使用图谱搜索 | false |
| `search_top_k` | 检索文档数量 | 5 |
| `temperature` | 生成温度 | 0.7 |
| `max_tokens` | 最大生成长度 | 2000 |

## 📁 项目结构

```
RAG_backend/
├── api/                         # FastAPI 应用
│   ├── routers/                # 路由模块
│   │   ├── knowledge_base.py  # 知识库路由
│   │   ├── document.py         # 文档路由
│   │   ├── search.py           # 搜索路由
│   │   └── chat.py             # 对话路由 ⭐ NEW
│   ├── services/               # 业务服务
│   │   └── document_service.py # 文档处理服务
│   └── schemas.py              # Pydantic 数据模型
├── database/                    # 数据库模块
│   ├── models.py               # SQLAlchemy 模型
│   ├── database.py             # 数据库连接
│   └── __init__.py
├── utils/                       # 工具模块
│   ├── chunk.py                # 文档分块
│   ├── faiss.py                # 向量存储
│   ├── neo4j.py                # 知识图谱
│   ├── chunk_to_ner.py         # 实体关系提取
│   └── file_parser.py          # 文件解析
├── docs/                        # 文档
│   ├── CHAT_API_GUIDE.md       # 对话 API 指南 ⭐ NEW
│   ├── CHAT_QUICKSTART.md      # 对话快速开始 ⭐ NEW
│   ├── GRAPH_SEARCH_GUIDE.md   # 图谱搜索指南
│   ├── API_DOCUMENTATION.md    # API 文档
│   └── ...
├── main.py                      # FastAPI 主应用
├── test_chat.py                 # 对话测试脚本 ⭐ NEW
├── chat_client.py               # 命令行客户端 ⭐ NEW
├── pyproject.toml               # 项目配置（uv/pip）⭐ NEW
├── requirements.txt             # 依赖列表（备用）
├── setup_uv.sh                  # uv 快速设置脚本（Linux/macOS）⭐ NEW
├── setup_uv.ps1                 # uv 快速设置脚本（Windows）⭐ NEW
├── UV_GUIDE.md                  # uv 使用指南 ⭐ NEW
├── .env                         # 环境变量
├── .gitignore                   # Git 忽略文件
└── README.md                    # 项目说明
```

## 🛠️ 技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| **uv** | 包管理器 | latest ⭐ NEW |
| **FastAPI** | Web 框架 | >=0.104.0 |
| **SQLAlchemy** | ORM | >=2.0.0 |
| **SQLite** | 数据库 | - |
| **Pydantic** | 数据验证 | >=2.0.0 |
| **FAISS** | 向量搜索 | >=1.7.4 |
| **Ollama** | 本地嵌入 | - |
| **OpenAI** | LLM 服务 | >=1.10.0 |
| **Neo4j** | 图数据库 | >=5.0 |
| **LangGraph** | 工作流 | >=0.0.30 |

## 📖 详细文档

- **环境配置**
  - [uv 使用指南](UV_GUIDE.md) ⭐ NEW
- **API 文档**
  - [完整 API 文档](docs/API_DOCUMENTATION.md)
  - [对话 API 指南](docs/CHAT_API_GUIDE.md) ⭐ NEW
  - [对话快速开始](docs/CHAT_QUICKSTART.md) ⭐ NEW
- **功能指南**
  - [Coze 工作流集成](docs/COZE_GUIDE.md) ⭐ NEW
  - [Coze API 接口文档](docs/COZE_API_GUIDE.md) ⭐ NEW
  - [FAISS 持久化说明](docs/FAISS_PERSISTENCE.md) ⭐ NEW
  - [图谱搜索指南](docs/GRAPH_SEARCH_GUIDE.md)
  - [实体关系模型](docs/ENTITY_RELATION_MODEL.md)
  - [异步处理说明](docs/ASYNC_PROCESSING.md)

## 🎯 使用场景

### 1. 智能文档问答
```
用户：Python 有哪些特点？
系统：[检索相关文档] → [生成答案]
```

### 2. 知识图谱查询
```
用户：小明的父亲是谁？
系统：[图谱查询] → 找到关系 → 张三
```

### 3. 混合检索
```
用户：深度学习的应用领域
系统：[向量搜索] + [图谱推理] → 综合答案
```

### 4. 企业知识库
- 技术文档库
- 产品手册库
- 客服知识库
- 法律法规库

### 5. AI 工作流增强 ⭐ NEW
```python
from utils.coze import run_coze_workflow

# 调用 Coze 工作流
result = run_coze_workflow(
    workflow_id="7562785533798547507",
    input_text="北京今天应该穿什么衣服"
)
print(result)
# 输出: 今天北京天气晴朗，但气温较低且有风，
#       建议穿着厚外套、毛衣、保暖裤...
```

## ⚡ 性能优化

### 索引选择
- **小数据集 (<10K)**: 使用 `Flat` 索引
- **中等数据集 (10K-1M)**: 使用 `HNSW` 索引
- **大数据集 (>1M)**: 使用 `IVF` 索引

### 分块策略
- **RAG 问答**: 语义分块 (200-500 字符)
- **长文档检索**: 递归分块 (500-1000 字符)
- **结构化文档**: 段落分块

### GPU 加速
```bash
# 使用 GPU 版本的 FAISS
pip install faiss-gpu
```

## 🐛 常见问题

### Q: Ollama 连接失败？
```bash
# 检查 Ollama 服务
curl http://localhost:11434/api/tags

# 重启 Ollama
ollama serve
```

### Q: OpenAI API 调用失败？
```bash
# 检查环境变量
curl http://localhost:8000/config

# 确认 API Key 是否正确
echo $OPENAI_API_KEY
```

### Q: Neo4j 连接失败？
```bash
# 检查 Neo4j 容器
docker ps | grep neo4j

# 查看日志
docker logs neo4j

# 测试连接
curl http://localhost:7474
```

### Q: 文档处理失败？
1. 检查知识库配置是否正确
2. 确认必要的服务已启动（Ollama/Neo4j）
3. 查看文档处理状态：`GET /api/v1/documents/{id}/status`

## 🚀 部署建议

### 开发环境
```bash
python main.py
```

### 生产环境
```bash
# 使用 Gunicorn + Uvicorn
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker 部署
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📈 路线图

- [x] 文档分块和向量存储
- [x] FAISS 向量检索
- [x] Neo4j 知识图谱
- [x] 实体关系提取
- [x] REST API
- [x] 异步文档处理
- [x] 智能对话问答
- [x] SSE 流式响应
- [ ] 用户认证和权限管理
- [ ] 多模态支持（图片、音频）
- [ ] 分布式部署
- [ ] 性能监控和日志

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

## 📮 联系方式

- 项目地址：[GitHub](https://github.com/your-repo/RAG_backend)
- 问题反馈：[Issues](https://github.com/your-repo/RAG_backend/issues)

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Ollama](https://ollama.ai/)
- [Neo4j](https://neo4j.com/)
- [OpenAI](https://openai.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)

---

**⭐ 如果这个项目对您有帮助，请给一个 Star！**
