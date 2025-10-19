"""
对话路由 - 支持 SSE 流式响应
"""

import time
import json
import os
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openai import OpenAI

from database import get_db
from database.models import ChatSession, ChatMessage, KnowledgeBase, MessageRoleEnum
from api.schemas import (
    ChatSessionCreate, 
    ChatSessionUpdate, 
    ChatSessionResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatHistoryResponse,
    MessageResponse
)
from api.services.document_service import document_service

router = APIRouter(prefix="/chat", tags=["chat"])


# ==================== 会话管理 ====================

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    """
    创建新会话
    
    - **knowledge_base_id**: 关联的知识库ID
    - **title**: 会话标题（可选）
    - **use_vector_search**: 是否使用向量搜索
    - **use_graph_search**: 是否使用图谱搜索
    - **search_top_k**: 检索数量
    """
    # 验证知识库是否存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == session_data.knowledge_base_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 {session_data.knowledge_base_id} 不存在"
        )
    
    # 创建会话
    session = ChatSession(
        knowledge_base_id=session_data.knowledge_base_id,
        title=session_data.title or "新对话",
        use_vector_search=session_data.use_vector_search,
        use_graph_search=session_data.use_graph_search,
        search_top_k=session_data.search_top_k
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_sessions(
    knowledge_base_id: int = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取会话列表
    
    - **knowledge_base_id**: 筛选知识库（可选）
    - **skip**: 跳过数量
    - **limit**: 返回数量
    """
    query = db.query(ChatSession)
    
    if knowledge_base_id:
        query = query.filter(ChatSession.knowledge_base_id == knowledge_base_id)
    
    sessions = query.order_by(ChatSession.last_active_at.desc()).offset(skip).limit(limit).all()
    
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """获取会话详情"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在"
        )
    
    return session


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: int,
    session_update: ChatSessionUpdate,
    db: Session = Depends(get_db)
):
    """更新会话配置"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在"
        )
    
    # 更新字段
    if session_update.title is not None:
        session.title = session_update.title
    if session_update.use_vector_search is not None:
        session.use_vector_search = session_update.use_vector_search
    if session_update.use_graph_search is not None:
        session.use_graph_search = session_update.use_graph_search
    if session_update.search_top_k is not None:
        session.search_top_k = session_update.search_top_k
    
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return session


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """删除会话（同时删除所有消息）"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在"
        )
    
    db.delete(session)
    db.commit()
    
    return MessageResponse(message=f"会话 {session_id} 已删除")


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
def get_session_history(
    session_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取会话历史
    
    - **session_id**: 会话ID
    - **limit**: 返回消息数量
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在"
        )
    
    # 获取最近的消息
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    # 反转顺序（最早的在前）
    messages.reverse()
    
    return ChatHistoryResponse(
        session=session,
        messages=messages,
        total=len(messages)
    )


# ==================== 对话接口 ====================

@router.post("/completions")
async def chat_completion(
    chat_req: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    对话接口 - 支持流式和非流式响应
    
    - **session_id**: 会话ID
    - **message**: 用户消息
    - **stream**: 是否流式返回（默认 true）
    - **temperature**: 生成温度
    - **max_tokens**: 最大生成长度
    
    流式响应使用 SSE (Server-Sent Events) 格式：
    ```
    data: {"type": "context", "data": {...}}
    data: {"type": "chunk", "data": "文本片段"}
    data: {"type": "done", "data": {...}}
    ```
    """
    # 验证会话
    session = db.query(ChatSession).filter(ChatSession.id == chat_req.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {chat_req.session_id} 不存在"
        )
    
    # 验证知识库
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == session.knowledge_base_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库 {session.knowledge_base_id} 不存在"
        )
    
    # 流式响应
    if chat_req.stream:
        return StreamingResponse(
            chat_stream_generator(db, session, kb, chat_req),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        # 非流式响应
        result = await chat_non_stream(db, session, kb, chat_req)
        return result


async def chat_stream_generator(
    db: Session,
    session: ChatSession,
    kb: KnowledgeBase,
    chat_req: ChatRequest
) -> AsyncGenerator[str, None]:
    """SSE 流式生成器"""
    
    start_time = time.time()
    
    try:
        # 1. 保存用户消息
        user_message = ChatMessage(
            session_id=session.id,
            role=MessageRoleEnum.USER,
            content=chat_req.message,
            token_count=len(chat_req.message) // 4  # 粗略估计
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 2. 检索相关内容（RAG）
        retrieved_chunks = []
        retrieved_entities = []
        context_text = ""
        
        if session.use_vector_search or session.use_graph_search:
            # 向量搜索
            if session.use_vector_search:
                chunks_with_scores = document_service.search_documents(
                    db=db,
                    kb_id=kb.id,
                    query=chat_req.message,
                    top_k=session.search_top_k
                )
                
                for chunk, score in chunks_with_scores:
                    retrieved_chunks.append({
                        'chunk_id': chunk.id,
                        'document_id': chunk.document_id,
                        'content': chunk.content[:200],  # 截断
                        'score': score
                    })
                    context_text += f"\n\n文档片段 {chunk.chunk_index}：\n{chunk.content}"

            # 图谱搜索
            if session.use_graph_search:
                graph_results = document_service.search_graph(
                    db=db,
                    kb_id=kb.id,
                    query=chat_req.message,
                    top_k=session.search_top_k
                )
                
                for gr in graph_results:
                    retrieved_entities.append({
                        'entity_name': gr['entity_name'],
                        'entity_type': gr['entity_type'],
                        'related_entities': gr['related_entities']
                    })
                
                    # 添加图谱信息到上下文
                    context_text += f"\n\n实体：{gr['entity_name']} ({gr['entity_type']})"
                    if gr['related_entities']:
                        context_text += f"\n相关实体："
                        for rel in gr['related_entities'][:3]:
                            context_text += f"\n  - {rel['name']} ({rel['relation']})"
        
        # 发送上下文信息
        yield f"data: {json.dumps({'type': 'context', 'data': {'chunks': len(retrieved_chunks), 'entities': len(retrieved_entities)}}, ensure_ascii=False)}\n\n"
        
        # 3. 获取历史消息（滑动窗口，最近5条）
        history_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.id < user_message.id  # 排除当前用户消息
        ).order_by(ChatMessage.created_at.desc()).limit(5).all()
        
        history_messages.reverse()  # 时间顺序
        
        # 4. 构建 OpenAI 消息
        openai_messages = []
        
        # 系统提示
        system_prompt = f"""你是一个智能助手，基于提供的知识库内容回答用户问题。

知识库名称：{kb.name}
知识库描述：{kb.description or '无'}

回答要求：
1. 优先使用检索到的知识库内容回答
2. 如果知识库中没有相关信息，请诚实告知
3. 引用具体内容时注明来源
4. 回答要准确、简洁、有帮助"""

        if context_text:
            system_prompt += f"\n\n检索到的相关内容：{context_text}"
        
        openai_messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 历史消息
        for msg in history_messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        # 当前用户消息
        openai_messages.append({
            "role": "user",
            "content": chat_req.message
        })
        
        # 5. 调用 OpenAI API（流式）
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        if not api_key:
            raise ValueError("未设置 OPENAI_API_KEY")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        stream = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=chat_req.temperature,
            max_tokens=chat_req.max_tokens,
            stream=True
        )
        
        # 6. 流式输出
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                
                # 发送内容块
                yield f"data: {json.dumps({'type': 'chunk', 'data': content}, ensure_ascii=False)}\n\n"
        
        # 7. 保存助手回复
        processing_time = time.time() - start_time
        
        assistant_message = ChatMessage(
            session_id=session.id,
            role=MessageRoleEnum.ASSISTANT,
            content=full_response,
            retrieved_chunks=retrieved_chunks,
            retrieved_entities=retrieved_entities,
            context_used=context_text[:1000] if context_text else None,  # 截断
            token_count=len(full_response) // 4,
            processing_time=processing_time
        )
        db.add(assistant_message)
        
        # 更新会话统计
        session.message_count += 2  # 用户 + 助手
        session.total_tokens += user_message.token_count + assistant_message.token_count
        session.last_active_at = datetime.utcnow()
        
        db.commit()
        db.refresh(assistant_message)
        
        # 8. 发送完成信号
        yield f"data: {json.dumps({'type': 'done', 'data': {'message_id': assistant_message.id, 'processing_time': processing_time}}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 对话失败: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # 发送错误
        yield f"data: {json.dumps({'type': 'error', 'data': error_msg}, ensure_ascii=False)}\n\n"


async def chat_non_stream(
    db: Session,
    session: ChatSession,
    kb: KnowledgeBase,
    chat_req: ChatRequest
):
    """非流式对话"""
    
    start_time = time.time()
    
    try:
        # 1. 保存用户消息
        user_message = ChatMessage(
            session_id=session.id,
            role=MessageRoleEnum.USER,
            content=chat_req.message,
            token_count=len(chat_req.message) // 4
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 2. 检索相关内容
        retrieved_chunks = []
        retrieved_entities = []
        context_text = ""
        
        if session.use_vector_search:
            chunks_with_scores = document_service.search_documents(
                db=db,
                kb_id=kb.id,
                query=chat_req.message,
                top_k=session.search_top_k
            )
            for chunk, score in chunks_with_scores:
                retrieved_chunks.append({
                    'chunk_id': chunk.id,
                    'document_id': chunk.document_id,
                    'content': chunk.content[:200],
                    'score': score
                })
                context_text += f"\n\n文档片段 {chunk.chunk_index}：\n{chunk.content}"
        
        if session.use_graph_search:
            graph_results = document_service.search_graph(
                db=db,
                kb_id=kb.id,
                query=chat_req.message,
                top_k=session.search_top_k
            )
            
            for gr in graph_results:
                retrieved_entities.append({
                    'entity_name': gr['entity_name'],
                    'entity_type': gr['entity_type'],
                    'related_entities': gr['related_entities']
                })
                
                context_text += f"\n\n实体：{gr['entity_name']} ({gr['entity_type']})"
                if gr['related_entities']:
                    context_text += f"\n相关实体："
                    for rel in gr['related_entities'][:3]:
                        context_text += f"\n  - {rel['name']} ({rel['relation']})"
        
        # 3. 获取历史消息
        history_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.id < user_message.id
        ).order_by(ChatMessage.created_at.desc()).limit(5).all()
        
        history_messages.reverse()
        
        # 4. 构建 OpenAI 消息
        openai_messages = []
        
        system_prompt = f"""你是一个智能助手，基于提供的知识库内容回答用户问题。

知识库名称：{kb.name}
知识库描述：{kb.description or '无'}

回答要求：
1. 优先使用检索到的知识库内容回答
2. 如果知识库中没有相关信息，请诚实告知
3. 引用具体内容时注明来源
4. 回答要准确、简洁、有帮助"""

        if context_text:
            system_prompt += f"\n\n检索到的相关内容：{context_text}"
        
        openai_messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        for msg in history_messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        openai_messages.append({
            "role": "user",
            "content": chat_req.message
        })
        
        # 5. 调用 OpenAI API
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        if not api_key:
            raise ValueError("未设置 OPENAI_API_KEY")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=chat_req.temperature,
            max_tokens=chat_req.max_tokens
        )
        
        full_response = response.choices[0].message.content
        
        # 6. 保存助手回复
        processing_time = time.time() - start_time
        
        assistant_message = ChatMessage(
            session_id=session.id,
            role=MessageRoleEnum.ASSISTANT,
            content=full_response,
            retrieved_chunks=retrieved_chunks,
            retrieved_entities=retrieved_entities,
            context_used=context_text[:1000] if context_text else None,
            token_count=len(full_response) // 4,
            processing_time=processing_time
        )
        db.add(assistant_message)
        
        # 更新会话统计
        session.message_count += 2
        session.total_tokens += user_message.token_count + assistant_message.token_count
        session.last_active_at = datetime.utcnow()
        
        db.commit()
        db.refresh(assistant_message)
        
        return {
            "message_id": assistant_message.id,
            "content": full_response,
            "retrieved_chunks": retrieved_chunks,
            "retrieved_entities": retrieved_entities,
            "processing_time": processing_time
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对话失败: {str(e)}"
        )

