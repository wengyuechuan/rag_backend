"""
文档管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from pathlib import Path

from database import get_db, Document, DocumentChunk, KnowledgeBase, DocumentStatusEnum
from api.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentDetailResponse,
    ChunkResponse,
    MessageResponse
)
from api.services.document_service import document_service
from utils.file_parser import file_parser

router = APIRouter(prefix="/documents", tags=["documents"])

# 上传文件保存目录
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    doc_data: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建文档并添加到知识库
    
    - **knowledge_base_id**: 知识库ID
    - **title**: 文档标题
    - **content**: 文档内容
    - **chunk_strategy**: 分块策略（可选，默认使用知识库配置）
    - **chunk_size**: 分块大小（可选）
    - **chunk_overlap**: 分块重叠（可选）
    - **auto_process**: 是否自动处理（默认true）
    """
    # 检查知识库是否存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc_data.knowledge_base_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 ID {doc_data.knowledge_base_id} 不存在"
        )
    
    # 创建文档
    document = Document(
        knowledge_base_id=doc_data.knowledge_base_id,
        title=doc_data.title,
        content=doc_data.content,
        source=doc_data.source,
        author=doc_data.author,
        category=doc_data.category,
        tags=doc_data.tags,
        chunk_strategy=doc_data.chunk_strategy.value if doc_data.chunk_strategy else None,
        chunk_size=doc_data.chunk_size,
        chunk_overlap=doc_data.chunk_overlap,
        status=DocumentStatusEnum.PENDING
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # 如果启用自动处理，提交到异步队列
    if doc_data.auto_process:
        document_service.process_document_async(document.id, kb.id)
    
    return document


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    file: UploadFile = File(...),
    knowledge_base_id: int = Form(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON 字符串
    chunk_strategy: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    auto_process: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    上传文件并创建文档
    
    支持的文件格式:
    - 文本文件: .txt, .md
    - PDF 文档: .pdf
    - Word 文档: .docx
    - HTML 文档: .html, .htm
    - 数据文件: .json, .csv
    
    参数:
    - **file**: 上传的文件
    - **knowledge_base_id**: 知识库ID
    - **title**: 文档标题（可选，默认使用文件名）
    - **chunk_strategy**: 分块策略（可选）
    - **auto_process**: 是否自动处理（默认true）
    """
    # 检查知识库
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 ID {knowledge_base_id} 不存在"
        )
    
    # 检查文件类型
    if not file_parser.is_supported(file.filename):
        supported = ', '.join(file_parser.get_supported_formats().keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式。支持的格式: {supported}"
        )
    
    # 生成唯一文件名
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        # 保存上传的文件
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 解析文件内容
        try:
            parse_result = file_parser.parse_file(str(file_path), file.filename)
            text_content = parse_result['content']
            
            if not text_content or len(text_content.strip()) == 0:
                raise ValueError("文件内容为空")
            
        except Exception as e:
            # 删除已上传的文件
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件解析失败: {str(e)}"
            )
        
        # 解析 tags
        import json
        tag_list = []
        if tags:
            try:
                tag_list = json.loads(tags) if isinstance(tags, str) else tags
            except:
                tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        
        # 创建文档记录
        document = Document(
            knowledge_base_id=knowledge_base_id,
            title=title or file.filename,
            content=text_content,
            source=f"上传文件: {file.filename}",
            file_path=str(file_path),
            author=author,
            category=category,
            tags=tag_list,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            status=DocumentStatusEnum.PENDING
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 如果启用自动处理，提交到异步队列
        if auto_process:
            document_service.process_document_async(document.id, kb.id)
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        # 清理文件
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("/supported-formats", response_model=MessageResponse)
def get_supported_file_formats():
    """获取支持的文件格式列表"""
    formats = file_parser.get_supported_formats()
    
    return MessageResponse(
        message="支持的文件格式",
        data={
            "formats": formats,
            "extensions": list(formats.keys())
        }
    )


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    knowledge_base_id: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取文档列表
    
    - **knowledge_base_id**: 过滤知识库
    - **status**: 过滤状态
    - **category**: 过滤分类
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    """
    query = db.query(Document)
    
    if knowledge_base_id:
        query = query.filter(Document.knowledge_base_id == knowledge_base_id)
    
    if status:
        try:
            status_enum = DocumentStatusEnum(status)
            query = query.filter(Document.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值: {status}"
            )
    
    if category:
        query = query.filter(Document.category == category)
    
    documents = query.offset(skip).limit(limit).all()
    return documents


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """获取文档详情（包含完整内容）"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 ID {doc_id} 不存在"
        )
    return document


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: int,
    doc_update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """更新文档信息"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 ID {doc_id} 不存在"
        )
    
    # 更新字段
    update_data = doc_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(document, field):
            setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return document


@router.delete("/{doc_id}", response_model=MessageResponse)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """删除文档及其所有分块"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 ID {doc_id} 不存在"
        )
    
    chunk_count = len(document.chunks)
    kb = document.knowledge_base
    
    # 更新知识库统计
    if kb:
        kb.document_count = max(0, kb.document_count - 1)
        kb.total_chunks = max(0, kb.total_chunks - chunk_count)
    
    db.delete(document)
    db.commit()
    
    return MessageResponse(
        message=f"文档 '{document.title}' 已删除",
        data={"deleted_chunks": chunk_count}
    )


@router.post("/{doc_id}/process", response_model=MessageResponse)
def process_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    reprocess: bool = False,
    db: Session = Depends(get_db)
):
    """
    手动触发文档处理
    
    - **reprocess**: 是否重新处理（会删除现有分块）
    """
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 ID {doc_id} 不存在"
        )
    
    kb = document.knowledge_base
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档所属的知识库不存在"
        )
    
    # 如果是重新处理，删除现有分块
    if reprocess and document.chunks:
        for chunk in document.chunks:
            db.delete(chunk)
        document.chunk_count = 0
        document.status = DocumentStatusEnum.PENDING
        db.commit()
    
    # 提交到异步队列
    document_service.process_document_async(document.id, kb.id)
    
    return MessageResponse(
        message=f"文档 '{document.title}' 已添加到处理队列",
        data={"document_id": document.id, "status": "queued"}
    )


@router.get("/{doc_id}/chunks", response_model=List[ChunkResponse])
def get_document_chunks(
    doc_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取文档的所有分块"""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 ID {doc_id} 不存在"
        )
    
    chunks = db.query(DocumentChunk)\
        .filter(DocumentChunk.document_id == doc_id)\
        .order_by(DocumentChunk.chunk_index)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return chunks


@router.get("/{doc_id}/status", response_model=MessageResponse)
def get_document_processing_status(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    获取文档处理状态
    
    返回文档在数据库中的状态以及在处理队列中的状态
    """
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 ID {doc_id} 不存在"
        )
    
    # 获取队列状态
    queue_status = document_service.get_processing_status(doc_id)
    
    return MessageResponse(
        message="文档状态查询成功",
        data={
            "document_id": doc_id,
            "db_status": document.status.value if hasattr(document.status, 'value') else str(document.status),
            "in_processing_queue": queue_status['in_queue'],
            "is_running": queue_status['running'],
            "chunk_count": document.chunk_count,
            "vector_stored": document.vector_stored,
            "graph_stored": document.graph_stored,
            "error_message": document.error_message,
            "processing_time": document.processing_time,
            "processed_at": document.processed_at.isoformat() if document.processed_at else None
        }
    )

