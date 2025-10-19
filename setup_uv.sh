#!/bin/bash
# 使用 uv 快速设置项目环境
# 适用于 Linux 和 macOS

set -e

echo "=========================================="
echo "RAG Backend - uv 环境设置"
echo "=========================================="
echo ""

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 未检测到 uv，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv 安装完成"
    echo ""
else
    echo "✅ uv 已安装: $(uv --version)"
    echo ""
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "🐍 Python 版本: $PYTHON_VERSION"
echo ""

# 创建虚拟环境
if [ -d ".venv" ]; then
    echo "⚠️  虚拟环境已存在，是否重新创建？[y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "🗑️  删除旧环境..."
        rm -rf .venv
    else
        echo "⏩ 跳过创建虚拟环境"
        source .venv/bin/activate
        SKIP_VENV=true
    fi
fi

if [ -z "$SKIP_VENV" ]; then
    echo "📦 创建虚拟环境..."
    uv venv --python 3.10
    echo "✅ 虚拟环境创建完成"
    echo ""
    
    # 激活虚拟环境
    source .venv/bin/activate
fi

# 安装依赖
echo "📚 安装依赖..."
echo "选择安装模式:"
echo "  1) 基础依赖 (默认)"
echo "  2) 基础 + 开发工具"
echo "  3) 基础 + GPU 支持"
echo "  4) 完整安装 (所有依赖)"
echo ""
echo -n "请选择 [1-4, 默认1]: "
read -r install_mode

case $install_mode in
    2)
        echo "安装基础依赖 + 开发工具..."
        uv pip install -e ".[dev]"
        ;;
    3)
        echo "安装基础依赖 + GPU 支持..."
        uv pip install -e ".[gpu]"
        ;;
    4)
        echo "完整安装..."
        uv pip install -e ".[all,dev]"
        ;;
    *)
        echo "安装基础依赖..."
        uv pip install -e .
        ;;
esac

echo ""
echo "✅ 依赖安装完成"
echo ""

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    echo "请创建 .env 文件并配置必要的环境变量："
    echo ""
    echo "必需配置："
    echo "  OPENAI_API_KEY=sk-xxxxxxxxxxxxx"
    echo ""
    echo "可选配置："
    echo "  OPENAI_BASE_URL=https://api.openai.com/v1"
    echo "  OPENAI_MODEL=gpt-4"
    echo "  NEO4J_URI=bolt://localhost:7687"
    echo "  NEO4J_USERNAME=neo4j"
    echo "  NEO4J_PASSWORD=password"
    echo ""
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "=========================================="
echo "✨ 设置完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 激活虚拟环境: source .venv/bin/activate"
echo "  2. 启动服务: python main.py"
echo "  3. 访问文档: http://localhost:8000/docs"
echo ""
echo "更多信息请查看: UV_GUIDE.md"
echo ""

