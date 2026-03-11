# 多智能体客服系统 (Multi-Agent Customer Service)

基于 Orchestrator-Worker 架构的智能客服系统，采用 LangGraph 进行智能体编排，结合 GraphRAG 技术实现知识图谱增强检索。前端使用 Vue 3 + Element Plus 构建。

## 🌟 核心特性

- **多智能体协作**: 包含 Orchestrator, FAQ, Order, Product, Complaint, Human 等多种 Agent。
- **知识图谱增强**: 基于 Neo4j 和 Milvus 实现 GraphRAG，提供更精准的知识检索。
- **记忆系统**: 三级记忆架构（工作记忆、短期记忆、长期画像），支持长对话和个性化服务。
- **现代化技术栈**: FastAPI, LangGraph, Vue 3, Docker Compose。

## 🏗️ 架构概览

### 后端技术栈
- **Web 框架**: FastAPI
- **Agent 框架**: LangGraph, LangChain
- **数据库**: PostgreSQL (业务数据), Redis (缓存/消息队列), Neo4j (知识图谱), Milvus (向量数据)
- **任务队列**: Celery + RabbitMQ

### 前端技术栈
- **框架**: Vue 3 + TypeScript + Vite
- **UI 库**: Element Plus
- **状态管理**: Pinia
- **通信**: Axios + SSE (Server-Sent Events)

## 🚀 快速开始

### 前置要求
- Docker & Docker Compose
- Python 3.11+ (开发环境)
- Node.js 18+ (开发环境)
- `uv` 包管理器 (可选，推荐)

### 方式一：Docker 一键部署 (推荐)

1. **克隆项目**
   ```bash
   git clone <repository_url>
   cd multi-agent-customer-service
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的 OpenAI/Anthropic API Key
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```
   该命令会自动构建后端、前端及 Celery Worker 镜像，并启动所有依赖服务（Postgres, Redis, Neo4j, Milvus 等）。

4. **初始化数据** (首次运行时)
   等待所有服务启动健康（约需 30秒-1分钟），然后执行：
   ```bash
   # 初始化数据库表
   docker-compose exec api-gateway python scripts/init_db.py

   # 填充示例数据
   docker-compose exec api-gateway python scripts/seed_data.py

   # 构建初始知识库
   docker-compose exec api-gateway python scripts/build_knowledge_graph.py
   ```

5. **访问应用**
   - **前端界面**: http://localhost
   - **后端 API 文档**: http://localhost:8000/docs

### 方式二：本地开发运行

#### 后端

1. **安装依赖**
   ```bash
   uv sync
   # 或者: pip install -r requirements.txt (如果生成了)
   ```

2. **启动基础服务** (依赖 Docker)
   ```bash
   docker-compose up -d postgres redis rabbitmq neo4j milvus etcd minio
   ```

3. **初始化数据库**
   ```bash
   uv run python scripts/init_db.py
   uv run python scripts/seed_data.py
   ```

4. **启动 API 服务**
   ```bash
   uv run uvicorn main:app --reload
   ```

5. **启动 Celery Worker** (另开终端)
   ```bash
   uv run celery -A src.tasks.celery_app worker --loglevel=info
   ```

#### 前端

1. **进入目录**
   ```bash
   cd frontend
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **启动开发服**
   ```bash
   npm run dev
   ```
   访问: http://localhost:5173

## 🧪 默认账号

- **管理员**: `admin` / `admin123`
- **测试用户**: `testuser` / `test123`

## 📚 目录结构

```
.
├── src/                    # 后端源码
│   ├── agents/             # 智能体实现 (LangGraph)
│   ├── api/                # FastAPI 路由
│   ├── core/               # 核心配置
│   ├── models/             # 数据库模型
│   ├── rag/                # RAG 模块 (Graph/Vector Store)
│   ├── services/           # 业务逻辑
│   └── tasks/              # Celery 任务
├── frontend/               # 前端源码 (Vue 3)
├── scripts/                # 工具脚本
├── tests/                  # 测试用例
├── docker-compose.yml      # 容器编排
└── README.md               # 项目文档
```
