"""
FastAPI 主应用
RAG 文档管理系统
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import os
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv

# 尝试从多个位置加载 .env 文件
env_paths = [
    Path('.env'),  # 当前目录
    Path(__file__).parent / '.env',  # 项目根目录
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path.absolute()}")
        break
else:
    print("⚠️  未找到 .env 文件，使用默认配置")

from database import init_db
from api.routers import knowledge_base, document, search, chat, coze

# 创建 FastAPI 应用
app = FastAPI(
    title="RAG 文档管理系统",
    description="""
    基于 FastAPI + SQLite 的文档管理和检索系统
    
    主要功能：
    - 知识库管理
    - 文档上传和管理
    - 自动/手动文档分块
    - 向量化存储
    - 语义搜索
    - 实体关系提取（可选）
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求计时中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"服务器内部错误: {str(exc)}",
            "path": str(request.url)
        }
    )


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    print("🚀 启动 RAG 文档管理系统...")
    
    # 显示关键环境变量配置（隐藏敏感信息）
    print("\n📋 环境变量配置:")
    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL"),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL"),
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL"),
        "COZE_API_KEY": os.getenv("COZE_API_KEY"),
        "COZE_WORKFLOW_ID": os.getenv("COZE_WORKFLOW_ID"),
    }
    
    for key, value in env_vars.items():
        if value:
            # 隐藏敏感信息
            if "KEY" in key or "PASSWORD" in key:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"   {key}: {display_value}")
        else:
            print(f"   {key}: <未设置>")
    
    print()
    init_db()
    print("✅ 数据库初始化完成")


# 根路径
@app.get("/", tags=["root"])
async def root():
    """API 根路径"""
    return {
        "message": "RAG 文档管理系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# 健康检查
@app.get("/health", tags=["root"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@app.get("/config", tags=["root"])
async def get_config_status():
    """
    获取配置状态
    
    显示哪些环境变量已配置（隐藏敏感信息）
    """
    def mask_value(value: str) -> str:
        """隐藏敏感信息"""
        if not value:
            return None
        if len(value) <= 8:
            return "***"
        return value[:8] + "..."
    
    config = {
        "openai": {
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "api_key": mask_value(os.getenv("OPENAI_API_KEY")),
            "base_url": os.getenv("OPENAI_BASE_URL", "默认"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4"),
        },
        "neo4j": {
            "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "username": os.getenv("NEO4J_USERNAME", "neo4j"),
            "password_configured": bool(os.getenv("NEO4J_PASSWORD")),
        },
        "ollama": {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        },
        "coze": {
            "api_key_configured": bool(os.getenv("COZE_API_KEY")),
            "api_key": mask_value(os.getenv("COZE_API_KEY")),
            "base_url": os.getenv("COZE_BASE_URL", "https://api.coze.cn"),
            "workflow_id": os.getenv("COZE_WORKFLOW_ID", "<未配置>"),
        },
        "features": {
            "vector_store": "可用",
            "ner": "可用" if os.getenv("OPENAI_API_KEY") else "需要配置 OPENAI_API_KEY",
            "knowledge_graph": "可用（需要启动 Neo4j）",
            "coze_workflow": "可用" if os.getenv("COZE_API_KEY") else "需要配置 COZE_API_KEY",
        }
    }
    
    return {
        "message": "配置状态",
        "config": config
    }


# 注册路由
app.include_router(knowledge_base.router, prefix="/api/v1")
app.include_router(document.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(coze.router, prefix="/api/v1")  # ⭐ NEW: Coze 工作流


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("RAG 文档管理系统")
    print("=" * 80)
    print("\n启动服务器...")
    print("API 文档: http://localhost:8000/docs")
    print("ReDoc 文档: http://localhost:8000/redoc")
    print("\n按 Ctrl+C 停止服务器\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )

