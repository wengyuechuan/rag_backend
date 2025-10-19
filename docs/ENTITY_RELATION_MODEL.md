# 实体关系模型说明

## 概述

本文档说明增强后的实体和关系数据模型，包括实体类型限定、chunk_id追踪、以及实体关系合并功能。

## 实体模型 (Entity)

### 限定的实体类型

系统支持以下11种实体类型（严格限定）：

| 类型 | 英文名称 | 说明 | 示例 |
|------|----------|------|------|
| 人物 | Person | 真实或虚构的人物 | 张三、爱因斯坦 |
| 组织机构 | Organization | 公司、政府、学校等 | 腾讯、哈佛大学 |
| 地点 | Location | 地理位置 | 北京、长江 |
| 产品 | Product | 商品、服务、软件等 | iPhone、微信 |
| 事件 | Event | 历史事件、活动等 | 五四运动、奥运会 |
| 日期时间 | Date | 时间点或时间段 | 2024年、春节 |
| 作品 | Work | 书籍、电影、音乐等创作 | 红楼梦、蒙娜丽莎 |
| 概念 | Concept | 抽象概念、理论等 | 人工智能、量子力学 |
| 资源 | Resource | 自然资源、数据等 | 石油、数据集 |
| 类别 | Category | 分类、类型等 | 编程语言、哺乳动物 |
| 操作 | Operation | 动作、流程等 | 机器学习、数据处理 |

### 实体数据结构

```python
@dataclass
class Entity:
    # 基本信息
    name: str                      # 实体名称
    entity_type: str               # 实体类型（限定类型）
    chunk_ids: List[str]           # 出现的文本块ID列表
    properties: Dict[str, Any]     # 实体属性
    
    # 元信息
    frequency: int                 # 出现频率
    first_seen_chunk: str          # 首次出现的文本块ID
    aliases: List[str]             # 别名列表
    description: str               # 实体描述
    
    # 统计信息
    confidence: float              # 置信度 (0-1)
    importance_score: float        # 重要性得分 (0-1)
```

### 实体示例

```json
{
  "name": "张三",
  "entity_type": "Person",
  "chunk_ids": ["chunk_1", "chunk_5", "chunk_12"],
  "properties": {
    "职业": "工程师",
    "公司": "腾讯"
  },
  "frequency": 3,
  "first_seen_chunk": "chunk_1",
  "aliases": ["小张"],
  "description": "软件工程师",
  "confidence": 0.98,
  "importance_score": 0.85
}
```

### 实体功能

#### 1. 添加文本块
```python
entity.add_chunk("chunk_10")
# 自动更新 frequency 和 chunk_ids
```

#### 2. 合并实体
```python
entity1.merge_with(entity2)
# 合并 chunk_ids、aliases、properties
# 更新 frequency 和 confidence
```

#### 3. 类型验证
```python
# 自动验证和标准化类型
Entity(name="张三", entity_type="person")  # 自动转为 "Person"
Entity(name="微信", entity_type="软件")      # 自动转为 "Product"
```

## 关系模型 (Relation)

### 关系数据结构

```python
@dataclass
class Relation:
    # 基本信息
    subject: str                   # 主体实体名称
    subject_type: str              # 主体类型
    predicate: str                 # 关系类型
    object: str                    # 客体实体名称
    object_type: str               # 客体类型
    chunk_ids: List[str]           # 关系出现的文本块ID列表
    
    # 元信息
    confidence: float              # 置信度 (0-1)
    frequency: int                 # 出现频率
    first_seen_chunk: str          # 首次出现的文本块ID
    properties: Dict[str, Any]     # 关系属性
    
    # 上下文信息
    contexts: List[str]            # 关系出现的上下文片段
```

### 关系示例

```json
{
  "subject": "张三",
  "subject_type": "Person",
  "predicate": "工作于",
  "object": "腾讯",
  "object_type": "Organization",
  "chunk_ids": ["chunk_1", "chunk_8"],
  "confidence": 0.95,
  "frequency": 2,
  "first_seen_chunk": "chunk_1",
  "properties": {
    "职位": "高级工程师",
    "部门": "AI部门"
  },
  "contexts": [
    "张三在腾讯公司工作",
    "张三是腾讯AI部门的工程师"
  ]
}
```

### 关系功能

#### 1. 添加文本块
```python
relation.add_chunk("chunk_15", context="上下文文本")
# 只有当主体、客体和关系都在该文本块中出现时才添加
```

#### 2. 合并关系
```python
relation1.merge_with(relation2)
# 合并 chunk_ids、contexts
# 更新 frequency 和 confidence
```

#### 3. 获取关系唯一标识
```python
key = relation.get_relation_key()
# 返回: "张三|工作于|腾讯"
```

## chunk_ids 追踪机制

### 实体追踪

实体的 `chunk_ids` 记录该实体在哪些文本块中出现过：

```python
# 文本块1: "张三是一名工程师"
entity = Entity(name="张三", entity_type="Person", chunk_ids=["chunk_1"])

# 文本块2: "张三在腾讯工作"
entity.add_chunk("chunk_2")  # chunk_ids = ["chunk_1", "chunk_2"]

# 文本块3: "李四认识张三"
entity.add_chunk("chunk_3")  # chunk_ids = ["chunk_1", "chunk_2", "chunk_3"]
```

### 关系追踪

关系的 `chunk_ids` 只记录当**主体、谓词、客体三者都出现**在同一文本块时的 chunk_id：

```python
# 文本块1: "张三在腾讯工作"
# ✅ 包含：张三（主体）、工作于（谓词）、腾讯（客体）
relation = Relation(
    subject="张三", 
    predicate="工作于", 
    object="腾讯",
    chunk_ids=["chunk_1"]
)

# 文本块2: "张三是工程师"
# ❌ 不包含腾讯（客体），不添加

# 文本块3: "张三在腾讯AI部门"
# ✅ 再次包含完整关系
relation.add_chunk("chunk_3")  # chunk_ids = ["chunk_1", "chunk_3"]
```

## 批量处理与合并

### process_chunks 方法

批量处理多个文本块时，自动合并相同的实体和关系：

```python
extractor = EntityRelationExtractor()

chunks = ["文本块1...", "文本块2...", "文本块3..."]
chunk_ids = ["chunk_1", "chunk_2", "chunk_3"]

result = extractor.process_chunks(chunks, chunk_ids=chunk_ids)
```

### 合并逻辑

#### 实体合并
- 相同 `name` 和 `entity_type` 的实体会合并
- 合并 `chunk_ids`、`aliases`、`properties`
- 更新 `frequency` 为 chunk_ids 的数量
- 取置信度的平均值

#### 关系合并
- 相同 `(subject, predicate, object)` 的关系会合并
- 合并 `chunk_ids` 和 `contexts`
- 更新 `frequency` 为 chunk_ids 的数量
- 取置信度的平均值

### 合并示例

```python
# 文本块1提取
entity1 = Entity(
    name="张三", 
    entity_type="Person",
    chunk_ids=["chunk_1"],
    aliases=["小张"]
)

# 文本块2提取（相同实体）
entity2 = Entity(
    name="张三", 
    entity_type="Person",
    chunk_ids=["chunk_2"],
    description="工程师"
)

# 合并后
merged_entity = {
    "name": "张三",
    "entity_type": "Person",
    "chunk_ids": ["chunk_1", "chunk_2"],  # 合并
    "aliases": ["小张"],
    "description": "工程师",  # 补充信息
    "frequency": 2,  # 更新
    "confidence": 平均值
}
```

## 重要性评分

### 计算公式

```python
importance_score = (frequency_score * 0.7) + (confidence * 0.3)

其中:
frequency_score = entity.frequency / max_frequency
```

### 排序

处理完成后，实体和关系会按重要性排序：

```python
# 按频率和置信度排序
entities.sort(key=lambda e: (e.frequency, e.confidence), reverse=True)
relations.sort(key=lambda r: (r.frequency, r.confidence), reverse=True)
```

## API 使用示例

### 1. 单文本块处理

```python
extractor = EntityRelationExtractor(api_key="your-key")

result = extractor.process_text(
    text="张三是腾讯的工程师",
    chunk_id="chunk_1"
)

print(f"实体: {len(result['entities'])}")
print(f"关系: {len(result['relations'])}")
```

### 2. 多文本块批量处理

```python
chunks = [
    "张三是腾讯的工程师",
    "张三在深圳工作",
    "李四也在腾讯"
]
chunk_ids = ["chunk_1", "chunk_2", "chunk_3"]

result = extractor.process_chunks(chunks, chunk_ids=chunk_ids)

# 查看合并后的实体
for entity in result['entities']:
    print(f"{entity.name} ({entity.entity_type})")
    print(f"  出现在: {entity.chunk_ids}")
    print(f"  频率: {entity.frequency}")
    print(f"  重要性: {entity.importance_score:.2f}")
```

### 3. 查看实体详情

```python
entity = result['entities'][0]

print(f"名称: {entity.name}")
print(f"类型: {entity.entity_type}")
print(f"出现次数: {entity.frequency}")
print(f"首次出现: {entity.first_seen_chunk}")
print(f"所有出现: {entity.chunk_ids}")
print(f"别名: {entity.aliases}")
print(f"描述: {entity.description}")
print(f"置信度: {entity.confidence:.2f}")
print(f"重要性: {entity.importance_score:.2f}")
```

### 4. 查看关系详情

```python
relation = result['relations'][0]

print(f"{relation.subject} --[{relation.predicate}]--> {relation.object}")
print(f"出现次数: {relation.frequency}")
print(f"首次出现: {relation.first_seen_chunk}")
print(f"所有出现: {relation.chunk_ids}")
print(f"上下文: {relation.contexts}")
print(f"置信度: {relation.confidence:.2f}")
```

## 数据导出

### 转换为字典

```python
entity_dict = entity.to_dict()
relation_dict = relation.to_dict()
```

### 导出为 JSON

```python
import json

# 导出实体
with open('entities.json', 'w', encoding='utf-8') as f:
    entities_data = [e.to_dict() for e in result['entities']]
    json.dump(entities_data, f, ensure_ascii=False, indent=2)

# 导出关系
with open('relations.json', 'w', encoding='utf-8') as f:
    relations_data = [r.to_dict() for r in result['relations']]
    json.dump(relations_data, f, ensure_ascii=False, indent=2)
```

## 最佳实践

1. **实体类型**: 始终使用11种限定类型之一，系统会自动验证和标准化
2. **chunk_id追踪**: 提供准确的 chunk_id 以便后续追踪和分析
3. **批量处理**: 对多个文本块使用 `process_chunks` 自动合并
4. **重要性评分**: 利用 `importance_score` 筛选重要实体
5. **上下文保留**: 关系的 `contexts` 字段保留原始上下文，有助于理解

## 与数据库集成

在 `document_service.py` 中，实体和关系会自动存储到数据库的 chunk 表中：

```python
# 每个 chunk 记录
chunk.entities = ["张三", "腾讯", "深圳"]  # 实体名称列表
chunk.relations = [
    {
        "subject": "张三",
        "subject_type": "Person",
        "predicate": "工作于",
        "object": "腾讯",
        "object_type": "Organization",
        "confidence": 0.95,
        "chunk_ids": ["chunk_1", "chunk_3"],
        "contexts": ["张三在腾讯工作"]
    }
]
```

## 总结

- ✅ 实体类型限定为11种标准类型
- ✅ chunk_ids 精确追踪实体和关系的出现位置
- ✅ 自动合并相同实体和关系
- ✅ 计算重要性评分用于排序
- ✅ 保留上下文信息
- ✅ 支持批量处理
- ✅ 完整的元数据和统计信息

