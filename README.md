# AI RAG Knowledge Assistant

这是一个基于 RAG（Retrieval-Augmented Generation，检索增强生成）的知识库问答项目。用户可以上传、更新和删除 TXT、PDF、DOCX 文档，通过向量检索、BGE 重排和远程 LLM API 获得带来源与置信度信息的流式回答。

## 主要功能

- 知识库文档上传、更新、删除和列表展示
- TXT、PDF、DOCX 文档读取与分块
- 远程 Embedding API 和 FAISS 向量检索
- 本地 BGE Reranker 二次排序
- 基于知识上下文和历史消息的 LLM 回答
- SSE 流式 token 输出，结束时发送来源和置信度 metadata
- SQLite 保存聊天历史和知识文件记录
- 向量索引、文档映射和知识库更新的一致性保护
- Docker Compose 部署，Nginx 提供前端并代理 `/api/` 请求

## 技术栈

### 前端

- Vue 3
- Vite
- Axios
- markdown-it
- Nginx

### 后端与 RAG

- FastAPI、Uvicorn
- SQLite
- FAISS（`IndexFlatL2`）
- OpenAI 兼容的 LLM/Embedding API
- FlagEmbedding `FlagReranker`
- 本地 `bge-reranker-base` 模型
- python-docx、pypdf

### 部署

- Docker
- Docker Compose

## 系统架构与请求流程

```text
Browser
  -> Vue 3 application
  -> Nginx /api/ reverse proxy
  -> FastAPI
       -> SQLite chat history
       -> query rewrite (when required)
       -> Embedding API
       -> FAISS retrieval
       -> BGE Reranker
       -> LLM API
  <- SSE token + metadata events
```

普通问答入口是 `POST /chat`，流式问答入口是 `POST /chat/stream`。Docker Compose 中只向宿主机发布前端的 80 端口；后端 8000 端口仅暴露在 Compose 网络内，由 Nginx 转发。

## RAG 流程

1. `document_loader.py` 读取 TXT、PDF 或 DOCX。
2. `create_vector.py` 清理文本并按配置切分 chunk。
3. `rag/rebuild_faiss.py` 调用远程 Embedding API，为每个 chunk 生成向量。
4. 向量写入 FAISS，chunk 内容与来源写入 `vector_db/documents.json`。
5. 查询时，`rag/search.py` 对问题生成向量，并从 FAISS 获取候选文档。
6. `rerank.py` 使用挂载在 `/models/bge-reranker-base` 的本地模型重排候选。
7. 过滤低分结果后，将知识上下文、问题和聊天历史发送给 LLM。
8. 返回回答、来源、chunk、重排分数和置信度信息。

## SSE 流式输出

`backend/llm/qwen.py` 只产生纯文本 token，`backend/main.py` 是唯一的 SSE 编码层。token 和 metadata 都使用 JSON 编码：

```text
event: token
data: {"text":"你好"}

event: metadata
data: {"sources":[],"confidence":{}}
```

前端在 `frontend/src/api/chat.js` 中按空行拆分 SSE 事件，并分别处理 `token` 与 `metadata`。JSON 编码可以安全传输换行、引号、反斜杠和 Markdown 代码块。

## 知识库更新与一致性保护

知识库同步不会先覆盖当前索引。新增、更新或删除文档时，后端先在临时目录构建候选 `documents.json`、FAISS 索引和 manifest，完成数量、维度、文件哈希和有序映射校验后再发布。

`vector_db/manifest.json` 记录同一代数据的：

- generation 标识
- 文档数量和向量维度
- `documents.json` SHA-256
- `index.faiss` SHA-256
- 文档有序映射指纹

检索前必须通过 manifest 校验。FAISS 返回 `-1` 时会忽略；返回其他负数或越界编号时会停止检索并报告一致性错误。

发布顺序为 documents、index、SQLite、manifest，其中 manifest 最后发布。普通异常会恢复旧文件和 SQLite 快照；进程中断时，旧 manifest 或 `update_in_progress.json` 会使检索失败关闭，避免继续使用无法证明一致的数据。

删除文档使用 `knowledge/.delete-backups/` 作为临时回滚目录。它与源知识文件位于同一个 Docker bind mount 内，避免跨挂载 `os.replace()` 触发 `EXDEV`。同步成功后清理备份；同步失败时恢复原文件；恢复失败时保留备份和更新标记供人工处理。该隐藏目录不会进入知识扫描或文件列表。

## 环境配置

复制占位符模板并填写 `backend/.env`。真实 `.env` 已被 Git 忽略，不要提交密钥。

```bash
cp backend/.env.example backend/.env
mkdir -p backend/knowledge backend/vector_db
touch backend/chat.db
```

PowerShell：

```powershell
Copy-Item backend\.env.example backend\.env
New-Item -ItemType Directory -Force backend\knowledge, backend\vector_db
New-Item -ItemType File -Force backend\chat.db
```

```dotenv
LLM_API_KEY=replace-with-your-api-key
LLM_BASE_URL=https://your-openai-compatible-endpoint.example/v1
LLM_MODEL=your-chat-model
LLM_EMBEDDING_MODEL=your-embedding-model

CHUNK_SIZE=450
CHUNK_OVERLAP=50
FAISS_TOP_K=20
RERANK_TOP_K=3
RERANK_SCORE_THRESHOLD=-2.5
```

Embedding 和聊天模型由同一个 OpenAI 兼容客户端配置。不要在代码、README、测试或压缩包中保存真实凭据。

## 模型准备

Reranker 从以下容器路径加载：

```text
/models/bge-reranker-base
```

Compose 将本地 `./models` 挂载到 `/models`。模型文件不适合提交到普通 Git 仓库，需要在部署机器上单独准备。

## Docker 使用

在项目根目录执行：

```bash
# 构建并启动
docker compose up -d --build

# 查看状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 停止服务
docker compose stop

# 停止并移除容器（不会主动删除 bind mount 中的数据）
docker compose down

# 代码更新后重新构建
docker compose build backend frontend
docker compose up -d
```

访问地址：<http://localhost>。

如果需要在宿主机直接查看 FastAPI Swagger，可在本地启动后端：

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

然后访问 <http://127.0.0.1:8000/docs>。

## 旧索引迁移

没有 manifest 的旧索引会被拒绝检索。确认已备份 `knowledge/`、`vector_db/` 和 `chat.db`，并确保 Embedding 服务可用后，可以在维护窗口执行一次受控重建：

```bash
docker compose stop backend
docker compose run --rm --no-deps backend \
  python -c "from knowledge_sync import sync_knowledge; sync_knowledge(force_rebuild=True)"
docker compose up -d backend
```

该命令会调用真实 Embedding API，并可能产生费用。它不会自动清理历史重复 chunk。

## 测试

后端一致性与删除回归测试使用临时目录和模拟 Embedding，不会修改真实知识库：

```bash
python -m unittest discover -s backend/tests -v
```

前端生产构建：

```bash
cd frontend
npm install
npm run build
```

最近一次本地和隔离 Docker 验证均执行了 25 个后端测试，覆盖：

- 正常检索、FAISS `-1` 和越界保护
- 数量不一致、缺少 manifest、文档顺序变化
- 添加、更新、删除成功与 Embedding 失败回滚
- 删除不存在文件及 HTTP 200/404/500/503 响应
- Docker 独立挂载下的删除备份回归
- 空知识库和强制重建

测试会出现 FastAPI TestClient 依赖弃用警告，当前不影响测试结果。

## 项目目录

```text
ai-rag-system/
├─ backend/
│  ├─ database/              # SQLite 访问层
│  ├─ knowledge/             # 知识源文件（可能包含私有数据）
│  ├─ llm/                   # LLM 与问题改写调用
│  ├─ rag/                   # 检索、索引重建与完整性校验
│  ├─ tests/                 # 临时目录隔离测试
│  ├─ vector_db/             # FAISS、documents、manifest 等运行数据
│  ├─ knowledge_manager.py   # 上传、删除与源文件回滚
│  ├─ knowledge_sync.py      # 候选构建、发布和回滚
│  └─ main.py                # FastAPI 入口
├─ frontend/
│  ├─ src/api/               # 聊天 API 与 SSE 解析
│  ├─ src/views/             # 知识库管理页面
│  └─ nginx.conf             # 静态资源与 /api/ 代理
├─ models/                   # 本地 Reranker 模型，不提交 Git
├─ docker-compose.yml
└─ README.md
```

## 最近修复

- SSE 由后端入口统一编码，token 使用 JSON，避免 Markdown 换行或代码块破坏事件边界。
- 检索加载时验证 FAISS、documents 和 manifest，拒绝 `-1` 误索引及越界编号。
- 知识库变更改为候选构建、验证、原子发布和可验证回滚。
- 修复 Docker 独立 bind mount 导致删除备份 `os.replace()` 报 `EXDEV` 的问题。
- 删除接口区分无效文件名、文件不存在、一致性错误和其他失败；前端显示成功或具体错误并防止重复提交。

## 已知限制

- 必须配置有效的远程 LLM 和 Embedding 服务；余额不足、限流或网络失败会使问答或索引重建失败。
- BGE Reranker 模型约 1.1 GB，需要单独下载并挂载，CPU 环境下重排可能较慢。
- 文件、FAISS 和 SQLite 无法组成真正的跨资源 ACID 事务。项目通过临时文件、备份、manifest 和更新标记实现失败关闭；进程异常退出后可能需要人工核对残留标记或备份。
- Python 线程锁只在单进程内有效。持久化更新标记可以阻止并发入口继续更新，但维护命令应在后端停止时执行。
- 当前不会自动清理历史重复 chunk。
- `backend/knowledge/`、`backend/vector_db/` 和 `backend/chat.db` 可能包含真实或私有数据，公开仓库前必须单独审核。
