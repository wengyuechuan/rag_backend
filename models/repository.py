"""
数据仓库模块
提供文档和分块的存储和查询功能
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime
import json
from pathlib import Path

from .document import Document, DocumentStatus, DocumentType
from .chunk import Chunk, ChunkType, ChunkRelation


class DocumentRepository:
    """
    文档仓库
    管理文档的存储和检索
    """
    
    def __init__(self):
        """初始化文档仓库"""
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, Chunk] = {}
        self.chunk_relations: List[ChunkRelation] = []
        
        # 索引
        self.doc_by_source: Dict[str, List[str]] = {}
        self.doc_by_category: Dict[str, List[str]] = {}
        self.doc_by_status: Dict[DocumentStatus, List[str]] = {}
        self.chunks_by_doc: Dict[str, List[str]] = {}
    
    # ==================== 文档操作 ====================
    
    def add_document(self, document: Document) -> str:
        """
        添加文档
        
        Args:
            document: 文档对象
            
        Returns:
            文档 ID
        """
        self.documents[document.id] = document
        
        # 更新索引
        self._update_document_indices(document)
        
        return document.id
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        获取文档
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            文档对象
        """
        return self.documents.get(doc_id)
    
    def update_document(self, document: Document):
        """
        更新文档
        
        Args:
            document: 文档对象
        """
        if document.id in self.documents:
            # 先移除旧索引
            old_doc = self.documents[document.id]
            self._remove_document_indices(old_doc)
            
            # 更新文档
            document.updated_at = datetime.now()
            self.documents[document.id] = document
            
            # 重建索引
            self._update_document_indices(document)
    
    def delete_document(self, doc_id: str, delete_chunks: bool = True) -> bool:
        """
        删除文档
        
        Args:
            doc_id: 文档 ID
            delete_chunks: 是否同时删除关联的分块
            
        Returns:
            是否删除成功
        """
        if doc_id not in self.documents:
            return False
        
        document = self.documents[doc_id]
        
        # 删除关联的分块
        if delete_chunks:
            for chunk_id in document.chunk_ids.copy():
                self.delete_chunk(chunk_id)
        
        # 移除索引
        self._remove_document_indices(document)
        
        # 删除文档
        del self.documents[doc_id]
        
        return True
    
    def find_documents(
        self,
        status: Optional[DocumentStatus] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        filter_func: Optional[Callable[[Document], bool]] = None
    ) -> List[Document]:
        """
        查找文档
        
        Args:
            status: 状态过滤
            category: 分类过滤
            source: 来源过滤
            tags: 标签过滤
            filter_func: 自定义过滤函数
            
        Returns:
            文档列表
        """
        # 先根据索引快速过滤
        if status is not None:
            doc_ids = set(self.doc_by_status.get(status, []))
        elif category is not None:
            doc_ids = set(self.doc_by_category.get(category, []))
        elif source is not None:
            doc_ids = set(self.doc_by_source.get(source, []))
        else:
            doc_ids = set(self.documents.keys())
        
        # 应用其他过滤条件
        results = []
        for doc_id in doc_ids:
            doc = self.documents[doc_id]
            
            # 标签过滤
            if tags and not any(tag in doc.tags for tag in tags):
                continue
            
            # 自定义过滤
            if filter_func and not filter_func(doc):
                continue
            
            results.append(doc)
        
        return results
    
    # ==================== 分块操作 ====================
    
    def add_chunk(self, chunk: Chunk) -> str:
        """
        添加分块
        
        Args:
            chunk: 分块对象
            
        Returns:
            分块 ID
        """
        self.chunks[chunk.id] = chunk
        
        # 更新索引
        if chunk.document_id:
            if chunk.document_id not in self.chunks_by_doc:
                self.chunks_by_doc[chunk.document_id] = []
            self.chunks_by_doc[chunk.document_id].append(chunk.id)
            
            # 更新文档的分块列表
            if chunk.document_id in self.documents:
                self.documents[chunk.document_id].add_chunk(chunk.id)
        
        return chunk.id
    
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """
        获取分块
        
        Args:
            chunk_id: 分块 ID
            
        Returns:
            分块对象
        """
        return self.chunks.get(chunk_id)
    
    def update_chunk(self, chunk: Chunk):
        """
        更新分块
        
        Args:
            chunk: 分块对象
        """
        if chunk.id in self.chunks:
            self.chunks[chunk.id] = chunk
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """
        删除分块
        
        Args:
            chunk_id: 分块 ID
            
        Returns:
            是否删除成功
        """
        if chunk_id not in self.chunks:
            return False
        
        chunk = self.chunks[chunk_id]
        
        # 从文档中移除
        if chunk.document_id and chunk.document_id in self.documents:
            self.documents[chunk.document_id].remove_chunk(chunk_id)
        
        # 从索引中移除
        if chunk.document_id in self.chunks_by_doc:
            if chunk_id in self.chunks_by_doc[chunk.document_id]:
                self.chunks_by_doc[chunk.document_id].remove(chunk_id)
        
        # 删除分块
        del self.chunks[chunk_id]
        
        return True
    
    def get_document_chunks(self, doc_id: str) -> List[Chunk]:
        """
        获取文档的所有分块
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            分块列表
        """
        chunk_ids = self.chunks_by_doc.get(doc_id, [])
        chunks = [self.chunks[cid] for cid in chunk_ids if cid in self.chunks]
        # 按索引排序
        chunks.sort(key=lambda c: c.chunk_index)
        return chunks
    
    def find_chunks(
        self,
        document_id: Optional[str] = None,
        chunk_type: Optional[ChunkType] = None,
        has_embedding: Optional[bool] = None,
        has_entities: Optional[bool] = None,
        filter_func: Optional[Callable[[Chunk], bool]] = None
    ) -> List[Chunk]:
        """
        查找分块
        
        Args:
            document_id: 文档 ID 过滤
            chunk_type: 分块类型过滤
            has_embedding: 是否有嵌入向量
            has_entities: 是否有实体
            filter_func: 自定义过滤函数
            
        Returns:
            分块列表
        """
        # 先根据文档 ID 快速过滤
        if document_id:
            chunk_ids = self.chunks_by_doc.get(document_id, [])
            chunks = [self.chunks[cid] for cid in chunk_ids if cid in self.chunks]
        else:
            chunks = list(self.chunks.values())
        
        # 应用其他过滤条件
        results = []
        for chunk in chunks:
            # 类型过滤
            if chunk_type and chunk.chunk_type != chunk_type:
                continue
            
            # 嵌入过滤
            if has_embedding is not None and chunk.has_embedding() != has_embedding:
                continue
            
            # 实体过滤
            if has_entities is not None and chunk.has_entities() != has_entities:
                continue
            
            # 自定义过滤
            if filter_func and not filter_func(chunk):
                continue
            
            results.append(chunk)
        
        return results
    
    # ==================== 关系操作 ====================
    
    def add_chunk_relation(self, relation: ChunkRelation):
        """
        添加分块关系
        
        Args:
            relation: 分块关系
        """
        self.chunk_relations.append(relation)
    
    def get_chunk_relations(
        self,
        source_chunk_id: Optional[str] = None,
        target_chunk_id: Optional[str] = None,
        relation_type: Optional[str] = None
    ) -> List[ChunkRelation]:
        """
        获取分块关系
        
        Args:
            source_chunk_id: 源分块 ID
            target_chunk_id: 目标分块 ID
            relation_type: 关系类型
            
        Returns:
            关系列表
        """
        results = []
        for relation in self.chunk_relations:
            if source_chunk_id and relation.source_chunk_id != source_chunk_id:
                continue
            if target_chunk_id and relation.target_chunk_id != target_chunk_id:
                continue
            if relation_type and relation.relation_type != relation_type:
                continue
            results.append(relation)
        return results
    
    # ==================== 统计和分析 ====================
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_documents': len(self.documents),
            'total_chunks': len(self.chunks),
            'total_relations': len(self.chunk_relations),
            'documents_by_status': {},
            'documents_by_category': {},
            'documents_by_type': {},
            'avg_chunks_per_doc': 0,
            'chunks_with_embedding': 0,
            'chunks_with_entities': 0
        }
        
        # 按状态统计
        for status in DocumentStatus:
            stats['documents_by_status'][status.value] = len(
                self.doc_by_status.get(status, [])
            )
        
        # 按分类统计
        stats['documents_by_category'] = {
            cat: len(docs) for cat, docs in self.doc_by_category.items()
        }
        
        # 按类型统计
        doc_types = {}
        for doc in self.documents.values():
            doc_type = doc.doc_type.value
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        stats['documents_by_type'] = doc_types
        
        # 平均分块数
        if self.documents:
            total_chunks = sum(doc.chunk_count for doc in self.documents.values())
            stats['avg_chunks_per_doc'] = total_chunks / len(self.documents)
        
        # 分块统计
        stats['chunks_with_embedding'] = sum(
            1 for chunk in self.chunks.values() if chunk.has_embedding()
        )
        stats['chunks_with_entities'] = sum(
            1 for chunk in self.chunks.values() if chunk.has_entities()
        )
        
        return stats
    
    # ==================== 持久化 ====================
    
    def save_to_file(self, filepath: str):
        """
        保存到文件
        
        Args:
            filepath: 文件路径
        """
        data = {
            'documents': {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()},
            'chunks': {chunk_id: chunk.to_dict() for chunk_id, chunk in self.chunks.items()},
            'chunk_relations': [rel.to_dict() for rel in self.chunk_relations]
        }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 仓库已保存到: {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'DocumentRepository':
        """
        从文件加载
        
        Args:
            filepath: 文件路径
            
        Returns:
            文档仓库实例
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        repo = cls()
        
        # 加载文档
        for doc_data in data.get('documents', {}).values():
            doc_data['doc_type'] = DocumentType(doc_data['doc_type'])
            doc_data['status'] = DocumentStatus(doc_data['status'])
            doc = Document.from_dict(doc_data)
            repo.documents[doc.id] = doc
            repo._update_document_indices(doc)
        
        # 加载分块
        for chunk_data in data.get('chunks', {}).values():
            chunk_data['chunk_type'] = ChunkType(chunk_data['chunk_type'])
            if chunk_data.get('embedding'):
                import numpy as np
                chunk_data['embedding'] = np.array(chunk_data['embedding'])
            chunk = Chunk.from_dict(chunk_data)
            repo.chunks[chunk.id] = chunk
            
            # 更新索引
            if chunk.document_id:
                if chunk.document_id not in repo.chunks_by_doc:
                    repo.chunks_by_doc[chunk.document_id] = []
                repo.chunks_by_doc[chunk.document_id].append(chunk.id)
        
        # 加载关系
        for rel_data in data.get('chunk_relations', []):
            rel = ChunkRelation(**rel_data)
            repo.chunk_relations.append(rel)
        
        print(f"✅ 仓库已从 {filepath} 加载")
        return repo
    
    # ==================== 内部辅助方法 ====================
    
    def _update_document_indices(self, document: Document):
        """更新文档索引"""
        # 按来源索引
        if document.source:
            if document.source not in self.doc_by_source:
                self.doc_by_source[document.source] = []
            if document.id not in self.doc_by_source[document.source]:
                self.doc_by_source[document.source].append(document.id)
        
        # 按分类索引
        if document.category:
            if document.category not in self.doc_by_category:
                self.doc_by_category[document.category] = []
            if document.id not in self.doc_by_category[document.category]:
                self.doc_by_category[document.category].append(document.id)
        
        # 按状态索引
        if document.status not in self.doc_by_status:
            self.doc_by_status[document.status] = []
        if document.id not in self.doc_by_status[document.status]:
            self.doc_by_status[document.status].append(document.id)
    
    def _remove_document_indices(self, document: Document):
        """移除文档索引"""
        # 从来源索引移除
        if document.source and document.source in self.doc_by_source:
            if document.id in self.doc_by_source[document.source]:
                self.doc_by_source[document.source].remove(document.id)
        
        # 从分类索引移除
        if document.category and document.category in self.doc_by_category:
            if document.id in self.doc_by_category[document.category]:
                self.doc_by_category[document.category].remove(document.id)
        
        # 从状态索引移除
        if document.status in self.doc_by_status:
            if document.id in self.doc_by_status[document.status]:
                self.doc_by_status[document.status].remove(document.id)

