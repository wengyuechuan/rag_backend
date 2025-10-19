"""
Coze 工作流 API 路由
提供 Coze AI 工作流调用接口
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import time
import json
import os

from api.schemas import (
    CozeWorkflowRequest,
    CozeWorkflowResponse,
    CozeSimpleRequest,
    CozeNodeMessage
)
from utils.coze import CozeClient, CozeMessage

router = APIRouter(prefix="/coze", tags=["coze"])


def convert_coze_message(msg: CozeMessage) -> CozeNodeMessage:
    """将 CozeMessage 转换为 CozeNodeMessage"""
    return CozeNodeMessage(
        node_execute_uuid=msg.node_execute_uuid,
        node_seq_id=msg.node_seq_id,
        node_title=msg.node_title,
        node_type=msg.node_type,
        node_id=msg.node_id,
        content=msg.content,
        content_type=msg.content_type,
        node_is_finish=msg.node_is_finish,
        usage=msg.usage,
        output=msg.get_output()
    )


@router.post("/workflow/run", response_model=CozeWorkflowResponse)
async def run_workflow(request: CozeWorkflowRequest):
    """
    运行 Coze 工作流（非流式）
    
    - **workflow_id**: 工作流 ID
    - **input_text**: 输入文本
    - **parameters**: 额外参数（可选）
    - **bot_id**: Bot ID（可选）
    """
    start_time = time.time()
    
    try:
        # 初始化 Coze 客户端
        client = CozeClient()
        
        # 构建参数
        parameters = request.parameters or {}
        parameters["input"] = request.input_text
        
        # 调用工作流
        response = client.run_workflow(
            workflow_id=request.workflow_id,
            parameters=parameters,
            bot_id=request.bot_id,
            stream=True  # 内部使用流式，但这里返回完整结果
        )
        
        # 转换消息格式
        messages = [convert_coze_message(msg) for msg in response.messages]
        
        return CozeWorkflowResponse(
            workflow_id=request.workflow_id,
            input_text=request.input_text,
            output=response.get_final_output(),
            messages=messages,
            total_tokens=response.total_tokens,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            debug_url=response.debug_url,
            processing_time=time.time() - start_time
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置错误: {str(e)}"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Coze API 调用失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器错误: {str(e)}"
        )


@router.post("/workflow/stream")
async def run_workflow_stream(request: CozeWorkflowRequest):
    """
    运行 Coze 工作流（流式返回）
    
    使用 SSE (Server-Sent Events) 实时返回工作流执行结果
    
    - **workflow_id**: 工作流 ID
    - **input_text**: 输入文本
    - **parameters**: 额外参数（可选）
    - **bot_id**: Bot ID（可选）
    
    返回格式（SSE）：
    ```
    data: {"event": "start", "workflow_id": "xxx"}
    
    data: {"event": "message", "node_title": "节点1", "output": "输出内容"}
    
    data: {"event": "done", "output": "最终输出", "total_tokens": 100}
    ```
    """
    
    async def generate():
        """生成 SSE 流"""
        try:
            # 初始化 Coze 客户端
            client = CozeClient()
            
            # 构建参数
            parameters = request.parameters or {}
            parameters["input"] = request.input_text
            
            # 发送开始事件
            yield f"data: {json.dumps({'event': 'start', 'workflow_id': request.workflow_id}, ensure_ascii=False)}\n\n"
            
            # 流式调用工作流
            final_output = None
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0
            debug_url = None
            
            for message in client.run_workflow_stream(
                workflow_id=request.workflow_id,
                parameters=parameters,
                bot_id=request.bot_id
            ):
                # 提取输出
                output = message.get_output()
                
                # 统计 tokens
                if message.usage:
                    total_tokens += message.usage.get('token_count', 0)
                    input_tokens += message.usage.get('input_count', 0)
                    output_tokens += message.usage.get('output_count', 0)
                
                # 发送节点消息
                event_data = {
                    "event": "message",
                    "node_title": message.node_title,
                    "node_type": message.node_type,
                    "output": output,
                    "node_is_finish": message.node_is_finish
                }
                
                if message.usage:
                    event_data["usage"] = message.usage
                
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                
                # 保存最终输出
                if message.node_type == "End" or message.node_is_finish:
                    if output:
                        final_output = output
            
            # 发送完成事件
            done_data = {
                "event": "done",
                "output": final_output,
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "debug_url": debug_url
            }
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            
        except ValueError as e:
            error_data = {
                "event": "error",
                "error": f"配置错误: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        except RuntimeError as e:
            error_data = {
                "event": "error",
                "error": f"Coze API 调用失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            error_data = {
                "event": "error",
                "error": f"服务器错误: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
        }
    )


@router.post("/simple", response_model=CozeWorkflowResponse)
async def run_simple(request: CozeSimpleRequest):
    """
    简化接口：使用默认工作流
    
    从环境变量 COZE_WORKFLOW_ID 读取默认工作流 ID
    
    - **input_text**: 输入文本
    """
    # 从环境变量获取默认工作流 ID
    default_workflow_id = os.getenv("COZE_WORKFLOW_ID")
    
    if not default_workflow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置默认工作流 ID，请设置环境变量 COZE_WORKFLOW_ID"
        )
    
    # 构建完整请求
    workflow_request = CozeWorkflowRequest(
        workflow_id=default_workflow_id,
        input_text=request.input_text,
        stream=request.stream
    )
    
    # 调用完整接口
    return await run_workflow(workflow_request)


@router.post("/simple/stream")
async def run_simple_stream(request: CozeSimpleRequest):
    """
    简化接口：使用默认工作流（流式返回）
    
    从环境变量 COZE_WORKFLOW_ID 读取默认工作流 ID
    
    - **input_text**: 输入文本
    """
    # 从环境变量获取默认工作流 ID
    default_workflow_id = os.getenv("COZE_WORKFLOW_ID")
    
    if not default_workflow_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "event": "error",
                "error": "未配置默认工作流 ID，请设置环境变量 COZE_WORKFLOW_ID"
            }
        )
    
    # 构建完整请求
    workflow_request = CozeWorkflowRequest(
        workflow_id=default_workflow_id,
        input_text=request.input_text,
        stream=True
    )
    
    # 调用流式接口
    return await run_workflow_stream(workflow_request)


@router.get("/config", tags=["coze"])
async def get_coze_config():
    """
    获取 Coze 配置状态
    
    显示 API Key 和默认工作流配置情况
    """
    api_key = os.getenv("COZE_API_KEY")
    workflow_id = os.getenv("COZE_WORKFLOW_ID")
    base_url = os.getenv("COZE_BASE_URL", "https://api.coze.cn")
    
    def mask_key(key: Optional[str]) -> str:
        """隐藏 API Key"""
        if not key:
            return "<未配置>"
        if len(key) <= 12:
            return "***"
        return key[:12] + "..."
    
    return {
        "configured": bool(api_key),
        "api_key": mask_key(api_key),
        "base_url": base_url,
        "default_workflow_id": workflow_id or "<未配置>",
        "status": "可用" if api_key else "需要配置 COZE_API_KEY"
    }

