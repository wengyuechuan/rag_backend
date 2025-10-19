# FAISS 向量索引持久化说明

## 🎯 功能概述

系统已实现 FAISS 向量索引的自动持久化，每次文档处理完成后自动保存，重启后自动加载。

## 📂 存储位置

FAISS 索引自动保存在：
```
data/indexes/kb_{knowledge_base_id}/
├── index.faiss          # FAISS 索引文件
├── documents.pkl        # 文档元数据
└── metadata.json        # 索引配置信息
```

**示例**：
- 知识库 1 的索引：`data/indexes/kb_1/`
- 知识库 2 的索引：`data/indexes/kb_2/`

## 🔄 自动持久化流程

### 1. 首次创建知识库

```bash
POST /api/v1/knowledge-bases
{
  "name": "技术文档库",
  "enable_vector_store": true
}
```

**系统行为**：
1. 创建新的知识库记录
2. 创建空的 FAISS 索引（在内存中）
3. 索引目录暂不创建（等待首个文档）

### 2. 添加文档

```bash
POST /api/v1/documents
{
  "knowledge_base_id": 1,
  "title": "Python 教程",
  "content": "...",
  "auto_process": true
}
```

**系统行为**：
1. 文档分块
2. 生成嵌入向量
3. 添加到 FAISS 索引
4. **自动保存索引到磁盘** 💾
   ```
   💾 向量索引已保存到: data/indexes/kb_1
   ```

### 3. 重启服务器

```bash
# 停止服务
Ctrl+C

# 重新启动
python main.py
```

**系统行为**：
1. 启动时不自动加载（按需加载）
2. 当第一次访问知识库时：
   ```python
   # 搜索文档时
   GET /api/v1/search/
   ```
3. **自动检测并加载已存在的索引** 📂
   ```
   📂 正在加载知识库 1 的向量索引...
   ✅ 成功加载向量索引，文档数: 150
   ```

### 4. 继续添加文档

```bash
POST /api/v1/documents
{
  "knowledge_base_id": 1,
  "title": "新文档",
  ...
}
```

**系统行为**：
1. 加载已存在的索引（如果尚未加载）
2. 添加新向量
3. **再次保存，包含所有文档** 💾

## ✨ 特性说明

### 自动持久化
- ✅ 每次向量化完成后自动保存
- ✅ 增量保存，不影响性能
- ✅ 保存所有元数据

### 自动加载
- ✅ 首次访问时自动检测
- ✅ 如果索引存在，自动加载
- ✅ 如果索引损坏，创建新索引

### 数据安全
- ✅ 保存在本地磁盘
- ✅ 不提交到 Git（已在 .gitignore）
- ✅ 支持备份和恢复

## 📊 数据迁移

### 备份索引

```bash
# 备份整个 indexes 目录
cp -r data/indexes data/indexes_backup

# 或者只备份特定知识库
cp -r data/indexes/kb_1 data/indexes_kb_1_backup
```

### 恢复索引

```bash
# 恢复整个 indexes 目录
cp -r data/indexes_backup data/indexes

# 或者只恢复特定知识库
cp -r data/indexes_kb_1_backup data/indexes/kb_1
```

### 迁移到新服务器

```bash
# 1. 在旧服务器上打包
tar -czf rag_indexes.tar.gz data/indexes

# 2. 传输到新服务器
scp rag_indexes.tar.gz user@new-server:/path/to/RAG_backend/

# 3. 在新服务器上解压
cd /path/to/RAG_backend
tar -xzf rag_indexes.tar.gz

# 4. 启动服务
python main.py
# 索引会自动加载
```

## 🔍 查看索引状态

### 通过 API

```bash
# 搜索文档（会触发加载并显示状态）
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试",
    "knowledge_base_id": 1,
    "top_k": 5
  }'
```

### 检查日志

启动服务或首次搜索时，查看控制台输出：

```
✅ 文档处理服务已初始化 (最大工作线程: 4)
🚀 启动 RAG 文档管理系统...
✅ 数据库初始化完成

# 首次搜索时
📂 正在加载知识库 1 的向量索引...
✅ 成功加载向量索引，文档数: 150

# 添加文档后
💾 向量索引已保存到: data/indexes/kb_1
```

### 检查文件系统

```bash
# Linux/macOS
ls -lh data/indexes/kb_1/

# Windows
dir data\indexes\kb_1\
```

**预期输出**：
```
index.faiss       # FAISS 索引文件（较大）
documents.pkl     # 文档元数据
metadata.json     # 配置信息
```

## 🛠️ 故障排查

### 问题 1：索引加载失败

**现象**：
```
⚠️  加载索引失败: [Errno 2] No such file or directory，将创建新索引
```

**原因**：
- 索引文件不存在或路径错误
- 索引文件损坏

**解决方案**：
1. 检查 `data/indexes/kb_{id}/` 目录是否存在
2. 如果文件损坏，删除目录让系统重新创建
3. 从备份恢复（如果有）

### 问题 2：保存失败

**现象**：
```
⚠️  保存向量索引失败: [Errno 13] Permission denied
```

**原因**：
- 没有写入权限
- 磁盘空间不足

**解决方案**：
```bash
# 检查权限
ls -ld data/indexes

# 修复权限
chmod -R 755 data/indexes

# 检查磁盘空间
df -h
```

### 问题 3：索引数据丢失

**现象**：
- 重启后搜索结果为空
- 显示"文档数: 0"

**原因**：
- 保存失败
- 文件被删除

**解决方案**：
1. 检查 `data/indexes/` 目录是否存在
2. 如果有备份，从备份恢复
3. 如果没有备份，需要重新处理所有文档：
   ```bash
   # 重新处理文档
   POST /api/v1/documents/{doc_id}/process
   ```

### 问题 4：重复索引

**现象**：
- 同一文档出现多次
- 搜索返回重复结果

**原因**：
- 文档被重复处理

**解决方案**：
1. 删除知识库的索引目录：
   ```bash
   rm -rf data/indexes/kb_1
   ```
2. 重新处理所有文档

## 💡 最佳实践

### 1. 定期备份

```bash
#!/bin/bash
# backup_indexes.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/indexes_$DATE"

mkdir -p $BACKUP_DIR
cp -r data/indexes/* $BACKUP_DIR/

echo "✅ 索引已备份到: $BACKUP_DIR"
```

### 2. 清理旧索引

```bash
# 删除特定知识库的索引（谨慎操作）
rm -rf data/indexes/kb_1

# 删除所有索引（谨慎操作）
rm -rf data/indexes/*
```

### 3. 监控索引大小

```bash
# 查看索引占用空间
du -sh data/indexes/*

# 输出示例
# 1.2G  data/indexes/kb_1
# 500M  data/indexes/kb_2
```

### 4. 性能优化

**小知识库** (<10,000 文档)：
- 使用 `Flat` 索引（默认）
- 快速精确搜索

**中等知识库** (10,000-100,000 文档)：
- 考虑使用 `HNSW` 索引
- 修改 `get_vector_store()` 中的 `index_type="HNSW"`

**大知识库** (>100,000 文档)：
- 使用 `IVF` 索引
- 需要训练时间

## 📈 存储空间估算

| 文档数量 | 平均分块数 | 索引大小（估算） |
|---------|-----------|-----------------|
| 100     | 500       | ~50 MB          |
| 1,000   | 5,000     | ~500 MB         |
| 10,000  | 50,000    | ~5 GB           |
| 100,000 | 500,000   | ~50 GB          |

**说明**：
- 假设使用 `nomic-embed-text`（768 维）
- 包括向量数据 + 元数据
- 实际大小取决于文档内容

## 🔐 安全建议

### 1. 权限控制

```bash
# 设置索引目录权限
chmod 700 data/indexes

# 只允许运行服务的用户访问
chown -R app_user:app_user data/indexes
```

### 2. 备份策略

- ✅ 每天自动备份索引
- ✅ 保留最近 7 天的备份
- ✅ 定期测试恢复流程

### 3. 数据加密（可选）

对于敏感数据，可以：
1. 加密整个 `data/` 目录
2. 使用加密文件系统
3. 定期审计访问日志

## 📚 相关文档

- [FAISS 官方文档](https://github.com/facebookresearch/faiss)
- [API 文档](API_DOCUMENTATION.md)
- [性能优化指南](../README.md#性能优化建议)

## ✅ 总结

FAISS 索引持久化的核心优势：

1. **自动化**：无需手动操作，全自动保存和加载
2. **可靠性**：每次添加文档后立即保存
3. **高性能**：增量保存，不影响系统性能
4. **易维护**：简单的文件结构，易于备份和迁移
5. **零配置**：开箱即用，无需额外配置

**重要提示**：
- ⚠️ `data/indexes/` 已在 `.gitignore` 中，不会提交到 Git
- ✅ 部署时需要单独备份和迁移索引文件
- 💾 建议定期备份，避免数据丢失

开始使用，享受持久化带来的便利！🚀

