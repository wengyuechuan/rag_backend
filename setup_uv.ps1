# 使用 uv 快速设置项目环境
# 适用于 Windows PowerShell

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RAG Backend - uv 环境设置" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 uv 是否安装
try {
    $uvVersion = uv --version
    Write-Host "✅ uv 已安装: $uvVersion" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "❌ 未检测到 uv，正在安装..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex
    Write-Host "✅ uv 安装完成" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  请重新打开 PowerShell 以更新 PATH" -ForegroundColor Yellow
    Write-Host "然后再次运行此脚本" -ForegroundColor Yellow
    exit
}

# 检查 Python 版本
try {
    $pythonVersion = python --version
    Write-Host "🐍 Python 版本: $pythonVersion" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "❌ 未找到 Python，请先安装 Python 3.10 或更高版本" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit
}

# 创建虚拟环境
if (Test-Path ".venv") {
    Write-Host "⚠️  虚拟环境已存在，是否重新创建？[y/N]" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -match '^[Yy]') {
        Write-Host "🗑️  删除旧环境..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
        $skipVenv = $false
    }
    else {
        Write-Host "⏩ 跳过创建虚拟环境" -ForegroundColor Yellow
        .venv\Scripts\Activate.ps1
        $skipVenv = $true
    }
}
else {
    $skipVenv = $false
}

if (-not $skipVenv) {
    Write-Host "📦 创建虚拟环境..." -ForegroundColor Cyan
    uv venv --python 3.10
    Write-Host "✅ 虚拟环境创建完成" -ForegroundColor Green
    Write-Host ""
    
    # 激活虚拟环境
    .venv\Scripts\Activate.ps1
}

# 安装依赖
Write-Host "📚 安装依赖..." -ForegroundColor Cyan
Write-Host "选择安装模式:" -ForegroundColor Yellow
Write-Host "  1) 基础依赖 (默认)"
Write-Host "  2) 基础 + 开发工具"
Write-Host "  3) 基础 + GPU 支持"
Write-Host "  4) 完整安装 (所有依赖)"
Write-Host ""
$installMode = Read-Host "请选择 [1-4, 默认1]"

switch ($installMode) {
    "2" {
        Write-Host "安装基础依赖 + 开发工具..." -ForegroundColor Cyan
        uv pip install -e ".[dev]"
    }
    "3" {
        Write-Host "安装基础依赖 + GPU 支持..." -ForegroundColor Cyan
        uv pip install -e ".[gpu]"
    }
    "4" {
        Write-Host "完整安装..." -ForegroundColor Cyan
        uv pip install -e ".[all,dev]"
    }
    default {
        Write-Host "安装基础依赖..." -ForegroundColor Cyan
        uv pip install -e .
    }
}

Write-Host ""
Write-Host "✅ 依赖安装完成" -ForegroundColor Green
Write-Host ""

# 检查环境变量
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  未找到 .env 文件" -ForegroundColor Yellow
    Write-Host "请创建 .env 文件并配置必要的环境变量：" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "必需配置："
    Write-Host "  OPENAI_API_KEY=sk-xxxxxxxxxxxxx"
    Write-Host ""
    Write-Host "可选配置："
    Write-Host "  OPENAI_BASE_URL=https://api.openai.com/v1"
    Write-Host "  OPENAI_MODEL=gpt-4"
    Write-Host "  NEO4J_URI=bolt://localhost:7687"
    Write-Host "  NEO4J_USERNAME=neo4j"
    Write-Host "  NEO4J_PASSWORD=password"
    Write-Host ""
}
else {
    Write-Host "✅ .env 文件已存在" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✨ 设置完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "  1. 激活虚拟环境: .venv\Scripts\Activate.ps1"
Write-Host "  2. 启动服务: python main.py"
Write-Host "  3. 访问文档: http://localhost:8000/docs"
Write-Host ""
Write-Host "更多信息请查看: UV_GUIDE.md" -ForegroundColor Cyan
Write-Host ""

# 提示执行策略
Write-Host "💡 提示：如果无法运行脚本，请以管理员身份运行：" -ForegroundColor Yellow
Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Gray
Write-Host ""

