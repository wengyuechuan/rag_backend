# 使用指南 - 基于 LangGraph 的实体关系提取

## 🎯 概述

本系统实现了基于 LangGraph 工作流的实体关系提取，可以从文本中自动提取知识图谱三元组。

## 📋 工作流程

```
文档块输入
    ↓
┌─────────────────────────────┐
│    LLM 处理（实体提取）      │
│    使用 OpenAI GPT-4         │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│    实体存储                  │
│    存储到图谱                │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│    关系提取                  │
│    识别实体间关系            │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│    知识图谱                  │
│    构建三元组                │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│    图谱查询                  │
│    支持多种查询方式          │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│    增强检索                  │
│    混合检索（向量+图谱）     │
└─────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install langgraph langchain-core openai

# 设置 OpenAI API Key
export OPENAI_API_KEY='your-api-key-here'

# 可选：使用自定义端点（如 Azure OpenAI）
export OPENAI_BASE_URL='https://your-endpoint.com/v1'
```

### 2. 基础使用

```python
from utils.chunk_to_ner import EntityRelationExtractor

# 初始化提取器
extractor = EntityRelationExtractor(
    model="gpt-4",  # 或 "gpt-3.5-turbo"
    temperature=0.3
)

# 处理文本
text = """
张三是一名软件工程师，他在腾讯公司工作。
张三精通 Python 和机器学习。
"""

result = extractor.process_text(text, use_workflow=True)

# 查看结果
print(f"实体数: {len(result['entities'])}")
print(f"关系数: {len(result['relations'])}")
print(f"三元组数: {len(result['triples'])}")
```

### 3. 批量处理

```python
# 处理多个文本块
chunks = [
    "文本块1...",
    "文本块2...",
    "文本块3..."
]

batch_result = extractor.process_chunks(chunks, batch_size=5)

# 自动去重实体
unique_entities = batch_result['entities']
```

### 4. 与 Neo4j 集成

```python
from utils.neo4j import Neo4jKnowledgeGraph

# 连接 Neo4j
kg = Neo4jKnowledgeGraph(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# 转换并存储
neo4j_data = extractor.to_neo4j_format(result)

# 插入实体
kg.insert_entities(neo4j_data['entities'])

# 插入三元组
kg.insert_triples(neo4j_data['triples'])

kg.close()
```

### 5. 完整端到端系统

```python
from example_complete_rag import CompleteRAGSystem

# 初始化系统
rag = CompleteRAGSystem()

# 处理文档（自动：分块 → 提取 → 存储）
rag.process_document(
    text="长文档内容...",
    doc_id="doc_001",
    source="知识库"
)

# 混合检索
result = rag.hybrid_query(
    query="什么是机器学习？",
    top_k=5,
    use_kg=True
)

# 获取格式化上下文（用于 LLM）
context = result['context']

rag.close()
```

## 📊 LangGraph 工作流详解

### 工作流节点

1. **extract_entities_node**
   - 使用 GPT-4 提取实体
   - 识别类型：人物、地点、组织、概念等
   - 返回结构化实体列表

2. **extract_relations_node**
   - 基于已提取的实体
   - 识别实体间的语义关系
   - 计算置信度分数

3. **build_triples_node**
   - 将关系转换为三元组格式
   - (主体, 谓语, 客体)

4. **validate_node**
   - 验证提取结果
   - 统计信息

### 状态管理

```python
class GraphState(TypedDict):
    text: str                    # 输入文本
    entities: List[Entity]       # 提取的实体
    relations: List[Relation]    # 提取的关系
    triples: List[Triple]        # 生成的三元组
    error: Optional[str]         # 错误信息
    metadata: Dict[str, Any]     # 元数据
    iteration: int               # 迭代次数
```

## 🎨 实体和关系格式

### 实体格式

```python
@dataclass
class Entity:
    name: str                          # 实体名称
    entity_type: str                   # 实体类型
    properties: Optional[Dict] = None  # 实体属性
```

示例：
```python
Entity(
    name="张三",
    entity_type="Person",
    properties={"occupation": "工程师"}
)
```

### 关系格式

```python
@dataclass
class Relation:
    subject: str              # 主体
    subject_type: str         # 主体类型
    predicate: str            # 关系类型
    object: str               # 客体
    object_type: str          # 客体类型
    confidence: float = 1.0   # 置信度
    properties: Optional[Dict] = None
```

示例：
```python
Relation(
    subject="张三",
    subject_type="Person",
    predicate="WORKS_AT",
    object="腾讯",
    object_type="Company",
    confidence=0.95
)
```

### 三元组格式

```python
@dataclass
class Triple:
    subject: str              # 主体
    predicate: str            # 谓语/关系
    object: str               # 客体
    subject_type: str = "Entity"
    object_type: str = "Entity"
```

示例：
```python
Triple(
    subject="张三",
    predicate="WORKS_AT",
    object="腾讯",
    subject_type="Person",
    object_type="Company"
)
```

## 🔧 高级配置

### 自定义 Prompt

你可以通过修改 `_extract_entities()` 和 `_extract_relations()` 方法中的 prompt 来自定义提取行为：

```python
# 自定义实体类型
prompt = """
请提取以下类型的实体：
- 技术栈 (Technology)
- 编程语言 (Language)
- 框架 (Framework)
- 工具 (Tool)
...
"""
```

### 使用不同的模型

```python
# 使用 GPT-3.5 Turbo（更快，成本更低）
extractor = EntityRelationExtractor(
    model="gpt-3.5-turbo",
    temperature=0.5
)

# 使用 Azure OpenAI
extractor = EntityRelationExtractor(
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com/",
    model="gpt-4"
)
```

### 调整温度参数

```python
# 更确定性的输出（推荐用于实体提取）
extractor = EntityRelationExtractor(temperature=0.1)

# 更有创造性的输出
extractor = EntityRelationExtractor(temperature=0.8)
```

## 📈 性能优化

### 1. 批处理

```python
# 推荐的批次大小
batch_result = extractor.process_chunks(
    chunks,
    batch_size=5  # 根据 API 限制调整
)
```

### 2. 并发处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 使用线程池并发处理
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(
        lambda chunk: extractor.process_text(chunk),
        chunks
    ))
```

### 3. 缓存结果

```python
import json

# 保存提取结果
with open('extraction_results.json', 'w') as f:
    json.dump({
        'entities': [asdict(e) for e in result['entities']],
        'relations': [asdict(r) for r in result['relations']]
    }, f, ensure_ascii=False, indent=2)
```

## 🐛 故障排查

### 常见问题

**Q: OpenAI API 调用失败？**
```bash
# 检查 API Key
echo $OPENAI_API_KEY

# 测试连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Q: LangGraph 导入错误？**
```bash
# 安装最新版本
pip install --upgrade langgraph langchain-core
```

**Q: JSON 解析错误？**
- 降低 temperature 参数（如 0.1）
- 使用 `response_format={"type": "json_object"}`
- 检查 prompt 是否明确要求 JSON 格式

**Q: 提取结果质量不佳？**
- 使用 GPT-4 替代 GPT-3.5
- 优化 prompt，提供更多示例
- 增加实体类型的详细说明
- 调整 temperature 参数

## 📚 示例场景

### 场景1: 科技文章知识提取

```python
text = """
深度学习是机器学习的一个分支，它基于人工神经网络。
卷积神经网络（CNN）特别适合图像处理任务。
"""

result = extractor.process_text(text)

# 预期结果：
# 实体: 深度学习, 机器学习, 人工神经网络, CNN, 图像处理
# 关系: (深度学习, IS_BRANCH_OF, 机器学习)
#       (深度学习, BASED_ON, 人工神经网络)
#       (CNN, SUITABLE_FOR, 图像处理)
```

### 场景2: 人物关系提取

```python
text = """
张三是李四的导师，李四在清华大学攻读博士学位。
王五是李四的同学，他们一起研究人工智能。
"""

result = extractor.process_text(text)

# 预期结果：
# 实体: 张三, 李四, 王五, 清华大学, 人工智能
# 关系: (张三, MENTOR_OF, 李四)
#       (李四, STUDIES_AT, 清华大学)
#       (王五, CLASSMATE_OF, 李四)
#       (李四, RESEARCHES, 人工智能)
```

### 场景3: 公司组织架构

```python
text = """
腾讯是一家科技公司，总部位于深圳。
马化腾是腾讯的创始人兼CEO。
微信是腾讯开发的即时通讯软件。
"""

result = extractor.process_text(text)

# 预期结果：
# 实体: 腾讯, 深圳, 马化腾, 微信
# 关系: (腾讯, LOCATED_IN, 深圳)
#       (马化腾, FOUNDED, 腾讯)
#       (马化腾, CEO_OF, 腾讯)
#       (微信, DEVELOPED_BY, 腾讯)
```

## 🔍 可视化

### 导出为 JSON

```python
# 导出图谱数据
extractor.visualize_graph(result, "knowledge_graph.json")

# 生成的文件可用于：
# - Neo4j 导入
# - 图谱可视化工具（如 D3.js, Cytoscape）
# - 数据分析
```

### 使用 Neo4j Browser

```cypher
// 查看所有节点
MATCH (n) RETURN n LIMIT 25

// 查看特定类型的关系
MATCH (a)-[r:WORKS_AT]->(b) RETURN a, r, b

// 查找路径
MATCH path = (a {name: "张三"})-[*1..3]-(b {name: "AI"})
RETURN path
```

## 📖 参考资料

- [LangGraph 官方文档](https://github.com/langchain-ai/langgraph)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [Neo4j Cypher 查询语言](https://neo4j.com/docs/cypher-manual/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

