# Coze 工作流 API 集成总结

## 📦 完成内容

本次更新为 RAG 系统添加了完整的 Coze 工作流集成，包括工具类和 RESTful API 接口。

---

## ✅ 新增文件

### 1. 核心工具类
- **`utils/coze.py`** (464 行)
  - `CozeClient` 类：完整的 Coze API 客户端
  - `CozeMessage` 和 `CozeResponse` 数据模型
  - 支持流式和非流式调用
  - 完整的错误处理和 Token 统计

### 2. API 路由
- **`api/routers/coze.py`** (335 行)
  - `/api/v1/coze/config` - 配置状态查询
  - `/api/v1/coze/workflow/run` - 非流式工作流调用
  - `/api/v1/coze/workflow/stream` - 流式工作流调用
  - `/api/v1/coze/simple` - 简化接口（非流式）
  - `/api/v1/coze/simple/stream` - 简化接口（流式）

### 3. 测试和示例
- **`test_coze_api.py`** (345 行) - 完整的 API 测试脚本
- **`example_coze_usage.py`** (155 行) - 工具类使用示例
- **`test_coze.py`** (153 行) - Coze 原始 API 测试

### 4. 文档
- **`docs/COZE_GUIDE.md`** - Coze 工具类使用指南
- **`docs/COZE_API_GUIDE.md`** - Coze API 接口文档
- **`COZE_API_SUMMARY.md`** (本文件) - 集成总结

---

## 🔧 修改的文件

### 1. 数据模型
**`api/schemas.py`**
- 添加 `CozeWorkflowRequest` - 工作流请求模型
- 添加 `CozeNodeMessage` - 节点消息模型
- 添加 `CozeWorkflowResponse` - 工作流响应模型
- 添加 `CozeSimpleRequest` - 简化请求模型

### 2. 主应用
**`main.py`**
- 导入并注册 `coze` 路由
- 添加 Coze 配置到启动日志
- 更新 `/config` 端点显示 Coze 状态

### 3. 模块导出
**`utils/__init__.py`**
- 导出 `CozeClient`, `CozeMessage`, `CozeResponse`, `run_coze_workflow`

### 4. 配置文件
**`config.example.env`**
```env
# 新增配置项
COZE_API_KEY=pat_xxxxxxxxxxxxx
COZE_BASE_URL=https://api.coze.cn
COZE_WORKFLOW_ID=7562785533798547507
```

### 5. 项目文档
**`README.md`**
- 添加 "AI 工作流集成" 功能说明
- 添加 Coze 配置示例
- 添加 Coze API 使用示例
- 更新系统架构图
- 添加文档链接

---

## 🚀 功能特性

### 1. 工具类功能
- ✅ 流式和非流式两种调用模式
- ✅ SSE 格式解析
- ✅ Token 使用统计
- ✅ 调试链接获取
- ✅ 环境变量配置
- ✅ 完整的错误处理
- ✅ 类型提示 (Type Hints)

### 2. API 接口功能
- ✅ RESTful API 设计
- ✅ 流式 SSE 响应
- ✅ 简化接口（使用默认工作流）
- ✅ 配置状态查询
- ✅ 完整的请求验证
- ✅ 详细的错误信息

### 3. 响应格式
**非流式响应**:
```json
{
  "workflow_id": "xxx",
  "input_text": "用户输入",
  "output": "最终输出",
  "messages": [...],
  "total_tokens": 1421,
  "input_tokens": 1252,
  "output_tokens": 169,
  "debug_url": "https://...",
  "processing_time": 3.45
}
```

**流式响应 (SSE)**:
```
data: {"event": "start", "workflow_id": "xxx"}
data: {"event": "message", "node_title": "节点", "output": "..."}
data: {"event": "done", "output": "最终输出", "total_tokens": 1421}
```

---

## 📖 使用方式

### 方式 1: Python 工具类
```python
from utils.coze import run_coze_workflow

result = run_coze_workflow(
    workflow_id="7562785533798547507",
    input_text="北京今天应该穿什么衣服"
)
print(result)
```

### 方式 2: HTTP API
```bash
curl -X POST http://localhost:8000/api/v1/coze/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "7562785533798547507",
    "input_text": "北京今天应该穿什么衣服"
  }'
```

### 方式 3: 简化接口
```bash
curl -X POST http://localhost:8000/api/v1/coze/simple \
  -H "Content-Type: application/json" \
  -d '{"input_text": "上海今天天气怎么样"}'
```

---

## 🔍 API 端点一览

| 端点 | 方法 | 功能 | 响应格式 |
|------|------|------|----------|
| `/api/v1/coze/config` | GET | 配置状态 | JSON |
| `/api/v1/coze/workflow/run` | POST | 运行工作流 | JSON |
| `/api/v1/coze/workflow/stream` | POST | 流式运行 | SSE |
| `/api/v1/coze/simple` | POST | 简化调用 | JSON |
| `/api/v1/coze/simple/stream` | POST | 简化流式 | SSE |

---

## 📊 代码统计

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| 核心工具类 | 1 | 464 |
| API 路由 | 1 | 335 |
| 测试脚本 | 3 | 653 |
| 文档 | 3 | ~2000 |
| **总计** | **8** | **~3452** |

---

## 🧪 测试

### 运行工具类测试
```bash
python utils/coze.py
```

### 运行 API 测试
```bash
# 启动服务
python main.py

# 新终端运行测试
python test_coze_api.py
```

### 测试覆盖
- ✅ 配置检查
- ✅ 非流式调用
- ✅ 流式调用
- ✅ 简化接口
- ✅ 批量请求
- ✅ 错误处理

---

## 📚 文档

1. **[Coze 工具类指南](docs/COZE_GUIDE.md)**
   - 快速开始
   - API 文档
   - 使用场景
   - 最佳实践

2. **[Coze API 接口文档](docs/COZE_API_GUIDE.md)**
   - 端点说明
   - 请求/响应格式
   - 代码示例
   - 错误处理

3. **[项目 README](README.md)**
   - 功能介绍
   - 配置说明
   - 快速开始

---

## 🎯 应用场景

### 1. 天气查询与建议
```python
result = run_coze_workflow(
    workflow_id="7562785533798547507",
    input_text="北京今天应该穿什么衣服"
)
# 输出: 今天北京天气晴朗，但气温较低且有风...
```

### 2. 与 RAG 系统结合
```python
# 1. 从知识库检索
context = search_documents(query)

# 2. 使用 Coze 增强回答
enhanced = run_coze_workflow(
    workflow_id="analysis_workflow",
    input_text=f"基于: {context}\n问题: {query}"
)
```

### 3. 批量文档处理
```python
for doc in documents:
    result = run_coze_workflow(
        workflow_id="summarize_workflow",
        input_text=doc.content
    )
    doc.summary = result
```

---

## 🔒 安全性

1. **API Key 保护**
   - 通过环境变量配置
   - 日志中自动隐藏敏感信息
   - 配置端点仅显示部分 Key

2. **错误处理**
   - 完整的异常捕获
   - 友好的错误信息
   - 不暴露内部细节

3. **请求验证**
   - Pydantic 模型验证
   - 参数类型检查
   - 必填字段验证

---

## ⚡ 性能

- **非流式**: 适合批量处理，单次返回完整结果
- **流式**: 适合实时交互，及时反馈处理进度
- **超时设置**: 默认 60 秒
- **Token 追踪**: 实时统计使用量

---

## 🔄 后续扩展

### 可能的增强功能
- [ ] 支持更多 Coze API 功能
- [ ] 添加工作流管理接口
- [ ] 实现结果缓存
- [ ] 添加异步调用支持
- [ ] 集成到对话系统

---

## 📝 总结

本次集成为 RAG 系统添加了完整的 Coze 工作流支持，包括：

1. ✅ **完整的工具类** - 支持流式和非流式调用
2. ✅ **RESTful API** - 5 个接口端点
3. ✅ **详细文档** - 工具类和 API 文档
4. ✅ **测试脚本** - 完整的测试覆盖
5. ✅ **配置集成** - 环境变量管理
6. ✅ **错误处理** - 完善的异常处理
7. ✅ **类型安全** - 完整的类型提示

现在您可以轻松地在项目中使用 Coze 工作流！🎉

---

**版本**: 1.0.0  
**日期**: 2025-10-19  
**作者**: RAG Backend Team

