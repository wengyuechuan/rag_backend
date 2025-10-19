"""
知识库管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db, KnowledgeBase
from api.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    MessageResponse
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("/", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    创建知识库
    
    - **name**: 知识库名称（唯一）
    - **description**: 描述信息
    - **default_chunk_strategy**: 默认分块策略
    - **default_chunk_size**: 默认分块大小
    - **default_chunk_overlap**: 默认分块重叠
    - **enable_vector_store**: 是否启用向量存储
    - **enable_knowledge_graph**: 是否启用知识图谱
    - **enable_ner**: 是否启用实体关系提取
    """
    # 检查名称是否已存在
    existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == kb_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"知识库名称 '{kb_data.name}' 已存在"
        )
    
    # 创建知识库
    kb = KnowledgeBase(
        name=kb_data.name,
        description=kb_data.description,
        default_chunk_strategy=kb_data.default_chunk_strategy.value,
        default_chunk_size=kb_data.default_chunk_size,
        default_chunk_overlap=kb_data.default_chunk_overlap,
        enable_vector_store=kb_data.enable_vector_store,
        enable_knowledge_graph=kb_data.enable_knowledge_graph,
        enable_ner=kb_data.enable_ner,
        embedding_model=kb_data.embedding_model
    )
    
    db.add(kb)
    db.commit()
    db.refresh(kb)
    
    return kb


@router.get("/", response_model=List[KnowledgeBaseResponse])
def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取知识库列表
    
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    """
    kbs = db.query(KnowledgeBase).offset(skip).limit(limit).all()
    return kbs


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """获取指定知识库的详细信息"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 ID {kb_id} 不存在"
        )
    return kb


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    kb_id: int,
    kb_update: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """更新知识库配置"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 ID {kb_id} 不存在"
        )
    
    # 更新字段
    update_data = kb_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(kb, field):
            setattr(kb, field, value)
    
    db.commit()
    db.refresh(kb)
    
    return kb


@router.delete("/{kb_id}", response_model=MessageResponse)
def delete_knowledge_base(
    kb_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除知识库
    
    - **force**: 是否强制删除（即使包含文档）
    """
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 ID {kb_id} 不存在"
        )
    
    # 检查是否包含文档
    if kb.document_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"知识库包含 {kb.document_count} 个文档，请使用 force=true 强制删除"
        )
    
    db.delete(kb)
    db.commit()
    
    return MessageResponse(
        message=f"知识库 '{kb.name}' 已删除",
        data={"deleted_documents": kb.document_count}
    )

