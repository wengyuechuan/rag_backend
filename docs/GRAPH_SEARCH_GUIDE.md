# 图谱搜索使用指南

## 概述

当启用图谱搜索（`use_graph: true`）时，系统会基于实体和关系进行智能搜索，返回结构化的知识图谱信息。

## 搜索类型

### 1. 向量搜索（vector）
```json
{
  "use_vector": true,
  "use_graph": false
}
```
- 基于语义相似度的文本搜索
- 返回相关的文本块

### 2. 图谱搜索（graph）
```json
{
  "use_vector": false,
  "use_graph": true
}
```
- 基于实体和关系的结构化搜索
- 返回匹配的实体及其关系网络

### 3. 混合搜索（hybrid）
```json
{
  "use_vector": true,
  "use_graph": true
}
```
- 结合向量搜索和图谱搜索
- 返回文本块 + 图谱增强信息

## 请求示例

### 基本图谱搜索

```bash
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "小明的父亲是谁",
    "knowledge_base_id": 1,
    "top_k": 5,
    "use_vector": false,
    "use_graph": true
  }'
```

### 混合搜索（推荐）

```bash
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "小明",
    "knowledge_base_id": 1,
    "top_k": 5,
    "use_vector": true,
    "use_graph": true
  }'
```

## 响应结构

### 完整响应格式

```json
{
  "query": "小明",
  "results": [...],           // 文本块搜索结果
  "total": 5,
  "processing_time": 0.123,
  "graph_results": [...],     // 图谱搜索结果（当 use_graph=true 时）
  "search_type": "hybrid"     // "vector", "graph", "hybrid"
}
```

### 1. 文本块搜索结果（results）

#### 仅向量搜索时
```json
{
  "results": [
    {
      "chunk_id": 123,
      "document_id": 45,
      "document_title": "家庭关系文档",
      "content": "小明的父亲是张三，母亲是李四...",
      "score": 0.85,
      "chunk_index": 2,
      "entities": null,        // 向量搜索时为 null
      "relations": null,
      "graph_context": null
    }
  ]
}
```

#### 混合搜索时（向量+图谱）
```json
{
  "results": [
    {
      "chunk_id": 123,
      "document_id": 45,
      "document_title": "家庭关系文档",
      "content": "小明的父亲是张三，母亲是李四...",
      "score": 0.85,
      "chunk_index": 2,
      
      // 图谱增强信息
      "entities": ["小明", "张三", "李四"],
      "relations": [
        {
          "subject": "小明",
          "subject_type": "Person",
          "predicate": "父亲",
          "object": "张三",
          "object_type": "Person",
          "confidence": 0.95,
          "chunk_ids": ["123", "456"],
          "contexts": ["小明的父亲是张三"]
        }
      ],
      "graph_context": {
        "matched_entity": "小明",
        "entity_type": "Person",
        "related_count": 3
      }
    }
  ]
}
```

### 2. 图谱搜索结果（graph_results）

```json
{
  "graph_results": [
    {
      "entity_name": "小明",
      "entity_type": "Person",
      "related_entities": [
        {
          "name": "张三",
          "type": "Person",
          "relation": "父亲"
        },
        {
          "name": "李四",
          "type": "Person",
          "relation": "母亲"
        },
        {
          "name": "第一小学",
          "type": "Organization",
          "relation": "就读于"
        }
      ],
      "relations": [
        {
          "subject": "小明",
          "subject_type": "Person",
          "predicate": "父亲",
          "object": "张三",
          "object_type": "Person",
          "confidence": 0.95,
          "chunk_id": 123
        },
        {
          "subject": "小明",
          "subject_type": "Person",
          "predicate": "母亲",
          "object": "李四",
          "object_type": "Person",
          "confidence": 0.92,
          "chunk_id": 123
        }
      ],
      "chunk_ids": ["123", "456", "789"],
      "relevance_score": 0.95
    }
  ]
}
```

## 字段说明

### SearchResult（文本块结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| `chunk_id` | int | 文本块ID |
| `document_id` | int | 文档ID |
| `document_title` | string | 文档标题 |
| `content` | string | 文本块内容 |
| `score` | float | 相关性得分（0-1） |
| `chunk_index` | int | 文本块索引 |
| `entities` | string[] | 实体列表（图谱搜索时） |
| `relations` | object[] | 关系列表（图谱搜索时） |
| `graph_context` | object | 图谱上下文信息 |

### GraphSearchResult（图谱结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| `entity_name` | string | 实体名称 |
| `entity_type` | string | 实体类型 |
| `related_entities` | object[] | 相关实体列表 |
| `relations` | object[] | 关系列表 |
| `chunk_ids` | string[] | 相关文本块ID列表 |
| `relevance_score` | float | 相关性得分（0-1） |

### Relation（关系对象）

| 字段 | 类型 | 说明 |
|------|------|------|
| `subject` | string | 主体实体 |
| `subject_type` | string | 主体类型 |
| `predicate` | string | 关系类型 |
| `object` | string | 客体实体 |
| `object_type` | string | 客体类型 |
| `confidence` | float | 置信度（0-1） |
| `chunk_ids` | string[] | 关系出现的文本块列表 |
| `contexts` | string[] | 上下文句子列表 |

## 使用场景

### 场景1：查找关系

**查询**："小明的父亲是谁"

**推荐配置**：
```json
{
  "use_vector": false,
  "use_graph": true
}
```

**返回**：
- 找到实体"小明"
- 返回"父亲"关系指向的实体"张三"
- 显示关系出现的文本块

### 场景2：实体信息聚合

**查询**："小明"

**推荐配置**：
```json
{
  "use_vector": false,
  "use_graph": true
}
```

**返回**：
- 实体"小明"的所有关系
- 相关实体列表（父亲、母亲、学校等）
- 所有提到小明的文本块

### 场景3：语义搜索 + 关系验证

**查询**："谁在第一小学上学"

**推荐配置**：
```json
{
  "use_vector": true,
  "use_graph": true
}
```

**返回**：
- 语义相关的文本块
- 提取的实体和关系
- 可验证哪些人与"第一小学"有"就读于"关系

## 评分机制

### 向量搜索评分
- 基于语义相似度
- 使用余弦相似度计算
- 范围：0-1（越高越相关）

### 图谱搜索评分
```python
relevance_score = base_score + relation_bonus + frequency_bonus

其中：
- base_score: 名称匹配度（完全匹配=1.0，部分匹配=0.7）
- relation_bonus: 关系数量 * 0.1（最多+0.5）
- frequency_bonus: 出现次数 * 0.05（最多+0.3）
```

## Python 示例

### 仅图谱搜索
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/search/",
    json={
        "query": "小明的父亲",
        "knowledge_base_id": 1,
        "top_k": 5,
        "use_vector": False,
        "use_graph": True
    }
)

data = response.json()

# 查看图谱结果
for graph_result in data.get("graph_results", []):
    print(f"实体: {graph_result['entity_name']} ({graph_result['entity_type']})")
    print(f"相关性: {graph_result['relevance_score']:.2f}")
    
    print("相关实体:")
    for related in graph_result['related_entities']:
        print(f"  - {related['name']} ({related['type']}) - {related['relation']}")
    
    print(f"出现在 {len(graph_result['chunk_ids'])} 个文本块中")
    print()
```

### 混合搜索
```python
response = requests.post(
    "http://localhost:8000/api/v1/search/",
    json={
        "query": "小明",
        "knowledge_base_id": 1,
        "top_k": 5,
        "use_vector": True,
        "use_graph": True
    }
)

data = response.json()

print(f"搜索类型: {data['search_type']}")
print(f"找到 {data['total']} 个文本块结果")
print(f"找到 {len(data.get('graph_results', []))} 个图谱结果")

# 查看文本块结果（包含实体和关系）
for result in data['results']:
    print(f"\n文本块 {result['chunk_id']}:")
    print(f"内容: {result['content'][:100]}...")
    print(f"评分: {result['score']:.2f}")
    
    if result['entities']:
        print(f"实体: {', '.join(result['entities'])}")
    
    if result['relations']:
        print(f"关系数: {len(result['relations'])}")
        for rel in result['relations'][:2]:
            print(f"  {rel['subject']} --[{rel['predicate']}]--> {rel['object']}")
```

## 最佳实践

### 1. 选择合适的搜索模式

- **回答事实性问题**（谁、什么、哪里）：使用图谱搜索
- **语义理解问题**（怎么样、为什么）：使用向量搜索
- **复杂查询**：使用混合搜索

### 2. 优化查询

**精确实体查询**：
```json
// 好
{"query": "张三"}

// 也可以
{"query": "张三是谁"}
```

**关系查询**：
```json
// 推荐
{"query": "张三的父亲"}

// 也可以用自然语言
{"query": "谁是张三的父亲"}
```

### 3. 处理结果

```python
# 优先使用图谱结果（更结构化）
if data['graph_results']:
    # 处理图谱结果
    for gr in data['graph_results']:
        process_graph_result(gr)
else:
    # 回退到文本结果
    for result in data['results']:
        process_text_result(result)
```

### 4. 可视化关系网络

```python
def build_graph_visualization(graph_results):
    """构建关系网络可视化数据"""
    nodes = []
    edges = []
    
    for gr in graph_results:
        # 中心实体
        nodes.append({
            'id': gr['entity_name'],
            'label': gr['entity_name'],
            'type': gr['entity_type'],
            'size': gr['relevance_score'] * 100
        })
        
        # 相关实体和关系
        for rel_entity in gr['related_entities']:
            nodes.append({
                'id': rel_entity['name'],
                'label': rel_entity['name'],
                'type': rel_entity['type']
            })
            
            edges.append({
                'source': gr['entity_name'],
                'target': rel_entity['name'],
                'label': rel_entity['relation']
            })
    
    return {'nodes': nodes, 'edges': edges}
```

## 注意事项

1. **需要NER处理**：图谱搜索依赖于实体关系提取，确保知识库启用了 `enable_ner: true`

2. **首次查询可能较慢**：系统需要遍历所有文本块的实体和关系

3. **大小写不敏感**：查询"小明"和"xiǎo míng"效果相同

4. **部分匹配**：查询"小"会匹配"小明"、"小红"等实体

5. **性能优化**：
   - 限制 `top_k` 值（建议5-10）
   - 对大知识库优先使用向量搜索筛选范围

## 错误处理

### 无图谱结果
```json
{
  "query": "xxx",
  "results": [],
  "total": 0,
  "processing_time": 0.05,
  "graph_results": null,
  "search_type": "graph"
}
```

**原因**：
- 未启用NER功能
- 查询的实体不存在
- 文档尚未处理

**解决方案**：
1. 确认知识库启用了 `enable_ner: true`
2. 检查文档处理状态
3. 尝试其他查询词

## 总结

图谱搜索提供了：
- ✅ 结构化的实体和关系信息
- ✅ 精确的关系匹配
- ✅ 实体出现位置追踪
- ✅ 关系网络可视化支持
- ✅ 与向量搜索的无缝结合

推荐在需要精确答案、关系推理、知识图谱应用的场景中使用！

