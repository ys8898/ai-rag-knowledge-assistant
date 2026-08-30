# AI RAG Knowledge Assistant


基于 RAG 架构的企业知识库智能问答系统。

支持用户上传企业文档，通过向量检索 + Rerank + LLM 实现智能问答。


## 项目演示

功能：

- AI智能问答
- 多轮对话
- SSE流式输出
- Markdown渲染
- 企业知识库管理
- PDF/TXT/DOCX文件上传
- 文档来源追踪
- Docker一键部署


## 技术栈


### Frontend

- Vue3
- Vite
- Axios
- Markdown-it
- Nginx


### Backend

- FastAPI
- SQLite
- FAISS
- Sentence Embedding
- Reranker


### LLM

- Qwen
- SiliconFlow API


### Deployment

- Docker
- Docker Compose



## 系统架构


用户

↓

Vue3 + Nginx

↓

FastAPI

↓

RAG Pipeline

↓

FAISS检索

↓

BGE Reranker

↓

LLM生成



## 启动方式


### 1. 克隆项目

git clone xxx


### 2. 配置环境变量

backend/.env


填写：

LLM_API_KEY=xxxx



### 3. 启动

docker compose up --build



访问：

http://localhost

## API

Swagger:

http://localhost:8000/docs

## 项目结构


ai-rag-system

├── backend

├── frontend

├── docker-compose.yml

└── README.md



## 后续优化

- Agent工作流
- 多模态RAG
- 权限管理
- 企业级部署