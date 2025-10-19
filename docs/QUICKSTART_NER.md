# 快速开始 - 实体关系提取

## 🎯 5分钟上手

### 步骤1: 安装依赖

```bash
pip install langgraph langchain-core openai
```

### 步骤2: 设置 API Key

```bash
# Linux/Mac
export OPENAI_API_KEY='sk-your-api-key-here'

# Windows PowerShell
$env:OPENAI_API_KEY='sk-your-api-key-here'

# Windows CMD
set OPENAI_API_KEY=sk-your-api-key-here
```

### 步骤3: 运行测试

```bash
python utils/chunk_to_ner.py
```

### 步骤4: 使用代码

```python
from utils.chunk_to_ner import EntityRelationExtractor

# 初始化
extractor = EntityRelationExtractor(model="gpt-4")

# 提取
text = "张三在腾讯工作，他是一名 Python 工程师。"
result = extractor.process_text(text)

# 查看结果
for entity in result['entities']:
    print(f"实体: {entity.name} ({entity.entity_type})")

for triple in result['triples']:
    print(f"三元组: {triple.subject} --[{triple.predicate}]--> {triple.object}")
```

## 🔥 完整示例

```bash
# 运行完整的端到端 RAG 系统
python example_complete_rag.py
```

## 💡 提示

1. 首次运行时会调用 OpenAI API，需要网络连接
2. 建议先用 `gpt-3.5-turbo` 测试（更快，更便宜）
3. 确保 Ollama 正在运行（用于向量化）
4. 如果使用 Neo4j，确保数据库在运行

## 📚 更多信息

- 详细使用指南: [USAGE_GUIDE.md](USAGE_GUIDE.md)
- 完整文档: [README.md](README.md)

