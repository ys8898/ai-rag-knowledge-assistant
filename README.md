# AI RAG Knowledge Assistant

基于 RAG（Retrieval-Augmented Generation）架构的企业知识库智能问答系统。

支持企业文档上传，通过向量检索、Rerank 重排序以及大语言模型生成，实现基于企业知识库的智能问答。

## 项目演示

主要功能：

* AI 智能问答
* 多轮对话
* SSE 流式输出
* Markdown 内容渲染
* 企业知识库管理
* PDF / TXT / DOCX 文档上传
* 文档来源追踪
* Docker 一键部署

## 技术栈

### Frontend

* Vue3
* Vite
* Axios
* Markdown-it
* Nginx

### Backend

* FastAPI
* SQLite
* FAISS
* Sentence Embedding
* BGE Reranker

### LLM

* Qwen
* SiliconFlow API

### Deployment

* Docker
* Docker Compose

## 系统架构

用户请求

↓

Vue3 + Nginx

↓

FastAPI Backend

↓

RAG Pipeline

↓

FAISS 向量检索

↓

BGE Reranker 重排序

↓

LLM 生成回答

## 在线访问

项目地址：

GitHub：
https://github.com/ys8898/ai-rag-knowledge-assistant

在线体验：

http://116.62.224.244

API 文档：

http://116.62.224.244:8000/docs

## 本地启动方式

### 1. 克隆项目

```bash
git clone https://github.com/ys8898/ai-rag-knowledge-assistant.git
```

### 2. 配置环境变量

进入 backend 目录：

```bash
cd backend
```

创建 `.env` 文件：

```env
LLM_API_KEY=your_api_key
```

### 3. Docker 启动

```bash
docker compose up --build
```

启动完成后访问：

```text
http://localhost
```

## API 接口

Swagger API 文档：

```text
http://localhost:8000/docs
```

## 项目结构

```
ai-rag-system

├── backend              # FastAPI 后端服务
│
├── frontend             # Vue3 前端项目
│
├── docker-compose.yml   # Docker编排配置
│
└── README.md
```

## 后续优化方向

* Agent 工作流
* Tool Calling 工具调用
* 多模态 RAG
* 用户权限管理
* 企业级部署优化
* RAG 检索效果优化
