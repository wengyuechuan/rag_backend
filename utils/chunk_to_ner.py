"""
基于 LangGraph 的实体关系提取工作流
使用 OpenAI 进行实体识别和关系提取，构建知识图谱三元组
"""

import os
import json
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, asdict, field
import operator

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️  LangGraph 未安装，部分功能不可用")

from openai import OpenAI


class EntityType:
    """实体类型枚举"""
    PERSON = "Person"              # 人物
    ORGANIZATION = "Organization"  # 组织机构
    LOCATION = "Location"          # 地点
    PRODUCT = "Product"            # 产品
    EVENT = "Event"                # 事件
    DATE = "Date"                  # 日期时间
    WORK = "Work"                  # 作品（书籍、电影等）
    CONCEPT = "Concept"            # 概念
    RESOURCE = "Resource"          # 资源
    CATEGORY = "Category"          # 类别
    OPERATION = "Operation"        # 操作/行为
    
    @classmethod
    def all_types(cls) -> List[str]:
        """获取所有实体类型"""
        return [
            cls.PERSON, cls.ORGANIZATION, cls.LOCATION, cls.PRODUCT,
            cls.EVENT, cls.DATE, cls.WORK, cls.CONCEPT,
            cls.RESOURCE, cls.CATEGORY, cls.OPERATION
        ]
    
    @classmethod
    def validate(cls, entity_type: str) -> str:
        """验证并标准化实体类型"""
        all_types = cls.all_types()
        
        # 精确匹配
        if entity_type in all_types:
            return entity_type
        
        # 大小写不敏感匹配
        entity_type_lower = entity_type.lower()
        for valid_type in all_types:
            if valid_type.lower() == entity_type_lower:
                return valid_type
        
        # 部分匹配或映射
        type_mapping = {
            'people': cls.PERSON,
            'person': cls.PERSON,
            'human': cls.PERSON,
            'org': cls.ORGANIZATION,
            'company': cls.ORGANIZATION,
            'place': cls.LOCATION,
            'geo': cls.LOCATION,
            'time': cls.DATE,
            'datetime': cls.DATE,
            'book': cls.WORK,
            'movie': cls.WORK,
            'idea': cls.CONCEPT,
        }
        
        if entity_type_lower in type_mapping:
            return type_mapping[entity_type_lower]
        
        # 默认返回 Concept
        return cls.CONCEPT


@dataclass
class Entity:
    """
    实体数据结构（增强版）
    
    包含实体的完整信息和元数据
    """
    name: str                                    # 实体名称
    entity_type: str                             # 实体类型（限定类型）
    chunk_ids: List[str] = field(default_factory=list)  # 出现的文本块ID列表
    properties: Optional[Dict[str, Any]] = field(default_factory=dict)  # 实体属性
    
    # 元信息
    frequency: int = 1                           # 出现频率
    first_seen_chunk: Optional[str] = None       # 首次出现的文本块ID
    aliases: List[str] = field(default_factory=list)  # 别名列表
    description: Optional[str] = None            # 实体描述
    
    # 统计信息
    confidence: float = 1.0                      # 置信度
    importance_score: float = 0.0                # 重要性得分
    
    def __post_init__(self):
        """验证并标准化实体类型"""
        self.entity_type = EntityType.validate(self.entity_type)
        
        # 如果 chunk_ids 非空且 first_seen_chunk 未设置
        if self.chunk_ids and not self.first_seen_chunk:
            self.first_seen_chunk = self.chunk_ids[0]
    
    def add_chunk(self, chunk_id: str):
        """添加文本块ID"""
        if chunk_id not in self.chunk_ids:
            self.chunk_ids.append(chunk_id)
            self.frequency = len(self.chunk_ids)
            
            # 设置首次出现
            if not self.first_seen_chunk:
                self.first_seen_chunk = chunk_id
    
    def merge_with(self, other: 'Entity'):
        """
        合并另一个实体的信息
        
        用于处理同一实体的多次出现
        """
        # 合并 chunk_ids
        for chunk_id in other.chunk_ids:
            self.add_chunk(chunk_id)
        
        # 合并别名
        if other.name != self.name and other.name not in self.aliases:
            self.aliases.append(other.name)
        
        for alias in other.aliases:
            if alias not in self.aliases and alias != self.name:
                self.aliases.append(alias)
        
        # 合并属性
        if other.properties:
            self.properties.update(other.properties)
        
        # 更新置信度（取平均值）
        self.confidence = (self.confidence + other.confidence) / 2
        
        # 更新描述（如果当前没有）
        if not self.description and other.description:
            self.description = other.description
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'entity_type': self.entity_type,
            'chunk_ids': self.chunk_ids,
            'properties': self.properties,
            'frequency': self.frequency,
            'first_seen_chunk': self.first_seen_chunk,
            'aliases': self.aliases,
            'description': self.description,
            'confidence': self.confidence,
            'importance_score': self.importance_score
        }


@dataclass
class Relation:
    """
    关系数据结构（增强版）
    
    记录实体之间的关系及其出现位置
    """
    subject: str                                 # 主体实体名称
    subject_type: str                            # 主体类型
    predicate: str                               # 关系类型
    object: str                                  # 客体实体名称
    object_type: str                             # 客体类型
    chunk_ids: List[str] = field(default_factory=list)  # 关系出现的文本块ID列表
    
    # 元信息
    confidence: float = 1.0                      # 置信度
    frequency: int = 1                           # 出现频率
    first_seen_chunk: Optional[str] = None       # 首次出现的文本块ID
    properties: Optional[Dict[str, Any]] = field(default_factory=dict)  # 关系属性
    
    # 上下文信息
    contexts: List[str] = field(default_factory=list)  # 关系出现的上下文片段
    
    def __post_init__(self):
        """初始化后处理"""
        # 验证实体类型
        self.subject_type = EntityType.validate(self.subject_type)
        self.object_type = EntityType.validate(self.object_type)
        
        # 设置首次出现
        if self.chunk_ids and not self.first_seen_chunk:
            self.first_seen_chunk = self.chunk_ids[0]
    
    def add_chunk(self, chunk_id: str, context: Optional[str] = None):
        """
        添加文本块ID
        
        只有当主体、客体和关系都在该文本块中出现时才添加
        """
        if chunk_id not in self.chunk_ids:
            self.chunk_ids.append(chunk_id)
            self.frequency = len(self.chunk_ids)
            
            # 设置首次出现
            if not self.first_seen_chunk:
                self.first_seen_chunk = chunk_id
            
            # 添加上下文
            if context and context not in self.contexts:
                self.contexts.append(context)
    
    def get_relation_key(self) -> str:
        """获取关系的唯一标识"""
        return f"{self.subject}|{self.predicate}|{self.object}"
    
    def merge_with(self, other: 'Relation'):
        """
        合并另一个关系的信息
        
        用于处理同一关系在不同文本块中的出现
        """
        # 合并 chunk_ids
        for i, chunk_id in enumerate(other.chunk_ids):
            context = other.contexts[i] if i < len(other.contexts) else None
            self.add_chunk(chunk_id, context)
        
        # 更新置信度（取平均值）
        self.confidence = (self.confidence + other.confidence) / 2
        
        # 合并属性
        if other.properties:
            self.properties.update(other.properties)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'subject': self.subject,
            'subject_type': self.subject_type,
            'predicate': self.predicate,
            'object': self.object,
            'object_type': self.object_type,
            'chunk_ids': self.chunk_ids,
            'confidence': self.confidence,
            'frequency': self.frequency,
            'first_seen_chunk': self.first_seen_chunk,
            'properties': self.properties,
            'contexts': self.contexts
        }


@dataclass
class Triple:
    """三元组数据结构"""
    subject: str
    predicate: str
    object: str
    subject_type: str = "Entity"
    object_type: str = "Entity"


class GraphState(TypedDict):
    """LangGraph 工作流状态"""
    text: str                                      # 输入文本
    entities: List[Entity]                         # 提取的实体
    relations: List[Relation]                      # 提取的关系
    triples: List[Triple]                          # 生成的三元组
    error: Optional[str]                           # 错误信息
    metadata: Dict[str, Any]                       # 元数据
    iteration: Annotated[int, operator.add]        # 迭代次数


class EntityRelationExtractor:
    """
    实体关系提取器（基于 LangGraph 工作流）
    
    功能：
    1. 使用 OpenAI 提取实体
    2. 使用 OpenAI 提取关系
    3. 构建知识图谱三元组
    4. 工作流状态管理
    5. 与 Neo4j 集成
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_retries: int = 3
    ):
        """
        初始化实体关系提取器
        
        Args:
            api_key: OpenAI API 密钥
            base_url: API 基础 URL（用于自定义端点）
            model: 使用的模型名称
            temperature: 温度参数（控制输出随机性）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        
        # 初始化 OpenAI 客户端
        if self.base_url:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = OpenAI(api_key=self.api_key)
        
        # 初始化工作流
        if LANGGRAPH_AVAILABLE:
            self.workflow = self._build_workflow()
            self.app = self.workflow.compile()
        else:
            self.workflow = None
            self.app = None
            print("⚠️  LangGraph 工作流未初始化")
    
    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("extract_entities", self._extract_entities_node)
        workflow.add_node("extract_relations", self._extract_relations_node)
        workflow.add_node("build_triples", self._build_triples_node)
        workflow.add_node("validate", self._validate_node)
        
        # 设置入口点
        workflow.set_entry_point("extract_entities")
        
        # 添加边
        workflow.add_edge("extract_entities", "extract_relations")
        workflow.add_edge("extract_relations", "build_triples")
        workflow.add_edge("build_triples", "validate")
        workflow.add_edge("validate", END)
        
        return workflow
    
    # ==================== LangGraph 节点函数 ====================
    
    def _extract_entities_node(self, state: GraphState) -> GraphState:
        """实体提取节点"""
        print(f"🔍 [步骤1] 实体提取...")
        
        try:
            entities = self._extract_entities(state["text"])
            print(f"  ✅ 提取到 {len(entities)} 个实体")
            
            return {
                **state,
                "entities": entities,
                "iteration": 1
            }
        except Exception as e:
            print(f"  ❌ 实体提取失败: {e}")
            return {
                **state,
                "entities": [],
                "error": str(e),
                "iteration": 1
            }
    
    def _extract_relations_node(self, state: GraphState) -> GraphState:
        """关系提取节点"""
        print(f"🔗 [步骤2] 关系提取...")
        
        try:
            relations = self._extract_relations(
                state["text"],
                state.get("entities", [])
            )
            print(f"  ✅ 提取到 {len(relations)} 个关系")
            
            return {
                **state,
                "relations": relations,
                "iteration": 1
            }
        except Exception as e:
            print(f"  ❌ 关系提取失败: {e}")
            return {
                **state,
                "relations": [],
                "error": str(e),
                "iteration": 1
            }
    
    def _build_triples_node(self, state: GraphState) -> GraphState:
        """构建三元组节点"""
        print(f"📦 [步骤3] 构建三元组...")
        
        relations = state.get("relations", [])
        triples = []
        
        for rel in relations:
            triple = Triple(
                subject=rel.subject,
                predicate=rel.predicate,
                object=rel.object,
                subject_type=rel.subject_type,
                object_type=rel.object_type
            )
            triples.append(triple)
        
        print(f"  ✅ 生成 {len(triples)} 个三元组")
        
        return {
            **state,
            "triples": triples,
            "iteration": 1
        }
    
    def _validate_node(self, state: GraphState) -> GraphState:
        """验证节点"""
        print(f"✓ [步骤4] 验证结果...")
        
        # 简单验证
        entities_count = len(state.get("entities", []))
        relations_count = len(state.get("relations", []))
        triples_count = len(state.get("triples", []))
        
        print(f"  实体数: {entities_count}")
        print(f"  关系数: {relations_count}")
        print(f"  三元组数: {triples_count}")
        
        return {
            **state,
            "metadata": {
                "entities_count": entities_count,
                "relations_count": relations_count,
                "triples_count": triples_count
            },
            "iteration": 1
        }
    
    # ==================== OpenAI 调用函数 ====================
    
    def _extract_entities(self, text: str, chunk_id: Optional[str] = None) -> List[Entity]:
        """
        使用 OpenAI 提取实体
        
        Args:
            text: 输入文本
            chunk_id: 文本块ID（可选）
            
        Returns:
            实体列表
        """
        entity_types_desc = """
实体类型说明（必须使用以下类型之一）：
1. Person - 人物：真实或虚构的人物，如"张三"、"爱因斯坦"
2. Organization - 组织机构：公司、政府、学校等，如"腾讯"、"哈佛大学"
3. Location - 地点：地理位置，如"北京"、"长江"
4. Product - 产品：商品、服务、软件等，如"iPhone"、"微信"
5. Event - 事件：历史事件、活动等，如"五四运动"、"奥运会"
6. Date - 日期时间：时间点或时间段，如"2024年"、"春节"
7. Work - 作品：书籍、电影、音乐等创作，如"红楼梦"、"蒙娜丽莎"
8. Concept - 概念：抽象概念、理论等，如"人工智能"、"量子力学"
9. Resource - 资源：自然资源、数据等，如"石油"、"数据集"
10. Category - 类别：分类、类型等，如"编程语言"、"哺乳动物"
11. Operation - 操作/行为：动作、流程等，如"机器学习"、"数据处理"
"""
        
        prompt = f"""
请从以下文本中提取所有实体，并按照 JSON 格式返回。

文本：
{text}

{entity_types_desc}

要求：
1. 准确识别文本中的实体
2. entity_type 必须是上述11种类型之一（严格匹配英文名称）
3. 提供实体的描述、别名等属性
4. 对于重要实体，可以添加 description 字段
5. 确保输出是有效的 JSON 格式

输出格式：
{{
    "entities": [
        {{
            "name": "实体名称",
            "entity_type": "Person|Organization|Location|Product|Event|Date|Work|Concept|Resource|Category|Operation",
            "description": "实体描述（可选）",
            "aliases": ["别名1", "别名2"],
            "properties": {{
                "key1": "value1",
                "key2": "value2"
            }},
            "confidence": 0.95
        }}
    ]
}}

示例：
{{
    "entities": [
        {{
            "name": "张三",
            "entity_type": "Person",
            "description": "软件工程师",
            "aliases": ["小张"],
            "properties": {{"职业": "工程师", "公司": "腾讯"}},
            "confidence": 0.98
        }},
        {{
            "name": "人工智能",
            "entity_type": "Concept",
            "description": "计算机科学的一个分支",
            "properties": {{"领域": "计算机科学"}},
            "confidence": 1.0
        }}
    ]
}}

请只返回 JSON，不要包含其他说明文字。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的实体识别专家，擅长从文本中提取结构化的实体信息。必须严格遵守实体类型的定义。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            entities = []
            
            for entity_data in result.get("entities", []):
                # 创建实体
                entity = Entity(
                    name=entity_data.get("name", ""),
                    entity_type=entity_data.get("entity_type", "Concept"),
                    chunk_ids=[chunk_id] if chunk_id else [],
                    properties=entity_data.get("properties", {}),
                    description=entity_data.get("description"),
                    aliases=entity_data.get("aliases", []),
                    confidence=entity_data.get("confidence", 0.8),
                    first_seen_chunk=chunk_id
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            print(f"实体提取错误: {e}")
            return []
    
    def _extract_relations(
        self,
        text: str,
        entities: List[Entity],
        chunk_id: Optional[str] = None
    ) -> List[Relation]:
        """
        使用 OpenAI 提取关系
        
        Args:
            text: 输入文本
            entities: 已提取的实体列表
            chunk_id: 文本块ID（可选）
            
        Returns:
            关系列表
        """
        # 构建实体列表字符串
        entity_names = [e.name for e in entities]
        entity_info = "\n".join([f"- {e.name} ({e.entity_type})" for e in entities])
        
        prompt = f"""
请从以下文本中提取实体之间的关系，并按照 JSON 格式返回。

文本：
{text}

已识别的实体：
{entity_info}

要求：
1. 只提取上述实体之间的关系
2. 关系应该是有意义的动作、状态或连接
3. 为每个关系提供置信度（0-1之间）
4. 提取关系所在的上下文句子
5. subject_type 和 object_type 必须与已识别实体的类型一致
6. 确保输出是有效的 JSON 格式

输出格式：
{{
    "relations": [
        {{
            "subject": "主体实体名称",
            "subject_type": "主体类型",
            "predicate": "关系类型",
            "object": "客体实体名称",
            "object_type": "客体类型",
            "confidence": 0.95,
            "context": "关系所在的句子或短语",
            "properties": {{
                "description": "关系描述",
                "time": "时间信息（如果有）"
            }}
        }}
    ]
}}

常见关系类型示例：
- 人物关系：朋友、同事、家人、上下级、师生
- 所属关系：属于、隶属、包含、拥有
- 行为关系：创建、发明、撰写、领导、开发
- 特征关系：具有、表现、展示、是
- 位置关系：位于、来自、在
- 时间关系：发生于、开始于、结束于

示例：
{{
    "relations": [
        {{
            "subject": "张三",
            "subject_type": "Person",
            "predicate": "工作于",
            "object": "腾讯",
            "object_type": "Organization",
            "confidence": 0.95,
            "context": "张三在腾讯公司工作",
            "properties": {{"职位": "工程师"}}
        }}
    ]
}}

请只返回 JSON，不要包含其他说明文字。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的关系抽取专家，擅长识别实体之间的语义关系。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            relations = []
            
            for rel_data in result.get("relations", []):
                # 提取上下文
                context = rel_data.get("context", "")
                
                # 创建关系
                relation = Relation(
                    subject=rel_data.get("subject", ""),
                    subject_type=rel_data.get("subject_type", "Concept"),
                    predicate=rel_data.get("predicate", "RELATES_TO"),
                    object=rel_data.get("object", ""),
                    object_type=rel_data.get("object_type", "Concept"),
                    chunk_ids=[chunk_id] if chunk_id else [],
                    confidence=rel_data.get("confidence", 0.8),
                    first_seen_chunk=chunk_id,
                    properties=rel_data.get("properties", {}),
                    contexts=[context] if context else []
                )
                relations.append(relation)
            
            return relations
            
        except Exception as e:
            print(f"关系提取错误: {e}")
            return []
    
    # ==================== 主要接口 ====================
    
    def process_text(
        self,
        text: str,
        chunk_id: Optional[str] = None,
        use_workflow: bool = True
    ) -> Dict[str, Any]:
        """
        处理文本，提取实体和关系
        
        Args:
            text: 输入文本
            chunk_id: 文本块ID（可选）
            use_workflow: 是否使用 LangGraph 工作流
            
        Returns:
            包含实体、关系和三元组的字典
        """
        if use_workflow and self.app is not None:
            # 使用 LangGraph 工作流
            initial_state = {
                "text": text,
                "entities": [],
                "relations": [],
                "triples": [],
                "error": None,
                "metadata": {},
                "iteration": 0
            }
            
            print("🚀 启动 LangGraph 工作流...")
            print("=" * 60)
            
            final_state = self.app.invoke(initial_state)
            
            print("=" * 60)
            print("✅ 工作流完成\n")
            
            return {
                "entities": final_state.get("entities", []),
                "relations": final_state.get("relations", []),
                "triples": final_state.get("triples", []),
                "metadata": final_state.get("metadata", {}),
                "error": final_state.get("error")
            }
        else:
            # 直接调用（不使用工作流）
            print("🔄 直接处理模式...")
            
            entities = self._extract_entities(text, chunk_id)
            relations = self._extract_relations(text, entities, chunk_id)
            
            triples = []
            for rel in relations:
                triple = Triple(
                    subject=rel.subject,
                    predicate=rel.predicate,
                    object=rel.object,
                    subject_type=rel.subject_type,
                    object_type=rel.object_type
                )
                triples.append(triple)
            
            return {
                "entities": entities,
                "relations": relations,
                "triples": triples,
                "metadata": {
                    "entities_count": len(entities),
                    "relations_count": len(relations),
                    "triples_count": len(triples)
                }
            }
    
    def process_chunks(
        self,
        chunks: List[str],
        chunk_ids: Optional[List[str]] = None,
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """
        批量处理文本块（支持实体和关系合并）
        
        Args:
            chunks: 文本块列表
            chunk_ids: 文本块ID列表（可选，与chunks对应）
            batch_size: 批次大小
            
        Returns:
            汇总的提取结果（包含合并的实体和关系）
        """
        # 如果没有提供 chunk_ids，自动生成
        if not chunk_ids:
            chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]
        
        # 使用字典存储实体和关系，方便合并
        entity_dict = {}  # key: (name, entity_type) -> Entity
        relation_dict = {}  # key: (subject, predicate, object) -> Relation
        all_triples = []
        
        total = len(chunks)
        
        for i in range(0, total, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_ids = chunk_ids[i:i + batch_size]
            
            print(f"\n处理批次 {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
            
            for j, (chunk_text, chunk_id) in enumerate(zip(batch_chunks, batch_ids)):
                print(f"\n--- 块 {i+j+1}/{total} (ID: {chunk_id}) ---")
                
                # 处理单个块
                result = self.process_text(chunk_text, chunk_id=chunk_id, use_workflow=False)
                
                # 合并实体
                for entity in result["entities"]:
                    key = (entity.name, entity.entity_type)
                    
                    if key in entity_dict:
                        # 实体已存在，合并信息
                        entity_dict[key].merge_with(entity)
                    else:
                        # 新实体
                        entity_dict[key] = entity
                
                # 合并关系
                for relation in result["relations"]:
                    key = (relation.subject, relation.predicate, relation.object)
                    
                    if key in relation_dict:
                        # 关系已存在，合并信息
                        relation_dict[key].merge_with(relation)
                    else:
                        # 新关系
                        relation_dict[key] = relation
                
                # 收集三元组
                all_triples.extend(result["triples"])
        
        # 转换为列表
        merged_entities = list(entity_dict.values())
        merged_relations = list(relation_dict.values())
        
        # 按频率排序（重要性）
        merged_entities.sort(key=lambda e: (e.frequency, e.confidence), reverse=True)
        merged_relations.sort(key=lambda r: (r.frequency, r.confidence), reverse=True)
        
        # 计算重要性得分
        if merged_entities:
            max_frequency = max(e.frequency for e in merged_entities)
            for entity in merged_entities:
                # 重要性 = (频率权重 * 0.7) + (置信度权重 * 0.3)
                freq_score = entity.frequency / max_frequency if max_frequency > 0 else 0
                entity.importance_score = (freq_score * 0.7) + (entity.confidence * 0.3)
        
        print(f"\n{'='*60}")
        print(f"📊 处理完成：")
        print(f"   总文本块数: {total}")
        print(f"   唯一实体数: {len(merged_entities)}")
        print(f"   唯一关系数: {len(merged_relations)}")
        print(f"   三元组数: {len(all_triples)}")
        print(f"{'='*60}\n")
        
        return {
            "entities": merged_entities,
            "relations": merged_relations,
            "triples": all_triples,
            "metadata": {
                "total_chunks": total,
                "entities_count": len(merged_entities),
                "relations_count": len(merged_relations),
                "triples_count": len(all_triples),
                "processed_chunk_ids": chunk_ids
            }
        }
    
    def to_neo4j_format(
        self,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        转换为 Neo4j 兼容格式
        
        Args:
            result: 提取结果
            
        Returns:
            Neo4j 格式的数据
        """
        from utils.neo4j import Triple as Neo4jTriple, Entity as Neo4jEntity
        
        # 转换实体
        neo4j_entities = []
        for entity in result["entities"]:
            neo4j_entities.append(
                Neo4jEntity(
                    name=entity.name,
                    label=entity.entity_type,
                    properties=entity.properties
                )
            )
        
        # 转换三元组
        neo4j_triples = []
        for triple in result["triples"]:
            neo4j_triples.append(
                Neo4jTriple(
                    subject=triple.subject,
                    subject_label=triple.subject_type,
                    predicate=triple.predicate,
                    object=triple.object,
                    object_label=triple.object_type
                )
            )
        
        return {
            "entities": neo4j_entities,
            "triples": neo4j_triples
        }
    
    def visualize_graph(
        self,
        result: Dict[str, Any],
        output_file: str = "knowledge_graph.json"
    ):
        """
        可视化知识图谱（导出为 JSON）
        
        Args:
            result: 提取结果
            output_file: 输出文件路径
        """
        # 构建节点和边
        nodes = []
        edges = []
        
        # 添加实体节点
        for i, entity in enumerate(result["entities"]):
            nodes.append({
                "id": f"entity_{i}",
                "label": entity.name,
                "type": entity.entity_type,
                "properties": entity.properties or {}
            })
        
        # 添加关系边
        for i, relation in enumerate(result["relations"]):
            edges.append({
                "id": f"relation_{i}",
                "source": relation.subject,
                "target": relation.object,
                "label": relation.predicate,
                "confidence": relation.confidence
            })
        
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": result.get("metadata", {})
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 图谱已导出到: {output_file}")


def test_entity_relation_extractor():
    """测试函数"""
    print("=" * 80)
    print("实体关系提取工作流测试")
    print("=" * 80)
    
    # 检查 API 密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  请设置 OPENAI_API_KEY 环境变量")
        print("示例: export OPENAI_API_KEY='your-api-key'")
        return
    
    try:
        # 初始化提取器
        print("\n初始化提取器...")
        extractor = EntityRelationExtractor(
            model="gpt-4",  # 或 "gpt-3.5-turbo"
            temperature=0.3
        )
        
        # 测试文本
        test_texts = [
            """
张三是一名软件工程师，他在腾讯公司工作。张三精通 Python 和机器学习，
最近他正在开发一个基于深度学习的推荐系统。这个项目由李四领导，
李四是腾讯 AI 实验室的主任。
            """.strip(),
            
            """
《红楼梦》是中国古典四大名著之一，由曹雪芹创作于清朝。
这部小说主要描写了贾宝玉、林黛玉和薛宝钗之间的爱情故事。
贾宝玉是贾府的公子，林黛玉是他的表妹。
            """.strip()
        ]
        
        # 测试1: 单文本处理
        print("\n" + "=" * 80)
        print("测试1: 单文本处理")
        print("=" * 80)
        
        result = extractor.process_text(test_texts[0], use_workflow=True)
        
        print("\n📋 提取结果:")
        print(f"\n实体 ({len(result['entities'])} 个):")
        for entity in result['entities']:
            print(f"  - {entity.name} ({entity.entity_type})")
        
        print(f"\n关系 ({len(result['relations'])} 个):")
        for rel in result['relations']:
            print(f"  - {rel.subject} --[{rel.predicate}]--> {rel.object} (置信度: {rel.confidence})")
        
        print(f"\n三元组 ({len(result['triples'])} 个):")
        for triple in result['triples']:
            print(f"  - ({triple.subject}, {triple.predicate}, {triple.object})")
        
        # 测试2: 批量处理
        print("\n" + "=" * 80)
        print("测试2: 批量处理")
        print("=" * 80)
        
        batch_result = extractor.process_chunks(test_texts, batch_size=2)
        
        print(f"\n📊 批量处理统计:")
        print(f"  总块数: {batch_result['metadata']['total_chunks']}")
        print(f"  实体数: {batch_result['metadata']['entities_count']}")
        print(f"  关系数: {batch_result['metadata']['relations_count']}")
        print(f"  三元组数: {batch_result['metadata']['triples_count']}")
        
        # 测试3: 导出可视化
        print("\n" + "=" * 80)
        print("测试3: 导出图谱")
        print("=" * 80)
        
        extractor.visualize_graph(result, "test_knowledge_graph.json")
        
        # 测试4: Neo4j 格式转换
        print("\n" + "=" * 80)
        print("测试4: Neo4j 格式转换")
        print("=" * 80)
        
        neo4j_data = extractor.to_neo4j_format(result)
        print(f"  转换了 {len(neo4j_data['entities'])} 个实体")
        print(f"  转换了 {len(neo4j_data['triples'])} 个三元组")
        
        print("\n" + "=" * 80)
        print("✅ 测试完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 故障排查:")
        print("1. 检查 OPENAI_API_KEY 是否正确设置")
        print("2. 确保网络连接正常")
        print("3. 检查 API 配额是否充足")
        print("4. 安装依赖: pip install langgraph openai")


if __name__ == "__main__":
    test_entity_relation_extractor()

