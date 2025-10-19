"""
基于 FAISS 的向量知识库工具类
支持使用 Ollama 进行文本嵌入和向量检索
"""

import faiss
import numpy as np
import json
import pickle
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import requests


@dataclass
class DocumentMetadata:
    """文档元数据"""
    doc_id: str
    text: str
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OllamaEmbedding:
    """
    Ollama Embedding 封装类
    用于生成文本嵌入向量
    """
    
    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434"
    ):
        """
        初始化 Ollama Embedding
        
        Args:
            model: 使用的嵌入模型名称（如 nomic-embed-text, mxbai-embed-large 等）
            base_url: Ollama API 地址
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/embeddings"
        self._dimension = None
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        获取单个文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            embedding = np.array(result['embedding'], dtype=np.float32)
            
            # 缓存维度信息
            if self._dimension is None:
                self._dimension = len(embedding)
            
            return embedding
        except Exception as e:
            raise RuntimeError(f"获取嵌入失败: {str(e)}")
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        批量获取文本的嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量矩阵，形状为 (n, dimension)
        """
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return np.vstack(embeddings)
    
    @property
    def dimension(self) -> int:
        """获取嵌入维度"""
        if self._dimension is None:
            # 通过一个测试文本获取维度
            test_embedding = self.get_embedding("test")
            self._dimension = len(test_embedding)
        return self._dimension


class FaissVectorStore:
    """
    基于 FAISS 的向量知识库
    
    功能：
    1. 初始化不同类型的 FAISS 索引
    2. 使用 Ollama 生成嵌入向量
    3. 批量存储文本和向量
    4. 相似度搜索
    5. 保存和加载索引
    6. 向量管理（添加、删除）
    """
    
    def __init__(
        self,
        embedding_model: str = "nomic-embed-text",
        index_type: str = "Flat",
        dimension: Optional[int] = None,
        ollama_base_url: str = "http://localhost:11434",
        metric: str = "L2"
    ):
        """
        初始化向量存储
        
        Args:
            embedding_model: Ollama 嵌入模型名称
            index_type: FAISS 索引类型 ("Flat", "IVF", "HNSW")
            dimension: 向量维度（如果为 None，会自动从模型获取）
            ollama_base_url: Ollama API 地址
            metric: 距离度量方式 ("L2", "IP"(内积), "Cosine")
        """
        # 初始化嵌入模型
        self.embedding = OllamaEmbedding(embedding_model, ollama_base_url)
        
        # 获取维度
        self.dimension = dimension or self.embedding.dimension
        self.index_type = index_type
        self.metric = metric
        
        # 初始化 FAISS 索引
        self.index = self._create_index()
        
        # 存储文档元数据
        self.documents: Dict[int, DocumentMetadata] = {}
        self.doc_id_to_idx: Dict[str, int] = {}
        self.current_idx = 0
    
    def _create_index(self) -> faiss.Index:
        """
        创建 FAISS 索引
        
        Returns:
            FAISS 索引对象
        """
        if self.metric == "L2":
            if self.index_type == "Flat":
                # 最简单的索引，精确搜索
                index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "IVF":
                # 倒排文件索引，适合大规模数据
                nlist = 100  # 聚类中心数量
                quantizer = faiss.IndexFlatL2(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            elif self.index_type == "HNSW":
                # 分层导航小世界图，快速近似搜索
                index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                raise ValueError(f"不支持的索引类型: {self.index_type}")
        
        elif self.metric == "IP":
            # 内积（适合余弦相似度，需要归一化向量）
            if self.index_type == "Flat":
                index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "IVF":
                nlist = 100
                quantizer = faiss.IndexFlatIP(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            else:
                raise ValueError(f"内积度量不支持索引类型: {self.index_type}")
        
        elif self.metric == "Cosine":
            # 余弦相似度（通过归一化 + 内积实现）
            if self.index_type == "Flat":
                index = faiss.IndexFlatIP(self.dimension)
            else:
                raise ValueError(f"余弦度量不支持索引类型: {self.index_type}")
        
        else:
            raise ValueError(f"不支持的度量方式: {self.metric}")
        
        return index
    
    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """
        归一化向量（用于余弦相似度）
        
        Args:
            vectors: 输入向量矩阵
            
        Returns:
            归一化后的向量矩阵
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / (norms + 1e-8)
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        批量添加文本到向量库
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            doc_ids: 文档 ID 列表（如果为 None，自动生成）
            
        Returns:
            添加的文档 ID 列表
        """
        if not texts:
            return []
        
        # 生成嵌入向量
        print(f"正在生成 {len(texts)} 个文本的嵌入向量...")
        embeddings = self.embedding.get_embeddings(texts)
        
        # 如果使用余弦相似度，需要归一化
        if self.metric == "Cosine":
            embeddings = self._normalize_vectors(embeddings)
        
        # 训练索引（仅对 IVF 类型需要）
        if self.index_type == "IVF" and not self.index.is_trained:
            print("训练 IVF 索引...")
            self.index.train(embeddings)
        
        # 生成文档 ID
        if doc_ids is None:
            doc_ids = [f"doc_{self.current_idx + i}" for i in range(len(texts))]
        
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        # 添加向量到索引
        start_idx = self.current_idx
        self.index.add(embeddings)
        
        # 保存文档元数据
        added_ids = []
        for i, (text, metadata, doc_id) in enumerate(zip(texts, metadatas, doc_ids)):
            idx = start_idx + i
            self.documents[idx] = DocumentMetadata(
                doc_id=doc_id,
                text=text,
                metadata=metadata
            )
            self.doc_id_to_idx[doc_id] = idx
            added_ids.append(doc_id)
            self.current_idx += 1
        
        print(f"成功添加 {len(texts)} 个文档")
        return added_ids
    
    def add_documents(
        self,
        documents: List[DocumentMetadata]
    ) -> List[str]:
        """
        批量添加文档对象
        
        Args:
            documents: 文档元数据列表
            
        Returns:
            添加的文档 ID 列表
        """
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        doc_ids = [doc.doc_id for doc in documents]
        return self.add_texts(texts, metadatas, doc_ids)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        return_scores: bool = True
    ) -> List[Tuple[DocumentMetadata, float]] | List[DocumentMetadata]:
        """
        搜索相似文本
        
        Args:
            query: 查询文本
            top_k: 返回最相似的前 k 个结果
            return_scores: 是否返回相似度分数
            
        Returns:
            搜索结果列表
        """
        if self.index.ntotal == 0:
            return []
        
        # 生成查询向量
        query_vector = self.embedding.get_embedding(query)
        query_vector = query_vector.reshape(1, -1)
        
        # 如果使用余弦相似度，需要归一化
        if self.metric == "Cosine":
            query_vector = self._normalize_vectors(query_vector)
        
        # 搜索
        if self.index_type == "IVF":
            # 设置搜索参数
            self.index.nprobe = 10  # 搜索的聚类中心数量
        
        distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        
        # 构建结果
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # FAISS 返回 -1 表示没有更多结果
                continue
            
            doc = self.documents.get(int(idx))
            if doc is None:
                continue
            
            # 转换距离为相似度分数
            if self.metric == "L2":
                # L2 距离越小越相似
                score = 1.0 / (1.0 + distance)
            elif self.metric in ["IP", "Cosine"]:
                # 内积越大越相似
                score = float(distance)
            else:
                score = float(distance)
            
            if return_scores:
                results.append((doc, score))
            else:
                results.append(doc)
        
        return results
    
    def search_by_vector(
        self,
        vector: np.ndarray,
        top_k: int = 5,
        return_scores: bool = True
    ) -> List[Tuple[DocumentMetadata, float]] | List[DocumentMetadata]:
        """
        使用向量搜索
        
        Args:
            vector: 查询向量
            top_k: 返回最相似的前 k 个结果
            return_scores: 是否返回相似度分数
            
        Returns:
            搜索结果列表
        """
        if self.index.ntotal == 0:
            return []
        
        vector = vector.reshape(1, -1)
        
        if self.metric == "Cosine":
            vector = self._normalize_vectors(vector)
        
        distances, indices = self.index.search(vector, min(top_k, self.index.ntotal))
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            
            doc = self.documents.get(int(idx))
            if doc is None:
                continue
            
            if self.metric == "L2":
                score = 1.0 / (1.0 + distance)
            else:
                score = float(distance)
            
            if return_scores:
                results.append((doc, score))
            else:
                results.append(doc)
        
        return results
    
    def get_document_by_id(self, doc_id: str) -> Optional[DocumentMetadata]:
        """
        根据文档 ID 获取文档
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            文档元数据
        """
        idx = self.doc_id_to_idx.get(doc_id)
        if idx is None:
            return None
        return self.documents.get(idx)
    
    def delete_by_ids(self, doc_ids: List[str]) -> int:
        """
        根据文档 ID 删除文档
        注意：FAISS 不支持直接删除，需要重建索引
        
        Args:
            doc_ids: 要删除的文档 ID 列表
            
        Returns:
            实际删除的文档数量
        """
        deleted_count = 0
        indices_to_remove = set()
        
        for doc_id in doc_ids:
            idx = self.doc_id_to_idx.get(doc_id)
            if idx is not None:
                indices_to_remove.add(idx)
                del self.documents[idx]
                del self.doc_id_to_idx[doc_id]
                deleted_count += 1
        
        if deleted_count > 0:
            # 重建索引
            self._rebuild_index(indices_to_remove)
        
        return deleted_count
    
    def _rebuild_index(self, indices_to_remove: set):
        """重建索引（排除已删除的文档）"""
        # 收集保留的文档
        remaining_docs = []
        new_idx_map = {}
        
        for idx, doc in self.documents.items():
            if idx not in indices_to_remove:
                remaining_docs.append(doc)
        
        # 重新创建索引
        self.index = self._create_index()
        self.documents.clear()
        self.doc_id_to_idx.clear()
        self.current_idx = 0
        
        # 重新添加文档
        if remaining_docs:
            texts = [doc.text for doc in remaining_docs]
            metadatas = [doc.metadata for doc in remaining_docs]
            doc_ids = [doc.doc_id for doc in remaining_docs]
            self.add_texts(texts, metadatas, doc_ids)
    
    def save(self, directory: str):
        """
        保存索引和元数据到磁盘
        
        Args:
            directory: 保存目录
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # 保存 FAISS 索引
        index_path = dir_path / "index.faiss"
        faiss.write_index(self.index, str(index_path))
        
        # 保存元数据
        metadata = {
            'dimension': self.dimension,
            'index_type': self.index_type,
            'metric': self.metric,
            'current_idx': self.current_idx,
            'embedding_model': self.embedding.model,
            'documents': {k: asdict(v) for k, v in self.documents.items()},
            'doc_id_to_idx': self.doc_id_to_idx
        }
        
        metadata_path = dir_path / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"索引已保存到: {directory}")
    
    @classmethod
    def load(
        cls,
        directory: str,
        ollama_base_url: str = "http://localhost:11434"
    ) -> 'FaissVectorStore':
        """
        从磁盘加载索引和元数据
        
        Args:
            directory: 保存目录
            ollama_base_url: Ollama API 地址
            
        Returns:
            加载的向量存储对象
        """
        dir_path = Path(directory)
        
        # 加载元数据
        metadata_path = dir_path / "metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 创建实例
        store = cls(
            embedding_model=metadata['embedding_model'],
            index_type=metadata['index_type'],
            dimension=metadata['dimension'],
            ollama_base_url=ollama_base_url,
            metric=metadata['metric']
        )
        
        # 加载 FAISS 索引
        index_path = dir_path / "index.faiss"
        store.index = faiss.read_index(str(index_path))
        
        # 恢复元数据
        store.current_idx = metadata['current_idx']
        store.documents = {
            int(k): DocumentMetadata(**v)
            for k, v in metadata['documents'].items()
        }
        store.doc_id_to_idx = {
            k: int(v) for k, v in metadata['doc_id_to_idx'].items()
        }
        
        print(f"索引已从 {directory} 加载，共 {store.index.ntotal} 个向量")
        return store
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_documents': len(self.documents),
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'metric': self.metric,
            'embedding_model': self.embedding.model
        }
    
    def clear(self):
        """清空所有数据"""
        self.index.reset()
        self.documents.clear()
        self.doc_id_to_idx.clear()
        self.current_idx = 0


def test_faiss_store():
    """测试函数"""
    print("=" * 80)
    print("FAISS 向量知识库测试")
    print("=" * 80)
    
    try:
        # 初始化向量存储
        print("\n【测试1: 初始化向量存储】")
        print("-" * 80)
        store = FaissVectorStore(
            embedding_model="nomic-embed-text",
            index_type="Flat",
            metric="Cosine"
        )
        print(f"向量维度: {store.dimension}")
        print(f"索引类型: {store.index_type}")
        print(f"度量方式: {store.metric}")
        
        # 添加测试文档
        print("\n【测试2: 批量添加文档】")
        print("-" * 80)
        test_texts = [
            "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
            "机器学习是人工智能的一个子集，专注于让计算机从数据中学习和改进。",
            "深度学习使用多层神经网络来处理复杂的模式识别任务。",
            "自然语言处理使计算机能够理解、解释和生成人类语言。",
            "计算机视觉使机器能够从图像和视频中提取信息。"
        ]
        
        metadatas = [
            {"category": "AI", "topic": "定义"},
            {"category": "AI", "topic": "机器学习"},
            {"category": "AI", "topic": "深度学习"},
            {"category": "NLP", "topic": "自然语言"},
            {"category": "CV", "topic": "计算机视觉"}
        ]
        
        doc_ids = store.add_texts(test_texts, metadatas)
        print(f"添加的文档 ID: {doc_ids}")
        
        # 搜索测试
        print("\n【测试3: 相似度搜索】")
        print("-" * 80)
        query = "什么是机器学习？"
        print(f"查询: {query}")
        results = store.search(query, top_k=3)
        
        for i, (doc, score) in enumerate(results, 1):
            print(f"\n结果 {i}:")
            print(f"  文档ID: {doc.doc_id}")
            print(f"  相似度: {score:.4f}")
            print(f"  文本: {doc.text}")
            print(f"  元数据: {doc.metadata}")
        
        # 根据 ID 获取文档
        print("\n【测试4: 根据 ID 获取文档】")
        print("-" * 80)
        doc = store.get_document_by_id(doc_ids[0])
        if doc:
            print(f"文档ID: {doc.doc_id}")
            print(f"文本: {doc.text}")
        
        # 统计信息
        print("\n【测试5: 统计信息】")
        print("-" * 80)
        stats = store.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # 保存和加载
        print("\n【测试6: 保存索引】")
        print("-" * 80)
        save_dir = "./test_faiss_index"
        store.save(save_dir)
        
        print("\n【测试7: 加载索引】")
        print("-" * 80)
        loaded_store = FaissVectorStore.load(save_dir)
        print(f"加载的文档数量: {loaded_store.get_stats()['total_documents']}")
        
        # 测试加载后的搜索
        results = loaded_store.search("深度学习是什么", top_k=2)
        print(f"\n加载后的搜索结果:")
        for doc, score in results:
            print(f"  - {doc.text[:50]}... (相似度: {score:.4f})")
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("\n提示:")
        print("1. 确保 Ollama 正在运行: ollama serve")
        print("2. 确保已安装嵌入模型: ollama pull nomic-embed-text")
        print("3. 确保已安装依赖: pip install faiss-cpu numpy requests")


if __name__ == "__main__":
    test_faiss_store()

