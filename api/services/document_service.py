"""
文档处理服务 - 支持异步处理
包括文档分块、向量化、实体关系抽取等功能
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import os
import json

from database.models import Document, DocumentChunk, KnowledgeBase, DocumentStatusEnum, ChunkStrategyEnum
from database.database import SessionLocal
from utils.chunk import TextChunker
from utils.faiss import FaissVectorStore
from api.schemas import DocumentCreate

# 导入 NER 和 Neo4j
try:
    from utils.chunk_to_ner import EntityRelationExtractor
    NER_AVAILABLE = True
except Exception as e:
    NER_AVAILABLE = False
    print(f"⚠️  NER 功能不可用: {e}")

try:
    from utils.neo4j import Neo4jKnowledgeGraph
    NEO4J_AVAILABLE = True
except Exception as e:
    NEO4J_AVAILABLE = False
    print(f"⚠️  Neo4j 功能不可用: {e}")


class DocumentProcessingService:
    """文档处理服务 - 支持异步后台处理"""
    
    def __init__(self, max_workers: int = 4):
        """
        初始化文档处理服务
        
        Args:
            max_workers: 线程池最大工作线程数
        """
        self.vector_stores = {}  # 缓存向量存储实例 {kb_id: FaissVectorStore}
        self.ner_extractors = {}  # 缓存 NER 提取器 {kb_id: EntityRelationExtractor}
        self.neo4j_clients = {}   # 缓存 Neo4j 客户端 {kb_id: Neo4jKnowledgeGraph}
        
        # 线程池用于异步处理
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="doc_processor")
        self.processing_lock = threading.Lock()
        self.processing_tasks = {}  # {document_id: Future}
        
        print(f"✅ 文档处理服务已初始化 (最大工作线程: {max_workers})")
    
    def __del__(self):
        """清理资源"""
        try:
            self.executor.shutdown(wait=False)
        except:
            pass
    
    # ==================== 资源获取 ====================
    
    def get_vector_store(self, kb: KnowledgeBase) -> Optional[FaissVectorStore]:
        """获取或创建向量存储实例"""
        if not kb.enable_vector_store:
            return None
        
        if kb.id not in self.vector_stores:
            try:
                self.vector_stores[kb.id] = FaissVectorStore(
                    embedding_model=kb.embedding_model,
                    index_type="Flat",
                    metric="Cosine"
                )
                print(f"✅ 为知识库 {kb.id} 创建向量存储")
            except Exception as e:
                print(f"❌ 创建向量存储失败: {e}")
                return None
        
        return self.vector_stores[kb.id]
    
    def get_ner_extractor(self, kb: KnowledgeBase) -> Optional[EntityRelationExtractor]:
        """获取或创建 NER 提取器"""
        if not kb.enable_ner or not NER_AVAILABLE:
            return None
        
        if kb.id not in self.ner_extractors:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                base_url = os.getenv("OPENAI_BASE_URL")
                
                if not api_key:
                    print("⚠️  未设置 OPENAI_API_KEY，NER 功能不可用")
                    return None
                
                self.ner_extractors[kb.id] = EntityRelationExtractor(
                    api_key=api_key,
                    base_url=base_url,
                    model=os.getenv("OPENAI_MODEL", "gpt-4"),
                    temperature=0.3
                )
                print(f"✅ 为知识库 {kb.id} 创建 NER 提取器")
            except Exception as e:
                print(f"❌ 创建 NER 提取器失败: {e}")
                return None
        
        return self.ner_extractors[kb.id]
    
    def get_neo4j_client(self, kb: KnowledgeBase) -> Optional[Neo4jKnowledgeGraph]:
        """获取或创建 Neo4j 客户端"""
        if not kb.enable_knowledge_graph or not NEO4J_AVAILABLE:
            return None
        
        if kb.id not in self.neo4j_clients:
            try:
                uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                username = os.getenv("NEO4J_USERNAME", "neo4j")
                password = os.getenv("NEO4J_PASSWORD", "password")
                
                self.neo4j_clients[kb.id] = Neo4jKnowledgeGraph(
                    uri=uri,
                    username=username,
                    password=password
                )
                print(f"✅ 为知识库 {kb.id} 创建 Neo4j 客户端")
            except Exception as e:
                print(f"❌ 创建 Neo4j 客户端失败: {e}")
                return None
        
        return self.neo4j_clients[kb.id]
    
    # ==================== 异步处理接口 ====================
    
    def process_document_async(self, document_id: int, kb_id: int):
        """
        异步处理文档（提交到线程池）
        
        Args:
            document_id: 文档ID
            kb_id: 知识库ID
        """
        with self.processing_lock:
            # 检查是否已经在处理中
            if document_id in self.processing_tasks:
                existing_task = self.processing_tasks[document_id]
                if not existing_task.done():
                    print(f"⚠️  文档 {document_id} 已在处理队列中")
                    return
            
            # 提交新任务
            future = self.executor.submit(
                self._process_document_worker,
                document_id,
                kb_id
            )
            self.processing_tasks[document_id] = future
            print(f"📋 文档 {document_id} 已提交到处理队列")
    
    def _process_document_worker(self, document_id: int, kb_id: int):
        """
        后台工作线程 - 处理文档
        
        这个方法在独立线程中运行，不会阻塞主线程
        """
        # 创建新的数据库 session
        db = SessionLocal()
        
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始处理文档 {document_id}")
            print(f"{'='*60}")
            
            start_time = time.time()
            
            # 获取文档和知识库
            document = db.query(Document).filter(Document.id == document_id).first()
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            
            if not document or not kb:
                print(f"❌ 文档 {document_id} 或知识库 {kb_id} 不存在")
                return
            
            # 更新状态为处理中
            document.status = DocumentStatusEnum.PROCESSING
            db.commit()
            
            # 1. 文档分块
            print(f"\n[步骤 1/4] 文档分块...")
            chunks = self._chunk_document_step(db, document, kb)
            
            if not chunks:
                raise ValueError("文档分块失败，没有生成任何分块")
            
            print(f"✅ 生成 {len(chunks)} 个分块")
            
            # 2. 向量化
            if kb.enable_vector_store:
                print(f"\n[步骤 2/4] 向量化...")
                self._vectorize_chunks_step(db, chunks, kb)
                print(f"✅ 向量化完成")
                document.vector_stored = True
            else:
                print(f"\n[步骤 2/4] 跳过向量化（未启用）")
            
            # 3. 实体关系提取
            if kb.enable_ner:
                print(f"\n[步骤 3/4] 实体关系提取...")
                entity_count, relation_count = self._extract_entities_relations_step(
                    db, document, chunks, kb
                )
                print(f"✅ 提取了 {entity_count} 个实体，{relation_count} 个关系")
                document.entity_count = entity_count
                document.relation_count = relation_count
            else:
                print(f"\n[步骤 3/4] 跳过实体关系提取（未启用）")
            
            # 4. 知识图谱存储
            if kb.enable_knowledge_graph and kb.enable_ner:
                print(f"\n[步骤 4/4] 知识图谱存储...")
                self._store_to_knowledge_graph_step(db, chunks, kb)
                print(f"✅ 知识图谱存储完成")
                document.graph_stored = True
            else:
                print(f"\n[步骤 4/4] 跳过知识图谱存储（未启用）")
            
            # 更新文档统计
            document.chunk_count = len(chunks)
            document.char_count = len(document.content)
            document.word_count = len(document.content.split())
            document.status = DocumentStatusEnum.COMPLETED
            document.processing_time = time.time() - start_time
            document.processed_at = datetime.utcnow()
            
            # 更新知识库统计
            kb.document_count += 1
            kb.total_chunks += len(chunks)
            
            db.commit()
            
            print(f"\n{'='*60}")
            print(f"✅ 文档 {document_id} 处理完成")
            print(f"   耗时: {document.processing_time:.2f}秒")
            print(f"   分块数: {len(chunks)}")
            print(f"   向量化: {'是' if document.vector_stored else '否'}")
            print(f"   知识图谱: {'是' if document.graph_stored else '否'}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ 处理文档 {document_id} 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 更新错误状态
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = DocumentStatusEnum.FAILED
                    document.error_message = str(e)
                    db.commit()
            except:
                pass
        
        finally:
            db.close()
            
            # 清理任务记录
            with self.processing_lock:
                if document_id in self.processing_tasks:
                    del self.processing_tasks[document_id]
    
    # ==================== 处理步骤 ====================
    
    def _chunk_document_step(
        self,
        db: Session,
        document: Document,
        kb: KnowledgeBase
    ) -> List[DocumentChunk]:
        """文档分块步骤"""
        # 确定分块配置
        chunk_strategy = document.chunk_strategy or kb.default_chunk_strategy
        chunk_size = document.chunk_size or kb.default_chunk_size
        chunk_overlap = document.chunk_overlap or kb.default_chunk_overlap
        
        # 执行分块
        chunks_text = self._chunk_text(
            document.content,
            chunk_strategy,
            chunk_size,
            chunk_overlap
        )
        
        # 创建分块记录
        chunks = []
        for i, text in enumerate(chunks_text):
            chunk = DocumentChunk(
                document_id=document.id,
                content=text,
                chunk_index=i,
                chunk_type=chunk_strategy.value if hasattr(chunk_strategy, 'value') else str(chunk_strategy),
                char_count=len(text),
                word_count=len(text.split()),
                start_pos=document.content.find(text[:50]) if len(text) >= 50 else 0
            )
            chunk.end_pos = chunk.start_pos + len(text)
            chunks.append(chunk)
            db.add(chunk)
        
        db.commit()
        
        # 刷新对象以获取 ID
        for chunk in chunks:
            db.refresh(chunk)
        
        return chunks
    
    def _chunk_text(
        self,
        content: str,
        strategy: ChunkStrategyEnum,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """执行文本分块"""
        chunker = TextChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if strategy == ChunkStrategyEnum.SEMANTIC:
            return chunker.semantic_chunking(content, language='zh')
        elif strategy == ChunkStrategyEnum.FIXED:
            return chunker.fixed_size_chunking(content)
        elif strategy == ChunkStrategyEnum.RECURSIVE:
            return chunker.recursive_chunking(content)
        elif strategy == ChunkStrategyEnum.PARAGRAPH:
            return chunker.paragraph_chunking(content)
        else:
            return chunker.semantic_chunking(content, language='zh')
    
    def _vectorize_chunks_step(
        self,
        db: Session,
        chunks: List[DocumentChunk],
        kb: KnowledgeBase
    ):
        """向量化分块步骤"""
        vector_store = self.get_vector_store(kb)
        if not vector_store:
            return
        
        try:
            texts = [chunk.content for chunk in chunks]
            metadatas = [
                {
                    'chunk_id': chunk.id,
                    'document_id': chunk.document_id,
                    'chunk_index': chunk.chunk_index
                }
                for chunk in chunks
            ]
            doc_ids = [f"chunk_{chunk.id}" for chunk in chunks]
            
            # 添加到向量存储
            added_ids = vector_store.add_texts(texts, metadatas, doc_ids)
            
            # 更新分块记录
            for chunk, vector_id in zip(chunks, added_ids):
                chunk.vector_id = vector_id
                chunk.has_embedding = True
                chunk.embedding_model = vector_store.embedding.model
            
            db.commit()
            
        except Exception as e:
            print(f"⚠️  向量化失败: {e}")
            # 不抛出异常，允许继续处理
    
    def _extract_entities_relations_step(
        self,
        db: Session,
        document: Document,
        chunks: List[DocumentChunk],
        kb: KnowledgeBase
    ) -> Tuple[int, int]:
        """实体关系提取步骤"""
        ner_extractor = self.get_ner_extractor(kb)
        if not ner_extractor:
            return 0, 0
        
        try:
            # 对每个分块进行实体关系提取
            total_entities = set()
            total_relations = []
            
            for chunk in chunks:
                try:
                    # 提取实体和关系（传入 chunk_id）
                    result = ner_extractor.process_text(
                        chunk.content,
                        chunk_id=str(chunk.id),  # 传入 chunk_id
                        use_workflow=False  # 使用直接模式，更快
                    )
                    
                    # 更新分块的实体和关系（存储详细信息）
                    entities = [e.name for e in result.get('entities', [])]
                    relations = [
                        {
                            'subject': r.subject,
                            'subject_type': r.subject_type,
                            'predicate': r.predicate,
                            'object': r.object,
                            'object_type': r.object_type,
                            'confidence': r.confidence,
                            'chunk_ids': r.chunk_ids,
                            'contexts': r.contexts
                        }
                        for r in result.get('relations', [])
                    ]
                    
                    chunk.entities = entities
                    chunk.relations = relations
                    
                    # 累计统计
                    total_entities.update(entities)
                    total_relations.extend(relations)
                    
                except Exception as e:
                    print(f"⚠️  分块 {chunk.id} NER 失败: {e}")
                    continue
            
            db.commit()
            
            return len(total_entities), len(total_relations)
            
        except Exception as e:
            print(f"⚠️  实体关系提取失败: {e}")
            return 0, 0
    
    def _store_to_knowledge_graph_step(
        self,
        db: Session,
        chunks: List[DocumentChunk],
        kb: KnowledgeBase
    ):
        """知识图谱存储步骤"""
        neo4j_client = self.get_neo4j_client(kb)
        if not neo4j_client:
            return
        
        try:
            # 收集所有三元组
            all_triples = []
            
            for chunk in chunks:
                relations = chunk.relations or []
                for rel in relations:
                    # 确保关系有必要的字段
                    subject = rel.get('subject', '')
                    subject_type = rel.get('subject_type', 'Concept')
                    predicate = rel.get('predicate', 'RELATES_TO')
                    object_ = rel.get('object', '')
                    object_type = rel.get('object_type', 'Concept')
                    
                    # 构建三元组（确保主体和客体都存在）
                    if subject and object_:
                        triple = (subject, subject_type, predicate, object_, object_type)
                        all_triples.append(triple)
            
            if all_triples:
                # 批量插入到 Neo4j
                result = neo4j_client.insert_triples_batch(
                    all_triples,
                    batch_size=100
                )
                print(f"   插入三元组: 成功 {result['success']}, 失败 {result['failed']}")
            
        except Exception as e:
            print(f"⚠️  知识图谱存储失败: {e}")
    
    # ==================== 搜索功能 ====================
    
    def search_documents(
        self,
        db: Session,
        kb_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[DocumentChunk, float]]:
        """搜索文档"""
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return []
        
        vector_store = self.get_vector_store(kb)
        if not vector_store:
            return []
        
        try:
            results = vector_store.search(query, top_k=top_k)
            
            # 转换结果
            search_results = []
            for doc_metadata, score in results:
                chunk_id = doc_metadata.metadata.get('chunk_id')
                if chunk_id:
                    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
                    if chunk:
                        search_results.append((chunk, score))
            
            return search_results
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []
    
    def get_processing_status(self, document_id: int) -> Dict[str, Any]:
        """获取文档处理状态"""
        with self.processing_lock:
            if document_id in self.processing_tasks:
                task = self.processing_tasks[document_id]
                return {
                    'in_queue': True,
                    'done': task.done(),
                    'running': task.running()
                }
            return {
                'in_queue': False,
                'done': None,
                'running': False
            }
    
    def search_graph(
        self,
        db: Session,
        kb_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        图谱搜索：基于实体和关系进行搜索
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            query: 搜索查询
            top_k: 返回结果数量
            
        Returns:
            图谱搜索结果列表
        """
        try:
            from database.models import DocumentChunk
            
            # 1. 在所有 chunk 的 entities 中搜索匹配的实体
            chunks = db.query(DocumentChunk).join(
                Document
            ).filter(
                Document.knowledge_base_id == kb_id
            ).all()
            # 2. 找出包含查询关键词的实体和关系
            entity_matches = {}  # {entity_name: {chunks: [], relations: []}}
            
            for chunk in chunks:
                entities = chunk.entities or []
                relations = chunk.relations or []
                # 检查实体是否匹配
                for entity_name in entities:
                    if query.lower() in entity_name.lower() or entity_name.lower() in query.lower():
                        if entity_name not in entity_matches:
                            entity_matches[entity_name] = {
                                'chunks': [],
                                'relations': [],
                                'entity_type': 'Concept'  # 默认类型
                            }
                        
                        entity_matches[entity_name]['chunks'].append({
                            'chunk_id': chunk.id,
                            'document_id': chunk.document_id,
                            'content': chunk.content,
                            'chunk_index': chunk.chunk_index
                        })
                
                # 检查关系是否匹配
                for relation in relations:
                    subject = relation.get('subject', '')
                    predicate = relation.get('predicate', '')
                    object_ = relation.get('object', '')
                    
                    # 如果查询词出现在关系的任何部分
                    if (query.lower() in subject.lower() or 
                        query.lower() in object_.lower() or
                        query.lower() in predicate.lower()):
                        
                        # 记录相关实体
                        for entity_name in [subject, object_]:
                            if entity_name not in entity_matches:
                                entity_matches[entity_name] = {
                                    'chunks': [],
                                    'relations': [],
                                    'entity_type': relation.get('subject_type', 'Concept') if entity_name == subject else relation.get('object_type', 'Concept')
                                }
                            
                            entity_matches[entity_name]['relations'].append({
                                'subject': subject,
                                'subject_type': relation.get('subject_type', 'Concept'),
                                'predicate': predicate,
                                'object': object_,
                                'object_type': relation.get('object_type', 'Concept'),
                                'confidence': relation.get('confidence', 0.8),
                                'chunk_id': chunk.id
                            })
                            
                            if chunk.id not in [c['chunk_id'] for c in entity_matches[entity_name]['chunks']]:
                                entity_matches[entity_name]['chunks'].append({
                                    'chunk_id': chunk.id,
                                    'document_id': chunk.document_id,
                                    'content': chunk.content,
                                    'chunk_index': chunk.chunk_index
                                })
            
            # 3. 构建图谱搜索结果
            graph_results = []
            for entity_name, data in entity_matches.items():
                # 计算相关性得分
                relevance_score = 0.0
                
                # 名称匹配度
                if query.lower() == entity_name.lower():
                    relevance_score += 1.0
                elif query.lower() in entity_name.lower():
                    relevance_score += 0.7
                
                # 关系数量加权
                relevance_score += min(len(data['relations']) * 0.1, 0.5)
                
                # 出现频率加权
                relevance_score += min(len(data['chunks']) * 0.05, 0.3)
                
                # 提取相关实体
                related_entities = []
                seen_entities = set()
                
                for rel in data['relations']:
                    # 添加关系中的另一个实体
                    if rel['subject'] == entity_name and rel['object'] not in seen_entities:
                        related_entities.append({
                            'name': rel['object'],
                            'type': rel['object_type'],
                            'relation': rel['predicate']
                        })
                        seen_entities.add(rel['object'])
                    elif rel['object'] == entity_name and rel['subject'] not in seen_entities:
                        related_entities.append({
                            'name': rel['subject'],
                            'type': rel['subject_type'],
                            'relation': rel['predicate']
                        })
                        seen_entities.add(rel['subject'])
                
                graph_results.append({
                    'entity_name': entity_name,
                    'entity_type': data['entity_type'],
                    'related_entities': related_entities[:5],  # 最多5个相关实体
                    'relations': data['relations'][:10],  # 最多10个关系
                    'chunk_ids': [str(c['chunk_id']) for c in data['chunks']],
                    'chunks': data['chunks'],
                    'relevance_score': min(relevance_score, 1.0)
                })
            
            # 4. 按相关性排序并返回 top_k
            graph_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return graph_results[:top_k]
            
        except Exception as e:
            print(f"❌ 图谱搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []


# 全局服务实例
document_service = DocumentProcessingService(max_workers=4)
