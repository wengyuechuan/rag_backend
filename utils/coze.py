"""
Coze 工作流调用工具类
支持流式和非流式调用 Coze AI 工作流
"""

import requests
import json
from typing import Dict, Any, Optional, Generator, List
from dataclasses import dataclass, asdict
import os


@dataclass
class CozeMessage:
    """Coze 消息数据结构"""
    node_execute_uuid: str
    node_seq_id: str
    node_title: str
    node_type: str
    node_id: str
    content: str
    content_type: str
    node_is_finish: bool
    usage: Optional[Dict[str, int]] = None
    
    def get_output(self) -> Optional[str]:
        """从 content 中提取 output 字段"""
        try:
            if self.content:
                content_obj = json.loads(self.content)
                return content_obj.get('output', '')
        except json.JSONDecodeError:
            return self.content
        return None


@dataclass
class CozeResponse:
    """Coze 完整响应"""
    messages: List[CozeMessage]
    debug_url: Optional[str] = None
    total_tokens: int = 0
    output_tokens: int = 0
    input_tokens: int = 0
    
    def get_final_output(self) -> Optional[str]:
        """获取最终输出结果"""
        for msg in reversed(self.messages):
            if msg.node_type == "End" or msg.node_is_finish:
                output = msg.get_output()
                if output:
                    return output
        return None
    
    def get_all_outputs(self) -> List[str]:
        """获取所有节点的输出"""
        outputs = []
        for msg in self.messages:
            output = msg.get_output()
            if output:
                outputs.append(output)
        return outputs


class CozeClient:
    """
    Coze AI 客户端
    用于调用 Coze 工作流 API
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.coze.cn",
        timeout: int = 60
    ):
        """
        初始化 Coze 客户端
        
        Args:
            api_key: Coze API Key（如果不提供，从环境变量 COZE_API_KEY 读取）
            base_url: API 基础 URL
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or os.getenv("COZE_API_KEY")
        if not self.api_key:
            raise ValueError("未设置 Coze API Key，请通过参数或环境变量 COZE_API_KEY 提供")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.stream_url = f"{self.base_url}/v1/workflow/stream_run"
        self.non_stream_url = f"{self.base_url}/v1/workflow/run"
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def run_workflow_stream(
        self,
        workflow_id: str,
        parameters: Dict[str, Any],
        bot_id: Optional[str] = None
    ) -> Generator[CozeMessage, None, CozeResponse]:
        """
        流式调用工作流（生成器模式）
        
        Args:
            workflow_id: 工作流 ID
            parameters: 工作流参数
            bot_id: Bot ID（可选）
            
        Yields:
            CozeMessage: 每个节点的消息
            
        Returns:
            CozeResponse: 完整响应（在生成器结束时）
            
        Example:
            >>> client = CozeClient(api_key="xxx")
            >>> for message in client.run_workflow_stream("workflow_id", {"input": "你好"}):
            ...     print(message.get_output())
        """
        payload = {
            "workflow_id": workflow_id,
            "parameters": parameters
        }
        
        if bot_id:
            payload["bot_id"] = bot_id
        
        try:
            response = requests.post(
                self.stream_url,
                headers=self._get_headers(),
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            messages = []
            debug_url = None
            total_tokens = 0
            output_tokens = 0
            input_tokens = 0
            
            # 解析 SSE 流
            current_event = None
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_text = line.decode('utf-8')
                
                # 解析 SSE 格式
                if line_text.startswith('event: '):
                    current_event = line_text[7:].strip()
                
                elif line_text.startswith('data: '):
                    data_str = line_text[6:].strip()
                    if not data_str or data_str == '[DONE]':
                        continue
                    
                    try:
                        data = json.loads(data_str)
                        
                        if current_event == 'Message':
                            # 解析消息
                            msg = CozeMessage(
                                node_execute_uuid=data.get('node_execute_uuid', ''),
                                node_seq_id=data.get('node_seq_id', ''),
                                node_title=data.get('node_title', ''),
                                node_type=data.get('node_type', ''),
                                node_id=data.get('node_id', ''),
                                content=data.get('content', ''),
                                content_type=data.get('content_type', 'text'),
                                node_is_finish=data.get('node_is_finish', False),
                                usage=data.get('usage')
                            )
                            
                            messages.append(msg)
                            
                            # 统计 token
                            if msg.usage:
                                total_tokens += msg.usage.get('token_count', 0)
                                output_tokens += msg.usage.get('output_count', 0)
                                input_tokens += msg.usage.get('input_count', 0)
                            
                            # 实时返回消息
                            yield msg
                        
                        elif current_event == 'Done':
                            # 解析完成信息
                            debug_url = data.get('debug_url')
                    
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON 解析失败: {e}, 数据: {data_str}")
                        continue
            
            # 返回完整响应
            return CozeResponse(
                messages=messages,
                debug_url=debug_url,
                total_tokens=total_tokens,
                output_tokens=output_tokens,
                input_tokens=input_tokens
            )
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Coze 工作流调用失败: {str(e)}")
    
    def run_workflow(
        self,
        workflow_id: str,
        parameters: Dict[str, Any],
        bot_id: Optional[str] = None,
        stream: bool = False
    ) -> CozeResponse:
        """
        调用工作流（阻塞模式）
        
        Args:
            workflow_id: 工作流 ID
            parameters: 工作流参数
            bot_id: Bot ID（可选）
            stream: 是否使用流式（默认 False）
            
        Returns:
            CozeResponse: 完整响应
            
        Example:
            >>> client = CozeClient(api_key="xxx")
            >>> response = client.run_workflow("workflow_id", {"input": "你好"})
            >>> print(response.get_final_output())
        """
        if stream:
            # 使用流式模式，收集所有消息
            messages = []
            result = None
            for message in self.run_workflow_stream(workflow_id, parameters, bot_id):
                messages.append(message)
            
            # 最后一个 yield 的是 CozeResponse
            # 但在生成器中我们已经 return 了，这里需要手动构建
            # 实际上生成器会在最后 return CozeResponse，但我们需要另一种方式
            
            # 重新实现：收集所有消息
            generator = self.run_workflow_stream(workflow_id, parameters, bot_id)
            messages = list(generator)
            
            # 构建响应（需要从消息中提取统计信息）
            total_tokens = sum(msg.usage.get('token_count', 0) for msg in messages if msg.usage)
            output_tokens = sum(msg.usage.get('output_count', 0) for msg in messages if msg.usage)
            input_tokens = sum(msg.usage.get('input_count', 0) for msg in messages if msg.usage)
            
            return CozeResponse(
                messages=messages,
                total_tokens=total_tokens,
                output_tokens=output_tokens,
                input_tokens=input_tokens
            )
        else:
            # 非流式模式
            payload = {
                "workflow_id": workflow_id,
                "parameters": parameters
            }
            
            if bot_id:
                payload["bot_id"] = bot_id
            
            try:
                response = requests.post(
                    self.non_stream_url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 解析响应（根据实际 API 响应格式调整）
                # 非流式响应格式可能与流式不同
                messages = []
                if 'data' in result:
                    # 假设返回格式类似流式
                    data = result['data']
                    msg = CozeMessage(
                        node_execute_uuid=data.get('node_execute_uuid', ''),
                        node_seq_id=data.get('node_seq_id', ''),
                        node_title=data.get('node_title', ''),
                        node_type=data.get('node_type', ''),
                        node_id=data.get('node_id', ''),
                        content=data.get('content', ''),
                        content_type=data.get('content_type', 'text'),
                        node_is_finish=True,
                        usage=data.get('usage')
                    )
                    messages.append(msg)
                
                return CozeResponse(
                    messages=messages,
                    debug_url=result.get('debug_url')
                )
                
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Coze 工作流调用失败: {str(e)}")
    
    def simple_run(
        self,
        workflow_id: str,
        input_text: str,
        stream: bool = True
    ) -> str:
        """
        简化调用接口，直接返回文本结果
        
        Args:
            workflow_id: 工作流 ID
            input_text: 输入文本
            stream: 是否使用流式
            
        Returns:
            str: 工作流输出文本
            
        Example:
            >>> client = CozeClient(api_key="xxx")
            >>> result = client.simple_run("workflow_id", "北京天气怎么样")
            >>> print(result)
        """
        response = self.run_workflow(
            workflow_id=workflow_id,
            parameters={"input": input_text},
            stream=stream
        )
        
        return response.get_final_output() or ""


# 便捷函数
def run_coze_workflow(
    workflow_id: str,
    input_text: str,
    api_key: Optional[str] = None,
    stream: bool = True
) -> str:
    """
    便捷函数：快速调用 Coze 工作流
    
    Args:
        workflow_id: 工作流 ID
        input_text: 输入文本
        api_key: API Key（可选，从环境变量读取）
        stream: 是否使用流式
        
    Returns:
        str: 工作流输出
        
    Example:
        >>> result = run_coze_workflow("7562785533798547507", "北京天气")
        >>> print(result)
    """
    client = CozeClient(api_key=api_key)
    return client.simple_run(workflow_id, input_text, stream)


# 测试代码
if __name__ == "__main__":
    import sys
    
    # 测试配置
    API_KEY = "pat_DCJgAjGAHRc4payGZnqtomuC3D9cQ0deeSbUpRevCej55Ux4ZaPmAYoURLQWDIJH"
    WORKFLOW_ID = "7562785533798547507"
    
    print("=" * 60)
    print("🧪 测试 Coze 工具类")
    print("=" * 60)
    
    # 测试 1: 流式调用
    print("\n📝 测试 1: 流式调用")
    print("-" * 60)
    
    try:
        client = CozeClient(api_key=API_KEY)
        
        print("🚀 开始流式调用...")
        for message in client.run_workflow_stream(
            workflow_id=WORKFLOW_ID,
            parameters={"input": "北京今天应该穿什么衣服"}
        ):
            output = message.get_output()
            if output:
                print(f"\n📤 节点 [{message.node_title}] 输出:")
                print(output)
                if message.usage:
                    print(f"   Token 统计: {message.usage}")
        
        print("\n✅ 流式调用测试完成")
    
    except Exception as e:
        print(f"❌ 流式调用失败: {e}")
    
    # 测试 2: 阻塞调用
    print("\n" + "=" * 60)
    print("📝 测试 2: 阻塞调用")
    print("-" * 60)
    
    try:
        client = CozeClient(api_key=API_KEY)
        
        print("🚀 开始阻塞调用...")
        response = client.run_workflow(
            workflow_id=WORKFLOW_ID,
            parameters={"input": "上海今天天气怎么样"},
            stream=True
        )
        
        print(f"\n📊 响应统计:")
        print(f"   消息数: {len(response.messages)}")
        print(f"   总 Token: {response.total_tokens}")
        print(f"   输入 Token: {response.input_tokens}")
        print(f"   输出 Token: {response.output_tokens}")
        
        print(f"\n📤 最终输出:")
        print(response.get_final_output())
        
        if response.debug_url:
            print(f"\n🔗 调试链接: {response.debug_url}")
        
        print("\n✅ 阻塞调用测试完成")
    
    except Exception as e:
        print(f"❌ 阻塞调用失败: {e}")
    
    # 测试 3: 简化调用
    print("\n" + "=" * 60)
    print("📝 测试 3: 简化调用")
    print("-" * 60)
    
    try:
        result = run_coze_workflow(
            workflow_id=WORKFLOW_ID,
            input_text="深圳今天需要带伞吗",
            api_key=API_KEY
        )
        
        print(f"📤 输出结果:")
        print(result)
        
        print("\n✅ 简化调用测试完成")
    
    except Exception as e:
        print(f"❌ 简化调用失败: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成")
    print("=" * 60)

