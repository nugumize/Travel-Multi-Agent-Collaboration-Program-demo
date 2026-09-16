# 智能旅行助手 - TravelAgent

基于多智能体（Multi-Agent）协作的 AI 旅行规划全栈 Web 应用。用户输入目的地、日期、偏好等信息后，系统通过 4 个专业 Agent 串行协作，结合高德地图实时数据，生成包含景点、天气、酒店、餐饮、预算的结构化旅行计划。

## ✨ 功能特点

- **多智能体协作**：景点搜索专家、天气查询专家、酒店推荐专家、行程规划专家，4 个 Agent 串行协作完成旅行规划
- **实时地图数据**：通过 MCP 接入高德地图，提供 POI 搜索、天气查询、路线规划等能力
- **可视化行程**：前端集成地图组件，支持景点标注、路线展示、行程编辑
- **导出功能**：支持行程导出为图片和 PDF
- **鲁棒性设计**：限流、缓存、重试、降级四层防护，保障服务可用性

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python + FastAPI |
| 前端 | Vue 3 + TypeScript + Vite |
| UI 框架 | Ant Design Vue |
| Agent 框架 | HelloAgents |
| LLM | ModelScope (Qwen3-235B) |
| 地图服务 | 高德地图 MCP Server |
| 图片服务 | Unsplash（可选） |

## 🏗 架构设计

```
用户请求
  │
  ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 景点搜索专家  │ ──▶ │ 天气查询专家  │ ──▶ │ 酒店推荐专家  │ ──▶ │ 行程规划专家  │
│  (MCP工具)   │     │  (MCP工具)   │     │  (MCP工具)   │     │  (整合输出)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                      │
                                                                      ▼
                                                              生成 JSON 行程计划
```

- 前 3 个 Agent 各自调用高德地图 MCP 工具搜索景点/天气/酒店
- 第 4 个 Agent 不调用工具，将前 3 个的结果整合生成结构化 JSON 行程计划

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 pnpm

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/travelAgent.git
cd travelAgent
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 5. 配置密钥

复制 `.env.example` 为 `.env`，填入你的密钥：

**后端** (`backend/.env`)：
```bash
# 必需：LLM API Key（兼容 OpenAI 格式，如 DeepSeek / 通义 / ModelScope）
LLM_API_KEY=your-llm-api-key-here
LLM_BASE_URL=https://api.deepseek.com/v1/

# 必需：高德 Web 服务 Key（申请地址：https://console.amap.com/）
AMAP_API_KEY=your_amap_web_service_key_here

# 可选：Unsplash Access Key（景点配图）
UNSPLASH_ACCESS_KEY=
```

**前端** (`frontend/.env`)：
```bash
# 可选：高德 Web 端 JS API Key（前端地图展示）
VITE_AMAP_WEB_JS_KEY=your_amap_web_js_key_here
```

### 6. 启动服务

**方式一：分别启动**

```bash
# 终端 1：启动后端（端口 8200）
cd backend
python run.py

# 终端 2：启动前端（端口 5173）
cd frontend
npm run dev
```

**方式二：一键启动（Windows）**

双击 `一键启动.bat`

### 7. 访问应用

- 前端地址：http://localhost:5173/
- 后端 API 文档：http://localhost:8200/docs

## 📁 项目结构

```
travelAgent/
├── backend/                      # 后端
│   ├── run.py                    # 启动入口
│   ├── requirements.txt          # Python 依赖
│   └── app/
│       ├── agents/               # 多智能体
│       ├── api/                  # API 路由
│       ├── models/               # 数据模型
│       └── services/             # 服务层（LLM/高德/Unsplash）
├── frontend/                     # 前端
│   └── src/
│       ├── views/                # 页面组件
│       ├── services/             # API 客户端
│       └── types/                # 类型定义
├── 一键启动.bat                   # Windows 一键启动脚本
├── 启动指南.md                    # 快速启动文档
├── 操作手册.md                    # 详细操作手册
└── 自检.py                       # 后端装配自检脚本
```

## 🔌 API 接口

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/trip/plan` | 生成完整旅行计划 |
| GET | `/api/poi/detail/{id}` | 获取 POI 详情 |
| GET | `/api/poi/search` | 搜索 POI |
| GET | `/api/poi/photo` | 获取景点图片 |
| GET | `/api/map/poi` | 地图 POI 搜索 |
| GET | `/api/map/weather` | 天气查询 |
| POST | `/api/map/route` | 路线规划 |
| GET | `/health` | 健康检查 |

## 🛡 容错机制

| 层级 | 策略 |
|------|------|
| LLM 层 | 429 限流自动重试（3 次指数退避） |
| Agent 层 | Agent 级别重试机制 |
| 高德服务层 | 令牌桶限流器（2 QPS）+ 结果缓存（TTL 10-60s）+ 3 次重试 |
| 降级方案 | Agent 全部失败时生成占位行程 |

## 📄 License

MIT
