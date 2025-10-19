"""
Neo4j 知识图谱工具类
支持三元组插入、查询、更新和删除操作
"""

from neo4j import GraphDatabase
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass
import json
from collections import defaultdict


@dataclass
class Triple:
    """三元组数据结构"""
    subject: str          # 主体
    subject_label: str    # 主体标签/类型
    predicate: str        # 谓语/关系
    object: str           # 客体
    object_label: str     # 客体标签/类型
    properties: Optional[Dict[str, Any]] = None  # 关系属性


@dataclass
class Entity:
    """实体数据结构"""
    name: str                              # 实体名称
    label: str                             # 实体标签/类型
    properties: Optional[Dict[str, Any]] = None  # 实体属性


class Neo4jKnowledgeGraph:
    """
    Neo4j 知识图谱管理类
    
    功能：
    1. 连接 Neo4j 数据库
    2. 插入三元组（节点和关系）
    3. 批量操作
    4. 查询节点和关系
    5. 更新和删除
    6. 图谱遍历和分析
    7. 与 RAG 系统集成
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        初始化 Neo4j 连接
        
        Args:
            uri: Neo4j 连接地址
            username: 用户名
            password: 密码
            database: 数据库名称
        """
        self.uri = uri
        self.username = username
        self.database = database
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            # 测试连接
            self.driver.verify_connectivity()
            print(f"✅ 成功连接到 Neo4j: {uri}")
        except Exception as e:
            raise ConnectionError(f"无法连接到 Neo4j: {str(e)}")
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            print("Neo4j 连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ==================== 三元组插入 ====================
    
    def insert_triple(
        self,
        subject: str,
        subject_label: str,
        predicate: str,
        object_: str,
        object_label: str,
        subject_props: Optional[Dict[str, Any]] = None,
        object_props: Optional[Dict[str, Any]] = None,
        relation_props: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        插入单个三元组
        
        Args:
            subject: 主体名称
            subject_label: 主体类型/标签
            predicate: 关系类型
            object_: 客体名称
            object_label: 客体类型/标签
            subject_props: 主体属性
            object_props: 客体属性
            relation_props: 关系属性
            
        Returns:
            是否插入成功
        """
        subject_props = subject_props or {}
        object_props = object_props or {}
        relation_props = relation_props or {}
        
        # 添加 name 属性
        subject_props['name'] = subject
        object_props['name'] = object_
        
        query = """
        MERGE (s:{subject_label} {name: $subject})
        SET s += $subject_props
        MERGE (o:{object_label} {name: $object})
        SET o += $object_props
        MERGE (s)-[r:{predicate}]->(o)
        SET r += $relation_props
        RETURN s, r, o
        """.format(
            subject_label=subject_label,
            object_label=object_label,
            predicate=predicate
        )
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query,
                    subject=subject,
                    object=object_,
                    subject_props=subject_props,
                    object_props=object_props,
                    relation_props=relation_props
                )
                result.single()
                return True
        except Exception as e:
            print(f"插入三元组失败: {str(e)}")
            return False
    
    def insert_triples(
        self,
        triples: List[Triple]
    ) -> Dict[str, int]:
        """
        批量插入三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            插入统计信息
        """
        success_count = 0
        failed_count = 0
        
        for triple in triples:
            result = self.insert_triple(
                subject=triple.subject,
                subject_label=triple.subject_label,
                predicate=triple.predicate,
                object_=triple.object,
                object_label=triple.object_label,
                relation_props=triple.properties
            )
            
            if result:
                success_count += 1
            else:
                failed_count += 1
        
        return {
            'success': success_count,
            'failed': failed_count,
            'total': len(triples)
        }
    
    def insert_triples_batch(
        self,
        triples: List[Tuple[str, str, str, str, str]],
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        高效批量插入三元组（使用 UNWIND）
        
        Args:
            triples: 三元组列表 [(subject, subject_label, predicate, object, object_label), ...]
            batch_size: 批次大小
            
        Returns:
            插入统计信息
        """
        total = len(triples)
        success_count = 0
        
        query = """
        UNWIND $triples AS triple
        MERGE (s {name: triple.subject})
        SET s :Entity
        SET s += {label: triple.subject_label}
        MERGE (o {name: triple.object})
        SET o :Entity
        SET o += {label: triple.object_label}
        MERGE (s)-[r:RELATES]->(o)
        SET r += {type: triple.predicate}
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                for i in range(0, total, batch_size):
                    batch = triples[i:i + batch_size]
                    batch_data = [
                        {
                            'subject': t[0],
                            'subject_label': t[1],
                            'predicate': t[2],
                            'object': t[3],
                            'object_label': t[4]
                        }
                        for t in batch
                    ]
                    
                    session.run(query, triples=batch_data)
                    success_count += len(batch)
                    
                    if i % (batch_size * 10) == 0:
                        print(f"已处理: {i}/{total}")
            
            print(f"批量插入完成: {success_count}/{total}")
            return {'success': success_count, 'failed': total - success_count, 'total': total}
            
        except Exception as e:
            print(f"批量插入失败: {str(e)}")
            return {'success': success_count, 'failed': total - success_count, 'total': total}
    
    # ==================== 实体操作 ====================
    
    def insert_entity(
        self,
        name: str,
        label: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        插入实体节点
        
        Args:
            name: 实体名称
            label: 实体标签
            properties: 实体属性
            
        Returns:
            是否插入成功
        """
        properties = properties or {}
        properties['name'] = name
        
        query = """
        MERGE (e:{label} {name: $name})
        SET e += $properties
        RETURN e
        """.format(label=label)
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, name=name, properties=properties)
                return True
        except Exception as e:
            print(f"插入实体失败: {str(e)}")
            return False
    
    def insert_entities(
        self,
        entities: List[Entity]
    ) -> Dict[str, int]:
        """
        批量插入实体
        
        Args:
            entities: 实体列表
            
        Returns:
            插入统计信息
        """
        success_count = 0
        
        for entity in entities:
            if self.insert_entity(entity.name, entity.label, entity.properties):
                success_count += 1
        
        return {
            'success': success_count,
            'failed': len(entities) - success_count,
            'total': len(entities)
        }
    
    # ==================== 查询操作 ====================
    
    def find_entity(
        self,
        name: str,
        label: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查找实体
        
        Args:
            name: 实体名称
            label: 实体标签（可选）
            
        Returns:
            实体信息
        """
        if label:
            query = f"MATCH (e:{label} {{name: $name}}) RETURN e"
        else:
            query = "MATCH (e {name: $name}) RETURN e"
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, name=name)
                record = result.single()
                
                if record:
                    node = record['e']
                    return {
                        'name': node.get('name'),
                        'labels': list(node.labels),
                        'properties': dict(node)
                    }
                return None
        except Exception as e:
            print(f"查询实体失败: {str(e)}")
            return None
    
    def find_relations(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查找关系
        
        Args:
            subject: 主体名称（可选）
            predicate: 关系类型（可选）
            object_: 客体名称（可选）
            limit: 返回数量限制
            
        Returns:
            关系列表
        """
        conditions = []
        params = {}
        
        if subject:
            conditions.append("s.name = $subject")
            params['subject'] = subject
        if object_:
            conditions.append("o.name = $object")
            params['object'] = object_
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rel_type = f":{predicate}" if predicate else ""
        
        query = f"""
        MATCH (s)-[r{rel_type}]->(o)
        {where_clause}
        RETURN s, r, o
        LIMIT {limit}
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, **params)
                
                relations = []
                for record in result:
                    relations.append({
                        'subject': dict(record['s']),
                        'relation': {
                            'type': type(record['r']).__name__,
                            'properties': dict(record['r'])
                        },
                        'object': dict(record['o'])
                    })
                
                return relations
        except Exception as e:
            print(f"查询关系失败: {str(e)}")
            return []
    
    def get_neighbors(
        self,
        entity_name: str,
        direction: str = "both",
        max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        获取实体的邻居节点
        
        Args:
            entity_name: 实体名称
            direction: 方向 ("in", "out", "both")
            max_depth: 最大深度
            
        Returns:
            邻居节点列表
        """
        if direction == "out":
            pattern = "(e)-[r*1..{depth}]->(n)".format(depth=max_depth)
        elif direction == "in":
            pattern = "(e)<-[r*1..{depth}]-(n)".format(depth=max_depth)
        else:
            pattern = "(e)-[r*1..{depth}]-(n)".format(depth=max_depth)
        
        query = f"""
        MATCH {pattern}
        WHERE e.name = $name
        RETURN DISTINCT n
        LIMIT 100
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, name=entity_name)
                
                neighbors = []
                for record in result:
                    node = record['n']
                    neighbors.append({
                        'name': node.get('name'),
                        'labels': list(node.labels),
                        'properties': dict(node)
                    })
                
                return neighbors
        except Exception as e:
            print(f"查询邻居失败: {str(e)}")
            return []
    
    def get_path(
        self,
        start_entity: str,
        end_entity: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        查找两个实体之间的路径
        
        Args:
            start_entity: 起始实体
            end_entity: 结束实体
            max_depth: 最大路径长度
            
        Returns:
            路径列表
        """
        query = """
        MATCH path = shortestPath(
            (start {name: $start})-[*1..{depth}]-(end {name: $end})
        )
        RETURN path
        LIMIT 10
        """.format(depth=max_depth)
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, start=start_entity, end=end_entity)
                
                paths = []
                for record in result:
                    path = record['path']
                    path_nodes = [node.get('name') for node in path.nodes]
                    paths.append(path_nodes)
                
                return paths
        except Exception as e:
            print(f"查询路径失败: {str(e)}")
            return []
    
    # ==================== 更新操作 ====================
    
    def update_entity(
        self,
        name: str,
        properties: Dict[str, Any],
        label: Optional[str] = None
    ) -> bool:
        """
        更新实体属性
        
        Args:
            name: 实体名称
            properties: 新属性
            label: 实体标签（可选）
            
        Returns:
            是否更新成功
        """
        if label:
            query = f"MATCH (e:{label} {{name: $name}}) SET e += $properties RETURN e"
        else:
            query = "MATCH (e {name: $name}) SET e += $properties RETURN e"
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, name=name, properties=properties)
                return result.single() is not None
        except Exception as e:
            print(f"更新实体失败: {str(e)}")
            return False
    
    # ==================== 删除操作 ====================
    
    def delete_entity(
        self,
        name: str,
        label: Optional[str] = None,
        delete_relations: bool = True
    ) -> bool:
        """
        删除实体
        
        Args:
            name: 实体名称
            label: 实体标签（可选）
            delete_relations: 是否同时删除相关关系
            
        Returns:
            是否删除成功
        """
        if label:
            match_clause = f"(e:{label} {{name: $name}})"
        else:
            match_clause = "(e {name: $name})"
        
        if delete_relations:
            query = f"MATCH {match_clause} DETACH DELETE e"
        else:
            query = f"MATCH {match_clause} DELETE e"
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, name=name)
                return True
        except Exception as e:
            print(f"删除实体失败: {str(e)}")
            return False
    
    def delete_relation(
        self,
        subject: str,
        predicate: str,
        object_: str
    ) -> bool:
        """
        删除关系
        
        Args:
            subject: 主体名称
            predicate: 关系类型
            object_: 客体名称
            
        Returns:
            是否删除成功
        """
        query = f"""
        MATCH (s {{name: $subject}})-[r:{predicate}]->(o {{name: $object}})
        DELETE r
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, subject=subject, object=object_)
                return True
        except Exception as e:
            print(f"删除关系失败: {str(e)}")
            return False
    
    def clear_graph(self) -> bool:
        """清空整个图谱（危险操作！）"""
        query = "MATCH (n) DETACH DELETE n"
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query)
                print("⚠️  图谱已清空")
                return True
        except Exception as e:
            print(f"清空图谱失败: {str(e)}")
            return False
    
    # ==================== 统计和分析 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        Returns:
            统计信息
        """
        queries = {
            'node_count': "MATCH (n) RETURN count(n) as count",
            'relation_count': "MATCH ()-[r]->() RETURN count(r) as count",
            'label_distribution': "MATCH (n) RETURN labels(n) as labels, count(*) as count",
            'relation_types': "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count"
        }
        
        stats = {}
        
        try:
            with self.driver.session(database=self.database) as session:
                # 节点数量
                result = session.run(queries['node_count'])
                stats['total_nodes'] = result.single()['count']
                
                # 关系数量
                result = session.run(queries['relation_count'])
                stats['total_relations'] = result.single()['count']
                
                # 标签分布
                result = session.run(queries['label_distribution'])
                label_dist = {}
                for record in result:
                    labels = tuple(record['labels'])
                    label_dist[str(labels)] = record['count']
                stats['label_distribution'] = label_dist
                
                # 关系类型
                result = session.run(queries['relation_types'])
                relation_types = {}
                for record in result:
                    relation_types[record['type']] = record['count']
                stats['relation_types'] = relation_types
                
                return stats
        except Exception as e:
            print(f"获取统计信息失败: {str(e)}")
            return {}
    
    # ==================== 高级查询 ====================
    
    def cypher_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行自定义 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
            
        Returns:
            查询结果
        """
        parameters = parameters or {}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, **parameters)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Cypher 查询失败: {str(e)}")
            return []
    
    def subgraph(
        self,
        entity_name: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        提取以某实体为中心的子图
        
        Args:
            entity_name: 实体名称
            depth: 深度
            
        Returns:
            子图信息（节点和边）
        """
        query = f"""
        MATCH path = (center {{name: $name}})-[*1..{depth}]-(n)
        WITH center, collect(DISTINCT n) as nodes, collect(DISTINCT relationships(path)) as rels
        RETURN center, nodes, rels
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, name=entity_name)
                record = result.single()
                
                if not record:
                    return {'nodes': [], 'edges': []}
                
                # 提取节点
                nodes = []
                center = record['center']
                nodes.append({
                    'id': center.element_id,
                    'name': center.get('name'),
                    'labels': list(center.labels),
                    'properties': dict(center)
                })
                
                for node in record['nodes']:
                    nodes.append({
                        'id': node.element_id,
                        'name': node.get('name'),
                        'labels': list(node.labels),
                        'properties': dict(node)
                    })
                
                # 提取边
                edges = []
                for rel_list in record['rels']:
                    for rel in rel_list:
                        edges.append({
                            'id': rel.element_id,
                            'type': type(rel).__name__,
                            'start': rel.start_node.element_id,
                            'end': rel.end_node.element_id,
                            'properties': dict(rel)
                        })
                
                return {
                    'nodes': nodes,
                    'edges': edges
                }
        except Exception as e:
            print(f"提取子图失败: {str(e)}")
            return {'nodes': [], 'edges': []}


def test_neo4j_kg():
    """测试函数"""
    print("=" * 80)
    print("Neo4j 知识图谱测试")
    print("=" * 80)
    
    try:
        # 连接数据库
        print("\n【测试1: 连接数据库】")
        print("-" * 80)
        kg = Neo4jKnowledgeGraph(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password"
        )
        
        # 清空测试数据（可选）
        # kg.clear_graph()
        
        # 插入实体
        print("\n【测试2: 插入实体】")
        print("-" * 80)
        entities = [
            Entity("张三", "Person", {"age": 30, "occupation": "工程师"}),
            Entity("李四", "Person", {"age": 28, "occupation": "设计师"}),
            Entity("Python", "Language", {"type": "编程语言", "year": 1991}),
            Entity("Java", "Language", {"type": "编程语言", "year": 1995}),
            Entity("机器学习", "Technology", {"field": "人工智能"}),
        ]
        result = kg.insert_entities(entities)
        print(f"插入实体: 成功 {result['success']}, 失败 {result['failed']}")
        
        # 插入三元组
        print("\n【测试3: 插入三元组】")
        print("-" * 80)
        triples = [
            Triple("张三", "Person", "KNOWS", "李四", "Person"),
            Triple("张三", "Person", "USES", "Python", "Language"),
            Triple("李四", "Person", "USES", "Java", "Language"),
            Triple("张三", "Person", "STUDIES", "机器学习", "Technology"),
            Triple("Python", "Language", "SUPPORTS", "机器学习", "Technology"),
        ]
        result = kg.insert_triples(triples)
        print(f"插入三元组: 成功 {result['success']}, 失败 {result['failed']}")
        
        # 查询实体
        print("\n【测试4: 查询实体】")
        print("-" * 80)
        entity = kg.find_entity("张三", "Person")
        if entity:
            print(f"实体: {entity['name']}")
            print(f"标签: {entity['labels']}")
            print(f"属性: {entity['properties']}")
        
        # 查询关系
        print("\n【测试5: 查询关系】")
        print("-" * 80)
        relations = kg.find_relations(subject="张三", limit=10)
        print(f"找到 {len(relations)} 个关系:")
        for rel in relations:
            print(f"  {rel['subject']['name']} -> {rel['relation']['type']} -> {rel['object']['name']}")
        
        # 查询邻居
        print("\n【测试6: 查询邻居节点】")
        print("-" * 80)
        neighbors = kg.get_neighbors("张三", direction="out")
        print(f"张三的邻居节点 ({len(neighbors)} 个):")
        for neighbor in neighbors:
            print(f"  - {neighbor['name']} ({neighbor['labels']})")
        
        # 查询路径
        print("\n【测试7: 查询路径】")
        print("-" * 80)
        paths = kg.get_path("张三", "机器学习", max_depth=3)
        print(f"从 '张三' 到 '机器学习' 的路径:")
        for i, path in enumerate(paths, 1):
            print(f"  路径{i}: {' -> '.join(path)}")
        
        # 提取子图
        print("\n【测试8: 提取子图】")
        print("-" * 80)
        subgraph = kg.subgraph("张三", depth=2)
        print(f"子图包含:")
        print(f"  节点数: {len(subgraph['nodes'])}")
        print(f"  边数: {len(subgraph['edges'])}")
        
        # 统计信息
        print("\n【测试9: 图谱统计】")
        print("-" * 80)
        stats = kg.get_stats()
        print(f"总节点数: {stats.get('total_nodes', 0)}")
        print(f"总关系数: {stats.get('total_relations', 0)}")
        print(f"标签分布: {stats.get('label_distribution', {})}")
        print(f"关系类型: {stats.get('relation_types', {})}")
        
        # Cypher 查询
        print("\n【测试10: 自定义 Cypher 查询】")
        print("-" * 80)
        query = """
        MATCH (p:Person)-[r]->(t)
        RETURN p.name as person, type(r) as relation, t.name as target
        LIMIT 5
        """
        results = kg.cypher_query(query)
        print("查询结果:")
        for record in results:
            print(f"  {record}")
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        
        # 关闭连接
        kg.close()
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("\n提示:")
        print("1. 确保 Neo4j 正在运行")
        print("2. 检查连接配置（URI、用户名、密码）")
        print("3. 安装依赖: pip install neo4j")


if __name__ == "__main__":
    test_neo4j_kg()

