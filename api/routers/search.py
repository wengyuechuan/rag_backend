"""
搜索路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import time

from database import get_db
from api.schemas import SearchRequest, SearchResponse, SearchResult
from api.services.document_service import document_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
def search_documents(
    search_req: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    搜索文档
    
    - **query**: 搜索查询文本
    - **knowledge_base_id**: 限定搜索的知识库
    - **top_k**: 返回结果数量
    - **use_vector**: 是否使用向量检索
    - **use_graph**: 是否使用图谱检索
    
    搜索类型：
    - vector: 仅向量搜索
    - graph: 仅图谱搜索
    - hybrid: 混合搜索（向量 + 图谱）
    """
    start_time = time.time()
    
    if not search_req.knowledge_base_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须指定 knowledge_base_id"
        )
    
    search_results = []
    graph_results = []
    search_type = "none"
    
    # 1. 向量搜索
    if search_req.use_vector:
        search_type = "vector"
        chunks_with_scores = document_service.search_documents(
            db=db,
            kb_id=search_req.knowledge_base_id,
            query=search_req.query,
            top_k=search_req.top_k
        )
        
        for chunk, score in chunks_with_scores:
            # 获取实体和关系（如果也启用了图谱）
            entities = chunk.entities if search_req.use_graph else None
            relations = chunk.relations if search_req.use_graph else None
            
            result = SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                content=chunk.content,
                score=score,
                chunk_index=chunk.chunk_index,
                entities=entities,
                relations=relations
            )
            search_results.append(result)
    
    # 2. 图谱搜索
    if search_req.use_graph:
        if search_type == "vector":
            search_type = "hybrid"  # 混合搜索
        else:
            search_type = "graph"
        
        from api.schemas import GraphSearchResult
        
        graph_search_results = document_service.search_graph(
            db=db,
            kb_id=search_req.knowledge_base_id,
            query=search_req.query,
            top_k=search_req.top_k
        )
        
        for graph_data in graph_search_results:
            graph_result = GraphSearchResult(
                entity_name=graph_data['entity_name'],
                entity_type=graph_data['entity_type'],
                related_entities=graph_data['related_entities'],
                relations=graph_data['relations'],
                chunk_ids=graph_data['chunk_ids'],
                relevance_score=graph_data['relevance_score']
            )
            graph_results.append(graph_result)
            
            # 如果只启用图谱搜索（没有向量搜索），添加相关文本块到结果中
            if not search_req.use_vector and graph_data.get('chunks'):
                for chunk_data in graph_data['chunks'][:3]:  # 每个实体最多3个文本块
                    from database import DocumentChunk
                    chunk = db.query(DocumentChunk).filter(
                        DocumentChunk.id == chunk_data['chunk_id']
                    ).first()
                    
                    if chunk:
                        result = SearchResult(
                            chunk_id=chunk.id,
                            document_id=chunk.document_id,
                            document_title=chunk.document.title,
                            content=chunk.content,
                            score=graph_data['relevance_score'],
                            chunk_index=chunk.chunk_index,
                            entities=chunk.entities,
                            relations=chunk.relations,
                            graph_context={
                                'matched_entity': graph_data['entity_name'],
                                'entity_type': graph_data['entity_type'],
                                'related_count': len(graph_data['related_entities'])
                            }
                        )
                        search_results.append(result)
    
    processing_time = time.time() - start_time
    
    return SearchResponse(
        query=search_req.query,
        results=search_results,
        total=len(search_results),
        processing_time=processing_time,
        graph_results=graph_results if graph_results else None,
        search_type=search_type
    )

