# Coze 工作流集成指南

## 📖 简介

Coze 是一个强大的 AI 工作流平台。本项目已集成 Coze API，支持调用自定义工作流。

## 🚀 快速开始

### 1. 配置 API Key

在 `.env` 文件中添加 Coze API Key：

```env
# Coze 配置
COZE_API_KEY=pat_xxxxxxxxxxxxx
COZE_WORKFLOW_ID=7562785533798547507  # 可选
```

### 2. 基础使用

#### 方式 1：便捷函数（推荐）

```python
from utils.coze import run_coze_workflow

# 快速调用
result = run_coze_workflow(
    workflow_id="7562785533798547507",
    input_text="北京今天应该穿什么衣服"
)

print(result)
```

#### 方式 2：使用客户端类

```python
from utils.coze import CozeClient

# 初始化客户端
client = CozeClient(api_key="your_api_key")

# 阻塞调用
response = client.run_workflow(
    workflow_id="7562785533798547507",
    parameters={"input": "北京今天应该穿什么衣服"},
    stream=True
)

# 获取结果
print(response.get_final_output())
print(f"使用 Token: {response.total_tokens}")
```

#### 方式 3：流式调用（实时输出）

```python
from utils.coze import CozeClient

client = CozeClient(api_key="your_api_key")

# 流式调用，实时获取每个节点的输出
for message in client.run_workflow_stream(
    workflow_id="7562785533798547507",
    parameters={"input": "北京今天应该穿什么衣服"}
):
    # 获取当前节点输出
    output = message.get_output()
    if output:
        print(f"[{message.node_title}] {output}")
        
        # 显示 token 使用情况
        if message.usage:
            print(f"  Token: {message.usage['token_count']}")
```

## 📚 API 文档

### CozeClient

#### 初始化

```python
client = CozeClient(
    api_key="your_api_key",  # 可选，默认从环境变量读取
    base_url="https://api.coze.cn",  # 可选
    timeout=60  # 超时时间（秒）
)
```

#### 方法

##### 1. `run_workflow_stream()`

流式调用工作流，返回生成器。

```python
for message in client.run_workflow_stream(
    workflow_id="workflow_id",
    parameters={"input": "your input"},
    bot_id="bot_id"  # 可选
):
    print(message.get_output())
```

**参数**：
- `workflow_id` (str): 工作流 ID
- `parameters` (dict): 工作流参数
- `bot_id` (str, 可选): Bot ID

**返回**：生成器，yield `CozeMessage` 对象

##### 2. `run_workflow()`

阻塞调用工作流，返回完整响应。

```python
response = client.run_workflow(
    workflow_id="workflow_id",
    parameters={"input": "your input"},
    bot_id="bot_id",  # 可选
    stream=True  # 是否使用流式内部处理
)
```

**参数**：
- `workflow_id` (str): 工作流 ID
- `parameters` (dict): 工作流参数
- `bot_id` (str, 可选): Bot ID
- `stream` (bool): 是否使用流式

**返回**：`CozeResponse` 对象

##### 3. `simple_run()`

简化接口，直接返回文本结果。

```python
result = client.simple_run(
    workflow_id="workflow_id",
    input_text="your input",
    stream=True
)
```

**参数**：
- `workflow_id` (str): 工作流 ID
- `input_text` (str): 输入文本
- `stream` (bool): 是否使用流式

**返回**：输出文本 (str)

### CozeMessage

表示工作流中一个节点的消息。

**属性**：
- `node_execute_uuid` (str): 节点执行 UUID
- `node_seq_id` (str): 节点序列 ID
- `node_title` (str): 节点标题
- `node_type` (str): 节点类型
- `node_id` (str): 节点 ID
- `content` (str): 内容（可能是 JSON 字符串）
- `content_type` (str): 内容类型
- `node_is_finish` (bool): 节点是否完成
- `usage` (dict, 可选): Token 使用统计

**方法**：
- `get_output()`: 从 content 中提取 output 字段

### CozeResponse

表示完整的工作流响应。

**属性**：
- `messages` (List[CozeMessage]): 所有消息列表
- `debug_url` (str, 可选): 调试链接
- `total_tokens` (int): 总 Token 数
- `output_tokens` (int): 输出 Token 数
- `input_tokens` (int): 输入 Token 数

**方法**：
- `get_final_output()`: 获取最终输出（End 节点）
- `get_all_outputs()`: 获取所有节点的输出列表

## 🎯 使用场景

### 场景 1：天气查询

```python
from utils.coze import CozeClient

client = CozeClient()

# 查询天气并获取穿衣建议
result = client.simple_run(
    workflow_id="7562785533798547507",
    input_text="北京今天应该穿什么衣服"
)

print(result)
# 输出: 今天北京天气晴朗，但气温较低且有风，出行时建议穿着厚外套...
```

### 场景 2：与 RAG 系统集成

```python
from utils.coze import CozeClient
from api.services.document_service import document_service

def enhanced_search(query: str, kb_id: int) -> str:
    """使用 Coze 增强的搜索"""
    
    # 1. 先从知识库检索
    results = document_service.search_documents(
        db=db,
        kb_id=kb_id,
        query=query,
        top_k=3
    )
    
    # 2. 构建上下文
    context = "\n\n".join([chunk.content for chunk, score in results])
    
    # 3. 使用 Coze 工作流处理
    coze_client = CozeClient()
    enhanced_result = coze_client.simple_run(
        workflow_id="your_workflow_id",
        input_text=f"基于以下内容回答问题：\n\n{context}\n\n问题：{query}"
    )
    
    return enhanced_result
```

### 场景 3：批量处理

```python
from utils.coze import CozeClient

client = CozeClient()

questions = [
    "北京今天天气怎么样",
    "上海今天天气怎么样",
    "深圳今天天气怎么样"
]

for question in questions:
    result = client.simple_run(
        workflow_id="7562785533798547507",
        input_text=question
    )
    print(f"问题: {question}")
    print(f"回答: {result}\n")
```

### 场景 4：流式输出到前端

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from utils.coze import CozeClient

app = FastAPI()

@app.get("/api/coze/stream")
async def coze_stream(query: str):
    """流式返回 Coze 工作流结果"""
    
    def generate():
        client = CozeClient()
        for message in client.run_workflow_stream(
            workflow_id="7562785533798547507",
            parameters={"input": query}
        ):
            output = message.get_output()
            if output:
                yield f"data: {output}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## 🔧 高级用法

### 1. 自定义参数

```python
response = client.run_workflow(
    workflow_id="workflow_id",
    parameters={
        "input": "用户输入",
        "custom_param_1": "自定义参数1",
        "custom_param_2": 123,
        "custom_param_3": True
    }
)
```

### 2. 错误处理

```python
from utils.coze import CozeClient

try:
    client = CozeClient(api_key="your_key")
    result = client.simple_run(
        workflow_id="workflow_id",
        input_text="input"
    )
except ValueError as e:
    print(f"配置错误: {e}")
except RuntimeError as e:
    print(f"调用失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 3. 获取详细信息

```python
response = client.run_workflow(
    workflow_id="workflow_id",
    parameters={"input": "input"}
)

# 所有节点的输出
all_outputs = response.get_all_outputs()
for i, output in enumerate(all_outputs):
    print(f"节点 {i+1}: {output}")

# Token 统计
print(f"总 Token: {response.total_tokens}")
print(f"输入 Token: {response.input_tokens}")
print(f"输出 Token: {response.output_tokens}")

# 调试链接
if response.debug_url:
    print(f"调试链接: {response.debug_url}")
```

### 4. 从环境变量读取配置

```python
import os
from utils.coze import run_coze_workflow

# .env 文件中设置
# COZE_API_KEY=pat_xxxxx
# COZE_WORKFLOW_ID=7562785533798547507

result = run_coze_workflow(
    workflow_id=os.getenv("COZE_WORKFLOW_ID"),
    input_text="北京天气"
)
```

## 📊 响应格式

### 流式响应 (SSE)

```
event: Message
data: {"node_title":"开始","content":"{\"output\":\"处理中...\"}","node_is_finish":false}

event: Message  
data: {"node_title":"End","content":"{\"output\":\"最终结果\"}","node_is_finish":true,"usage":{"token_count":100}}

event: Done
data: {"debug_url":"https://www.coze.cn/work_flow?execute_id=xxx"}
```

### 解析后的对象

```python
# CozeMessage
{
    "node_title": "End",
    "node_type": "End",
    "content": '{"output":"最终结果"}',
    "node_is_finish": True,
    "usage": {
        "token_count": 1421,
        "output_count": 169,
        "input_count": 1252
    }
}

# CozeResponse
{
    "messages": [CozeMessage, ...],
    "total_tokens": 1421,
    "output_tokens": 169,
    "input_tokens": 1252,
    "debug_url": "https://..."
}
```

## 🐛 故障排查

### 问题 1: API Key 未设置

**错误**：
```
ValueError: 未设置 Coze API Key
```

**解决方案**：
1. 在代码中直接传入：
   ```python
   client = CozeClient(api_key="your_key")
   ```

2. 或设置环境变量：
   ```bash
   export COZE_API_KEY=your_key
   ```

### 问题 2: 请求超时

**错误**：
```
RuntimeError: Coze 工作流调用失败: timeout
```

**解决方案**：
```python
# 增加超时时间
client = CozeClient(timeout=120)
```

### 问题 3: 工作流 ID 错误

**错误**：
```
HTTP 404 或其他错误
```

**解决方案**：
- 检查工作流 ID 是否正确
- 确认工作流已发布
- 检查 API Key 权限

### 问题 4: 无输出结果

**可能原因**：
- 工作流没有 End 节点
- content 字段格式不正确

**解决方案**：
```python
# 获取所有节点输出
response = client.run_workflow(...)
all_outputs = response.get_all_outputs()
print(all_outputs)

# 或查看所有消息
for msg in response.messages:
    print(f"{msg.node_title}: {msg.content}")
```

## 💡 最佳实践

### 1. 使用环境变量

```env
# .env
COZE_API_KEY=pat_xxxxx
COZE_DEFAULT_WORKFLOW=7562785533798547507
```

```python
import os
from utils.coze import CozeClient

client = CozeClient()  # 自动从环境变量读取
workflow_id = os.getenv("COZE_DEFAULT_WORKFLOW")
```

### 2. 封装业务逻辑

```python
# services/coze_service.py
from utils.coze import CozeClient

class CozeService:
    def __init__(self):
        self.client = CozeClient()
        self.weather_workflow = "7562785533798547507"
    
    def get_weather_advice(self, city: str) -> str:
        """获取天气穿衣建议"""
        return self.client.simple_run(
            workflow_id=self.weather_workflow,
            input_text=f"{city}今天应该穿什么衣服"
        )

# 使用
service = CozeService()
advice = service.get_weather_advice("北京")
```

### 3. 缓存结果

```python
from functools import lru_cache
from utils.coze import CozeClient

@lru_cache(maxsize=100)
def cached_coze_call(workflow_id: str, input_text: str) -> str:
    """带缓存的 Coze 调用"""
    client = CozeClient()
    return client.simple_run(workflow_id, input_text)
```

### 4. 异步调用

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from utils.coze import CozeClient

async def async_coze_call(input_text: str) -> str:
    """异步 Coze 调用"""
    client = CozeClient()
    loop = asyncio.get_event_loop()
    
    # 在线程池中执行同步调用
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            client.simple_run,
            "workflow_id",
            input_text
        )
    
    return result

# 使用
result = await async_coze_call("北京天气")
```

## 📚 相关资源

- [Coze 官方文档](https://www.coze.cn/docs)
- [Coze API 文档](https://www.coze.cn/docs/developer_guides/coze_api_overview)
- [本项目 API 文档](API_DOCUMENTATION.md)

## ✅ 总结

Coze 工具类提供了：
- ✅ 简单易用的 API
- ✅ 流式和非流式两种模式
- ✅ 完整的类型提示
- ✅ 灵活的配置选项
- ✅ 详细的错误处理
- ✅ 与现有系统的良好集成

开始使用 Coze，为您的 RAG 系统增添更强大的 AI 能力！🚀

