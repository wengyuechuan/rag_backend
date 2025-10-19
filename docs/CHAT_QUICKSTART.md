# 对话功能快速启动指南

## 🎯 功能概述

刚刚实现的对话接口提供了完整的 RAG（检索增强生成）智能问答功能：

✅ **会话管理**：多会话、多轮对话支持  
✅ **RAG 检索**：向量搜索 + 图谱搜索（可配置）  
✅ **滑动窗口**：自动召回前5条历史消息  
✅ **SSE 流式**：实时返回生成内容  
✅ **OpenAI 集成**：使用 OpenAI SDK 调用 GPT 模型  

## 📁 新增文件

### 1. 数据库模型
- `database/models.py`
  - `MessageRoleEnum`: 消息角色枚举
  - `ChatSession`: 会话模型
  - `ChatMessage`: 消息模型

### 2. API Schemas
- `api/schemas.py`
  - `ChatSessionCreate/Update/Response`
  - `ChatMessageResponse`
  - `ChatRequest`
  - `ChatHistoryResponse`

### 3. 路由
- `api/routers/chat.py`
  - 会话管理端点（创建、列表、更新、删除）
  - 对话端点（流式/非流式）
  - 历史记录端点

### 4. 文档
- `docs/CHAT_API_GUIDE.md`: 完整 API 使用指南
- `docs/CHAT_QUICKSTART.md`: 快速启动指南（本文件）

### 5. 测试脚本
- `test_chat.py`: 对话接口测试脚本

## 🚀 快速开始

### 步骤 1: 配置环境变量

确保 `.env` 文件包含 OpenAI 配置：

```env
# OpenAI 配置（必需）
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Ollama 配置（向量搜索）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Neo4j 配置（图谱搜索，可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

### 步骤 2: 初始化数据库

新的会话和消息表会在启动时自动创建：

```bash
# 删除旧数据库（可选，如果需要重新开始）
rm rag_backend.db

# 启动服务器（会自动创建新表）
python main.py
```

### 步骤 3: 准备知识库

确保至少有一个知识库和一些文档：

```bash
# 创建知识库
curl -X POST "http://localhost:8000/api/v1/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试知识库",
    "description": "用于测试对话功能",
    "enable_vector_store": true,
    "enable_ner": true,
    "enable_knowledge_graph": true
  }'

# 上传文档
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@test.txt" \
  -F "knowledge_base_id=1" \
  -F "title=测试文档" \
  -F "auto_process=true"
```

### 步骤 4: 测试对话功能

运行测试脚本：

```bash
python test_chat.py
```

或手动测试：

```bash
# 1. 创建会话
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": 1,
    "title": "我的第一次对话",
    "use_vector_search": true,
    "use_graph_search": true
  }'

# 2. 发送消息（流式）
curl -N -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "message": "小明的父亲是谁？",
    "stream": true
  }'

# 3. 查看历史
curl "http://localhost:8000/api/v1/chat/sessions/1/history"
```

## 📊 数据库结构

### ChatSession 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| knowledge_base_id | Integer | 关联知识库 |
| title | String | 会话标题 |
| use_vector_search | Boolean | 是否使用向量搜索 |
| use_graph_search | Boolean | 是否使用图谱搜索 |
| search_top_k | Integer | 检索数量 |
| message_count | Integer | 消息数量 |
| total_tokens | Integer | 总 Token 数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| last_active_at | DateTime | 最后活跃时间 |

### ChatMessage 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| session_id | Integer | 关联会话 |
| role | Enum | 角色（user/assistant/system） |
| content | Text | 消息内容 |
| retrieved_chunks | JSON | 检索到的文档块 |
| retrieved_entities | JSON | 检索到的实体 |
| context_used | Text | 使用的上下文 |
| token_count | Integer | Token 数量 |
| processing_time | Float | 处理时间（秒） |
| created_at | DateTime | 创建时间 |

## 🔍 核心实现

### 1. RAG 检索流程

```python
# 在 chat.py 中
async def chat_stream_generator(...):
    # 1. 向量搜索
    if session.use_vector_search:
        chunks_with_scores = document_service.search_documents(
            db=db,
            kb_id=kb.id,
            query=chat_req.message,
            top_k=session.search_top_k
        )
    
    # 2. 图谱搜索
    if session.use_graph_search:
        graph_results = document_service.search_graph(
            db=db,
            kb_id=kb.id,
            query=chat_req.message,
            top_k=session.search_top_k
        )
```

### 2. 滑动窗口上下文

```python
# 获取最近 5 条历史消息
history_messages = db.query(ChatMessage).filter(
    ChatMessage.session_id == session.id,
    ChatMessage.id < user_message.id
).order_by(ChatMessage.created_at.desc()).limit(5).all()

history_messages.reverse()  # 时间顺序
```

### 3. SSE 流式输出

```python
# 发送上下文
yield f"data: {json.dumps({'type': 'context', 'data': {...}})}\n\n"

# 流式生成
for chunk in stream:
    if chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        yield f"data: {json.dumps({'type': 'chunk', 'data': content})}\n\n"

# 完成信号
yield f"data: {json.dumps({'type': 'done', 'data': {...}})}\n\n"
```

### 4. System Prompt 构建

```python
system_prompt = f"""你是一个智能助手，基于提供的知识库内容回答用户问题。

知识库名称：{kb.name}
知识库描述：{kb.description}

回答要求：
1. 优先使用检索到的知识库内容回答
2. 如果知识库中没有相关信息，请诚实告知
3. 引用具体内容时注明来源
4. 回答要准确、简洁、有帮助

检索到的相关内容：
{context_text}
"""
```

## 🎨 前端集成示例

### React + EventSource

```tsx
import { useState, useEffect } from 'react';

function ChatComponent({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (message: string) => {
    setIsLoading(true);
    
    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    
    // 准备助手消息
    let assistantContent = '';
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
    
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
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          
          if (data.type === 'chunk') {
            assistantContent += data.data;
            setMessages(prev => {
              const newMessages = [...prev];
              newMessages[newMessages.length - 1].content = assistantContent;
              return newMessages;
            });
          } else if (data.type === 'done') {
            setIsLoading(false);
          }
        }
      }
    }
  };

  return (
    <div>
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
      
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyPress={e => {
          if (e.key === 'Enter' && !isLoading) {
            sendMessage(input);
            setInput('');
          }
        }}
        disabled={isLoading}
      />
    </div>
  );
}
```

## 📝 API 端点总览

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/sessions` | 创建会话 |
| GET | `/api/v1/chat/sessions` | 获取会话列表 |
| GET | `/api/v1/chat/sessions/{id}` | 获取会话详情 |
| PATCH | `/api/v1/chat/sessions/{id}` | 更新会话 |
| DELETE | `/api/v1/chat/sessions/{id}` | 删除会话 |
| GET | `/api/v1/chat/sessions/{id}/history` | 获取会话历史 |

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/completions` | 发送消息（支持流式/非流式） |

## 🔧 故障排查

### 问题 1: "未设置 OPENAI_API_KEY"

**解决方案**：
```bash
# 检查 .env 文件
cat .env | grep OPENAI_API_KEY

# 或在代码中检查
curl http://localhost:8000/config
```

### 问题 2: "会话 X 不存在"

**解决方案**：
```bash
# 检查会话是否存在
curl http://localhost:8000/api/v1/chat/sessions

# 创建新会话
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{"knowledge_base_id": 1}'
```

### 问题 3: SSE 连接中断

**原因**：某些代理服务器不支持 SSE

**解决方案**：
- 使用非流式模式：`"stream": false`
- 或配置代理支持 SSE

### 问题 4: 检索不到文档

**检查清单**：
1. 知识库是否有文档？
2. 文档是否处理完成？
3. 向量搜索是否启用？
4. Ollama 服务是否运行？

```bash
# 检查知识库
curl http://localhost:8000/api/v1/knowledge-bases/1

# 检查文档
curl http://localhost:8000/api/v1/documents?knowledge_base_id=1
```

## 🎯 下一步

1. **添加用户认证**：为每个用户隔离会话
2. **会话摘要**：自动生成会话标题和摘要
3. **引用标注**：在回答中标注引用来源
4. **多模态支持**：支持图片、文件上传
5. **导出功能**：导出会话历史为 Markdown/PDF

## 📚 相关文档

- [完整 API 文档](./CHAT_API_GUIDE.md)
- [图谱搜索指南](./GRAPH_SEARCH_GUIDE.md)
- [FastAPI 文档](http://localhost:8000/docs)

## 🎉 总结

✅ **完整的对话系统**：从会话管理到 RAG 检索，再到流式响应  
✅ **灵活的配置**：可调整搜索策略、生成参数  
✅ **详细的记录**：保存检索内容、统计信息  
✅ **易于集成**：标准 RESTful API + SSE  

开始构建您的智能问答应用吧！🚀

