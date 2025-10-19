# 对话接口使用指南

## 概述

对话接口提供了基于知识库的智能问答功能，支持：
- ✅ RAG（检索增强生成）：结合向量搜索和图谱搜索
- ✅ 会话管理：多轮对话，自动维护上下文
- ✅ 滑动窗口：自动召回前5条历史消息
- ✅ SSE 流式响应：实时返回生成内容
- ✅ 上下文增强：知识库内容 + 实体关系

## 架构设计

### 数据模型

#### ChatSession（会话）
- 关联知识库
- 配置搜索参数（向量/图谱/Top-K）
- 统计信息（消息数、Token 数）

#### ChatMessage（消息）
- 角色：user/assistant/system
- 内容：问题和回答
- RAG 信息：检索的文本块和实体
- 统计：Token 数、处理时间

### 工作流程

```
用户消息
   ↓
1. 保存到数据库
   ↓
2. RAG 检索
   ├─ 向量搜索（语义相似）
   └─ 图谱搜索（实体关系）
   ↓
3. 获取历史消息（最近5条）
   ↓
4. 构建 Prompt
   ├─ System: 知识库信息 + 检索内容
   ├─ History: 最近5条对话
   └─ User: 当前问题
   ↓
5. 调用 OpenAI API
   ↓
6. 流式/非流式返回
   ↓
7. 保存助手回复
```

## API 端点

### 1. 会话管理

#### 创建会话
```bash
POST /api/v1/chat/sessions
```

**请求体**：
```json
{
  "knowledge_base_id": 1,
  "title": "我的第一次对话",
  "use_vector_search": true,
  "use_graph_search": true,
  "search_top_k": 5
}
```

**响应**：
```json
{
  "id": 1,
  "knowledge_base_id": 1,
  "title": "我的第一次对话",
  "summary": null,
  "use_vector_search": true,
  "use_graph_search": true,
  "search_top_k": 5,
  "message_count": 0,
  "total_tokens": 0,
  "created_at": "2025-10-19T10:00:00",
  "updated_at": "2025-10-19T10:00:00",
  "last_active_at": "2025-10-19T10:00:00"
}
```

#### 获取会话列表
```bash
GET /api/v1/chat/sessions?knowledge_base_id=1&skip=0&limit=50
```

#### 获取会话详情
```bash
GET /api/v1/chat/sessions/{session_id}
```

#### 更新会话配置
```bash
PATCH /api/v1/chat/sessions/{session_id}
```

**请求体**：
```json
{
  "title": "更新后的标题",
  "search_top_k": 10
}
```

#### 删除会话
```bash
DELETE /api/v1/chat/sessions/{session_id}
```

#### 获取会话历史
```bash
GET /api/v1/chat/sessions/{session_id}/history?limit=50
```

**响应**：
```json
{
  "session": {...},
  "messages": [
    {
      "id": 1,
      "session_id": 1,
      "role": "user",
      "content": "小明的父亲是谁？",
      "retrieved_chunks": [...],
      "retrieved_entities": [...],
      "context_used": "...",
      "token_count": 10,
      "processing_time": 1.234,
      "created_at": "2025-10-19T10:00:00"
    },
    {
      "id": 2,
      "session_id": 1,
      "role": "assistant",
      "content": "根据知识库的内容，小明的父亲是张三。",
      "token_count": 15,
      "processing_time": 1.234,
      "created_at": "2025-10-19T10:00:05"
    }
  ],
  "total": 2
}
```

### 2. 对话接口

#### 发送消息（流式 SSE）
```bash
POST /api/v1/chat/completions
```

**请求体**：
```json
{
  "session_id": 1,
  "message": "小明的父亲是谁？",
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**SSE 响应流**：
```
data: {"type": "context", "data": {"chunks": 3, "entities": 2}}

data: {"type": "chunk", "data": "根据"}

data: {"type": "chunk", "data": "知识库"}

data: {"type": "chunk", "data": "的内容"}

...

data: {"type": "done", "data": {"message_id": 2, "processing_time": 1.234}}
```

**事件类型**：
- `context`: 检索到的上下文信息（chunks、entities 数量）
- `chunk`: 生成的文本片段
- `error`: 错误信息
- `done`: 完成信号（包含 message_id 和处理时间）

#### 发送消息（非流式）
```bash
POST /api/v1/chat/completions
```

**请求体**：
```json
{
  "session_id": 1,
  "message": "小明的父亲是谁？",
  "stream": false,
  "temperature": 0.7
}
```

**响应**：
```json
{
  "message_id": 2,
  "content": "根据知识库的内容，小明的父亲是张三。这个信息来自文档《家庭关系》。",
  "retrieved_chunks": [
    {
      "chunk_id": 123,
      "document_id": 45,
      "content": "小明的父亲是张三，母亲是李四...",
      "score": 0.92
    }
  ],
  "retrieved_entities": [
    {
      "entity_name": "小明",
      "entity_type": "Person",
      "related_entities": [
        {
          "name": "张三",
          "type": "Person",
          "relation": "父亲"
        }
      ]
    }
  ],
  "processing_time": 1.234
}
```

## 使用示例

### Python 示例

#### 1. 创建会话并开始对话

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. 创建会话
session_response = requests.post(
    f"{BASE_URL}/chat/sessions",
    json={
        "knowledge_base_id": 1,
        "title": "家庭关系问答",
        "use_vector_search": True,
        "use_graph_search": True,
        "search_top_k": 5
    }
)
session = session_response.json()
session_id = session['id']
print(f"✅ 会话创建成功，ID: {session_id}")

# 2. 发送消息（流式）
response = requests.post(
    f"{BASE_URL}/chat/completions",
    json={
        "session_id": session_id,
        "message": "小明的父亲是谁？",
        "stream": True
    },
    stream=True
)

print("\n🤖 AI 回复：")
for line in response.iter_lines():
    if line:
        line_text = line.decode('utf-8')
        if line_text.startswith('data: '):
            data = json.loads(line_text[6:])
            
            if data['type'] == 'context':
                print(f"📚 检索到 {data['data']['chunks']} 个文档块，{data['data']['entities']} 个实体")
            
            elif data['type'] == 'chunk':
                print(data['data'], end='', flush=True)
            
            elif data['type'] == 'done':
                print(f"\n\n✅ 完成 (耗时: {data['data']['processing_time']:.2f}秒)")
            
            elif data['type'] == 'error':
                print(f"\n❌ 错误: {data['data']}")
```

#### 2. 多轮对话

```python
# 继续对话
messages = [
    "小明的父亲是谁？",
    "他的母亲呢？",
    "他们住在哪里？",
    "小明多大了？"
]

for msg in messages:
    print(f"\n👤 用户: {msg}")
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json={
            "session_id": session_id,
            "message": msg,
            "stream": True
        },
        stream=True
    )
    
    print("🤖 AI: ", end='')
    for line in response.iter_lines():
        if line:
            line_text = line.decode('utf-8')
            if line_text.startswith('data: '):
                data = json.loads(line_text[6:])
                if data['type'] == 'chunk':
                    print(data['data'], end='', flush=True)
    print()
```

#### 3. 查看会话历史

```python
# 获取完整对话历史
history_response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/history")
history = history_response.json()

print(f"\n📜 会话历史 (共 {history['total']} 条消息):")
print(f"标题: {history['session']['title']}")
print(f"消息数: {history['session']['message_count']}")
print(f"总 Token 数: {history['session']['total_tokens']}")

print("\n对话记录:")
for msg in history['messages']:
    role_icon = "👤" if msg['role'] == 'user' else "🤖"
    print(f"\n{role_icon} [{msg['created_at']}]")
    print(f"{msg['content'][:100]}...")
    
    if msg['role'] == 'assistant' and msg.get('retrieved_chunks'):
        print(f"  📚 使用了 {len(msg['retrieved_chunks'])} 个文档块")
```

### JavaScript/TypeScript 示例

#### 使用 EventSource（浏览器 SSE）

```javascript
// 创建会话
const createSession = async () => {
  const response = await fetch('/api/v1/chat/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      knowledge_base_id: 1,
      title: '新对话',
      use_vector_search: true,
      use_graph_search: true
    })
  });
  return await response.json();
};

// 流式对话
const chatStream = async (sessionId, message) => {
  // 注意：浏览器的 EventSource 不支持 POST，需要用 fetch stream
  const response = await fetch('/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    
    // 按行分割
    const lines = buffer.split('\n');
    buffer = lines.pop(); // 保留不完整的行
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === 'context') {
          console.log(`📚 检索到 ${data.data.chunks} 个文档块`);
        } else if (data.type === 'chunk') {
          // 显示文本片段
          document.getElementById('chat-output').textContent += data.data;
        } else if (data.type === 'done') {
          console.log(`✅ 完成 (${data.data.processing_time}秒)`);
        } else if (data.type === 'error') {
          console.error(`❌ 错误: ${data.data}`);
        }
      }
    }
  }
};

// 使用示例
(async () => {
  const session = await createSession();
  console.log('会话 ID:', session.id);
  
  await chatStream(session.id, '小明的父亲是谁？');
})();
```

### cURL 示例

#### 创建会话
```bash
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "title": "测试对话",
    "use_vector_search": true,
    "use_graph_search": true,
    "search_top_k": 5
  }'
```

#### 流式对话（SSE）
```bash
curl -N -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "message": "小明的父亲是谁？",
    "stream": true,
    "temperature": 0.7
  }'
```

**输出示例**：
```
data: {"type": "context", "data": {"chunks": 3, "entities": 2}}

data: {"type": "chunk", "data": "根据"}

data: {"type": "chunk", "data": "知识库"}

data: {"type": "chunk", "data": "的内容，小明的父亲是张三。"}

data: {"type": "done", "data": {"message_id": 2, "processing_time": 1.234}}
```

#### 非流式对话
```bash
curl -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "message": "小明的父亲是谁？",
    "stream": false
  }'
```

#### 查看会话历史
```bash
curl "http://localhost:8000/api/v1/chat/sessions/1/history?limit=20"
```

## 配置说明

### 环境变量

必须在 `.env` 文件中配置 OpenAI API：

```env
# OpenAI 配置（必需）
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，使用代理或其他兼容服务
OPENAI_MODEL=gpt-4  # 或 gpt-3.5-turbo

# Ollama 配置（向量搜索）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Neo4j 配置（图谱搜索）
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

### 会话配置

创建会话时可以配置：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `use_vector_search` | 是否使用向量搜索 | true |
| `use_graph_search` | 是否使用图谱搜索 | false |
| `search_top_k` | 检索文档数量 | 5 |

### 对话参数

发送消息时可以调整：

| 参数 | 说明 | 默认值 | 范围 |
|------|------|--------|------|
| `stream` | 是否流式返回 | true | - |
| `temperature` | 生成温度（创造性） | 0.7 | 0-2 |
| `max_tokens` | 最大生成长度 | None | 1-4000 |

## RAG 检索策略

### 1. 仅向量搜索
```json
{
  "use_vector_search": true,
  "use_graph_search": false
}
```
**适用场景**：语义相似问题、模糊查询

### 2. 仅图谱搜索
```json
{
  "use_vector_search": false,
  "use_graph_search": true
}
```
**适用场景**：实体关系查询、精确问答

### 3. 混合搜索（推荐）
```json
{
  "use_vector_search": true,
  "use_graph_search": true
}
```
**适用场景**：复杂问题、需要全面理解

## 系统提示词（System Prompt）

系统会自动构建包含以下内容的提示词：

```
你是一个智能助手，基于提供的知识库内容回答用户问题。

知识库名称：{kb.name}
知识库描述：{kb.description}

回答要求：
1. 优先使用检索到的知识库内容回答
2. 如果知识库中没有相关信息，请诚实告知
3. 引用具体内容时注明来源
4. 回答要准确、简洁、有帮助

检索到的相关内容：
{context}
```

## 滑动窗口机制

每次对话自动召回**最近 5 条历史消息**：

```
[System Prompt + Context]
[历史消息 -5]
[历史消息 -4]
[历史消息 -3]
[历史消息 -2]
[历史消息 -1]
[当前用户消息]
```

这样可以：
- ✅ 保持上下文连贯性
- ✅ 支持多轮对话
- ✅ 控制 Token 消耗

## 性能优化建议

### 1. 控制检索数量
```json
{
  "search_top_k": 3  // 减少到 3 可以加快响应
}
```

### 2. 调整温度参数
```json
{
  "temperature": 0.3  // 降低温度提高准确性
}
```

### 3. 限制生成长度
```json
{
  "max_tokens": 500  // 限制回答长度
}
```

### 4. 选择合适的模型
```env
OPENAI_MODEL=gpt-3.5-turbo  # 更快但稍弱
# OPENAI_MODEL=gpt-4  # 更强但较慢
```

## 错误处理

### 常见错误

#### 1. 会话不存在
```json
{
  "detail": "会话 999 不存在"
}
```

#### 2. 知识库不存在
```json
{
  "detail": "知识库 999 不存在"
}
```

#### 3. OpenAI API 未配置
```
data: {"type": "error", "data": "未设置 OPENAI_API_KEY"}
```

#### 4. API 调用失败
```
data: {"type": "error", "data": "OpenAI API 错误: Rate limit exceeded"}
```

## 完整示例：构建聊天界面

### 简单的命令行聊天

```python
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def create_chat_session(kb_id):
    """创建会话"""
    response = requests.post(
        f"{BASE_URL}/chat/sessions",
        json={
            "knowledge_base_id": kb_id,
            "title": "命令行对话",
            "use_vector_search": True,
            "use_graph_search": True
        }
    )
    return response.json()['id']

def chat(session_id, message):
    """发送消息并接收流式响应"""
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json={
            "session_id": session_id,
            "message": message,
            "stream": True
        },
        stream=True
    )
    
    print("🤖 AI: ", end='', flush=True)
    
    for line in response.iter_lines():
        if line:
            line_text = line.decode('utf-8')
            if line_text.startswith('data: '):
                data = json.loads(line_text[6:])
                
                if data['type'] == 'chunk':
                    print(data['data'], end='', flush=True)
                elif data['type'] == 'done':
                    print(f"\n(耗时: {data['data']['processing_time']:.2f}秒)\n")
                elif data['type'] == 'error':
                    print(f"\n❌ 错误: {data['data']}\n")

def main():
    print("=" * 60)
    print("RAG 智能对话系统")
    print("=" * 60)
    
    # 创建会话
    kb_id = int(input("请输入知识库 ID: "))
    session_id = create_chat_session(kb_id)
    print(f"✅ 会话已创建 (ID: {session_id})")
    print("输入 'exit' 或 'quit' 退出\n")
    
    # 对话循环
    while True:
        try:
            user_input = input("👤 您: ").strip()
            
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("再见！")
                break
            
            if not user_input:
                continue
            
            chat(session_id, user_input)
            
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")

if __name__ == "__main__":
    main()
```

运行：
```bash
python chat_client.py
```

## 总结

对话接口的核心特性：

✅ **RAG 增强**：结合向量搜索和图谱搜索，提供准确的知识库问答  
✅ **会话管理**：支持多会话、多轮对话  
✅ **滑动窗口**：自动维护上下文（最近5条消息）  
✅ **SSE 流式**：实时显示生成内容，提升用户体验  
✅ **灵活配置**：可调整搜索策略、生成参数  
✅ **详细记录**：保存检索内容、Token 统计、处理时间  

开始使用，构建您的智能问答系统！🚀

