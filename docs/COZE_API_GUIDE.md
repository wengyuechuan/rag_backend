# Coze 工作流 API 文档

## 📖 概述

Coze 工作流 API 提供了调用 Coze AI 工作流的 RESTful 接口，支持流式和非流式两种模式。

**基础 URL**: `http://localhost:8000/api/v1/coze`

## 🔧 配置

在 `.env` 文件中配置：

```env
# 必需
COZE_API_KEY=pat_xxxxxxxxxxxxx

# 可选
COZE_BASE_URL=https://api.coze.cn
COZE_WORKFLOW_ID=7562785533798547507  # 默认工作流 ID
```

## 📚 API 端点

### 1. 获取配置状态

**GET** `/api/v1/coze/config`

获取 Coze 配置状态，检查 API Key 和工作流是否已配置。

**响应示例**:
```json
{
  "configured": true,
  "api_key": "pat_DCJG...",
  "base_url": "https://api.coze.cn",
  "default_workflow_id": "7562785533798547507",
  "status": "可用"
}
```

**测试命令**:
```bash
curl http://localhost:8000/api/v1/coze/config
```

---

### 2. 运行工作流（非流式）

**POST** `/api/v1/coze/workflow/run`

调用指定的 Coze 工作流，返回完整结果。

**请求体**:
```json
{
  "workflow_id": "7562785533798547507",
  "input_text": "北京今天应该穿什么衣服",
  "parameters": {
    "custom_param": "value"
  },
  "bot_id": "optional_bot_id",
  "stream": false
}
```

**参数说明**:
- `workflow_id` (必需): 工作流 ID
- `input_text` (必需): 输入文本
- `parameters` (可选): 额外参数，会与 `{"input": input_text}` 合并
- `bot_id` (可选): Bot ID
- `stream` (可选): 是否流式，默认 false

**响应示例**:
```json
{
  "workflow_id": "7562785533798547507",
  "input_text": "北京今天应该穿什么衣服",
  "output": "今天北京天气晴朗，但气温较低且有风...",
  "messages": [
    {
      "node_execute_uuid": "",
      "node_seq_id": "0",
      "node_title": "End",
      "node_type": "End",
      "node_id": "900001",
      "content": "{\"output\":\"...\"}",
      "content_type": "text",
      "node_is_finish": true,
      "usage": {
        "token_count": 1421,
        "output_count": 169,
        "input_count": 1252
      },
      "output": "今天北京天气晴朗..."
    }
  ],
  "total_tokens": 1421,
  "input_tokens": 1252,
  "output_tokens": 169,
  "debug_url": "https://www.coze.cn/work_flow?execute_id=xxx",
  "processing_time": 3.45
}
```

**测试命令**:
```bash
curl -X POST http://localhost:8000/api/v1/coze/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "7562785533798547507",
    "input_text": "北京今天应该穿什么衣服"
  }'
```

---

### 3. 运行工作流（流式）

**POST** `/api/v1/coze/workflow/stream`

使用 SSE (Server-Sent Events) 流式返回工作流执行结果。

**请求体**: 与非流式接口相同

**响应格式** (SSE):
```
data: {"event": "start", "workflow_id": "7562785533798547507"}

data: {"event": "message", "node_title": "开始", "node_type": "Start", "output": null, "node_is_finish": false}

data: {"event": "message", "node_title": "End", "node_type": "End", "output": "今天北京天气晴朗...", "node_is_finish": true, "usage": {"token_count": 1421}}

data: {"event": "done", "output": "今天北京天气晴朗...", "total_tokens": 1421, "input_tokens": 1252, "output_tokens": 169, "debug_url": "https://..."}
```

**事件类型**:
- `start`: 开始执行
- `message`: 节点消息
- `done`: 执行完成
- `error`: 发生错误

**测试命令**:
```bash
curl -X POST http://localhost:8000/api/v1/coze/workflow/stream \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "7562785533798547507",
    "input_text": "北京今天应该穿什么衣服"
  }'
```

**Python 示例**:
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/api/v1/coze/workflow/stream",
    json={
        "workflow_id": "7562785533798547507",
        "input_text": "北京今天应该穿什么衣服"
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line_text = line.decode('utf-8')
        if line_text.startswith('data: '):
            data = json.loads(line_text[6:])
            print(f"事件: {data.get('event')}")
            if data.get('output'):
                print(f"输出: {data['output']}")
```

---

### 4. 简化接口（非流式）

**POST** `/api/v1/coze/simple`

使用环境变量中配置的默认工作流 ID (`COZE_WORKFLOW_ID`)。

**请求体**:
```json
{
  "input_text": "深圳今天需要带伞吗",
  "stream": false
}
```

**参数说明**:
- `input_text` (必需): 输入文本
- `stream` (可选): 是否流式

**响应**: 与完整接口相同

**测试命令**:
```bash
curl -X POST http://localhost:8000/api/v1/coze/simple \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "深圳今天需要带伞吗"
  }'
```

---

### 5. 简化接口（流式）

**POST** `/api/v1/coze/simple/stream`

使用默认工作流 ID，流式返回结果。

**请求体**: 与简化非流式接口相同

**响应**: SSE 流式响应

**测试命令**:
```bash
curl -X POST http://localhost:8000/api/v1/coze/simple/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "广州今天天气如何"
  }'
```

---

## 💡 使用示例

### Python (requests)

```python
import requests
import json

# 1. 非流式调用
response = requests.post(
    "http://localhost:8000/api/v1/coze/workflow/run",
    json={
        "workflow_id": "7562785533798547507",
        "input_text": "北京今天应该穿什么衣服"
    }
)

result = response.json()
print(result['output'])

# 2. 流式调用
response = requests.post(
    "http://localhost:8000/api/v1/coze/workflow/stream",
    json={
        "workflow_id": "7562785533798547507",
        "input_text": "上海今天天气怎么样"
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line_text = line.decode('utf-8')
        if line_text.startswith('data: '):
            data = json.loads(line_text[6:])
            if data.get('event') == 'message' and data.get('output'):
                print(f"节点输出: {data['output']}")

# 3. 简化接口
response = requests.post(
    "http://localhost:8000/api/v1/coze/simple",
    json={"input_text": "深圳今天需要带伞吗"}
)

result = response.json()
print(result['output'])
```

### JavaScript (fetch)

```javascript
// 1. 非流式调用
fetch('http://localhost:8000/api/v1/coze/workflow/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    workflow_id: '7562785533798547507',
    input_text: '北京今天应该穿什么衣服'
  })
})
.then(response => response.json())
.then(data => {
  console.log('输出:', data.output);
  console.log('Token:', data.total_tokens);
});

// 2. 流式调用 (EventSource)
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/coze/workflow/stream?' + 
  new URLSearchParams({
    workflow_id: '7562785533798547507',
    input_text: '上海今天天气怎么样'
  })
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('事件:', data.event);
  if (data.output) {
    console.log('输出:', data.output);
  }
};

eventSource.onerror = (error) => {
  console.error('错误:', error);
  eventSource.close();
};
```

### cURL

```bash
# 1. 检查配置
curl http://localhost:8000/api/v1/coze/config

# 2. 非流式调用
curl -X POST http://localhost:8000/api/v1/coze/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "7562785533798547507",
    "input_text": "北京今天应该穿什么衣服"
  }'

# 3. 流式调用
curl -X POST http://localhost:8000/api/v1/coze/workflow/stream \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "7562785533798547507",
    "input_text": "上海今天天气怎么样"
  }'

# 4. 简化接口
curl -X POST http://localhost:8000/api/v1/coze/simple \
  -H "Content-Type: application/json" \
  -d '{"input_text": "深圳今天需要带伞吗"}'
```

---

## 🔍 错误处理

### 错误响应格式

```json
{
  "detail": "错误信息"
}
```

### 常见错误

| 状态码 | 错误 | 解决方案 |
|--------|------|----------|
| 400 | 未配置 COZE_API_KEY | 在 .env 文件中设置 |
| 400 | 未配置默认工作流 ID | 在 .env 文件中设置 COZE_WORKFLOW_ID 或在请求中提供 workflow_id |
| 502 | Coze API 调用失败 | 检查网络连接和 API Key 是否正确 |
| 500 | 服务器错误 | 查看服务器日志 |

### 流式响应中的错误

```json
data: {"event": "error", "error": "错误信息"}
```

---

## 📊 性能建议

1. **批量请求**: 使用非流式接口处理批量请求，避免频繁建立 SSE 连接
2. **超时设置**: 建议设置 60 秒以上的超时时间
3. **错误重试**: 实现指数退避重试机制
4. **Token 监控**: 监控 Token 使用量，避免超出配额

---

## 🔗 相关资源

- [Coze 工具类文档](COZE_GUIDE.md)
- [完整 API 文档](API_DOCUMENTATION.md)
- [测试脚本](../test_coze_api.py)

---

## 📝 更新日志

### v1.0.0 (2025-10-19)
- ✅ 实现完整的工作流调用接口
- ✅ 支持流式和非流式两种模式
- ✅ 提供简化接口
- ✅ 完整的错误处理
- ✅ SSE 流式响应

