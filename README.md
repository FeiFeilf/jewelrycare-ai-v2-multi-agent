# JewelryCare AI v2：跨境珠宝智能客服与售后风控系统

JewelryCare AI 是一个面向 **Shopify 珠宝类跨境独立站** 的智能客服与售后风控系统。

项目从最小 MVP 开始，逐步演进为支持 **售前导购、订单物流查询、售后定损、弃单挽回、人工兜底、图片识别、ReAct Trace 和 Bad Case 自动评测** 的 v2 Multi-Agent 闭环系统。

本项目不是简单的大模型聊天 Demo，而是围绕跨境电商客服与售后中的真实业务问题，构建了一个可运行、可解释、可测试、可扩展的智能客服后端系统。

---

## 1. 项目要解决什么问题

跨境珠宝独立站在客服与售后场景中存在多个高频痛点：

| 业务问题 | 具体表现 | 系统解决方式 |
|---|---|---|
| 售前咨询重复 | 用户反复询问尺码、材质、保养、送礼建议 | RAG 知识库 + LLM 生成自然回复 |
| 物流查询耗费人工 | 用户频繁询问订单是否发货、是否送达 | 后端查询订单状态，避免模型编造 |
| 售后风险高 | 划痕、掉钻、断裂、褪色等问题可能涉及退款补发 | 售后工单 + 风险等级 + 人工兜底 |
| 图片售后难处理 | 用户提供商品损坏图片，需要初步判断损坏类型 | Vision Adapter 调用视觉模型做初筛 |
| 大模型容易幻觉 | 可能编造订单、优惠码、退款结果 | 业务事实由后端决定，LLM 只负责表达 |
| 投诉和退款争议敏感 | 用户强烈投诉或要求立即退款 | 高风险场景转人工客服处理 |

核心设计原则：

> 低风险问题自动化处理，高风险问题转人工兜底。  
> 事实判断交给后端，专业知识交给知识库，语言表达交给大模型。

---

## 2. 系统整体架构

```text
用户输入 query / image_url
        ↓
Dify Chatflow
        ↓
RAG 知识库检索
        ↓
HTTP 节点调用 FastAPI 后端
        ↓
v4 Multi-Agent Orchestrator
        ↓
Router / Order / After-sales / Vision / Recovery / Handoff / Task Agents
        ↓
SQLite 模拟业务数据库 + Vision Adapter + Shopify Mock Tools
        ↓
结构化业务结果
        ↓
LLM 生成最终客服回复
        ↓
返回用户
```

系统中不同模块的职责：

| 模块 | 作用 |
|---|---|
| Dify Chatflow | 负责用户入口、知识库检索、调用后端和生成客服回复 |
| FastAPI Backend | 提供统一后端接口，承接 Dify HTTP 请求 |
| Multi-Agent Orchestrator | 负责任务编排、Agent 调用和业务闭环 |
| SQLite Mock DB | 模拟订单、购物车、工单、人工兜底、退款审核等业务数据 |
| Vision Adapter | 调用真实视觉模型，对图片 URL 进行售后初筛 |
| ReAct Trace | 记录 Thought → Action → Observation，展示系统执行过程 |
| Stage 5 Eval Suite | 自动执行 80 条 Bad Case，验证系统稳定性和幻觉控制 |

---

## 3. 项目从 0 到 1 的演进过程

本项目不是一次性完成，而是按真实产品研发流程逐步演进。

### 阶段 1：最小 MVP

第一版只验证最小业务闭环：

```text
用户输入
↓
Dify Chatflow
↓
FastAPI 后端
↓
SQLite 模拟业务数据
↓
结构化业务结果
↓
客服回复
```

实现能力：

- 基础订单查询；
- 基础售后工单；
- 基础弃单优惠；
- Dify HTTP 节点与 FastAPI 联调。

### 阶段 2：业务能力补全

MVP 跑通后，补充真实客服系统需要的业务动作：

- 售后工单字段增强；
- 风险等级；
- 售后证据要求；
- 人工兜底记录；
- 弃单挽回记录；
- 运营统计接口。

### 阶段 3：Multi-Agent 架构升级

将原本集中在一个流程中的业务逻辑拆分为多个 Agent：

| Agent | 职责 |
|---|---|
| Router Agent | 判断用户意图并路由 |
| Order Agent | 查询订单和物流状态 |
| After-sales Agent | 创建售后工单并判断风险 |
| Vision Agent | 根据图片摘要判断损坏类型 |
| Recovery Agent | 处理弃单挽回和优惠策略 |
| Handoff Agent | 创建人工兜底记录 |
| Task Agent | 创建后续跟进任务 |
| Memory Agent | 管理对话中的上下文记忆 |
| Evaluation Agent | 支持自动评测与结果检查 |

### 阶段 4：ReAct Trace 可解释链路

引入 ReAct Trace，记录系统每一步：

```text
Thought → Action → Observation
```

它可以展示：

- 为什么判断为售后；
- 调用了哪个 Agent；
- 查询到了什么订单；
- 是否创建工单；
- 是否转人工；
- 是否创建后续任务。

### 阶段 5：Vision Adapter 图片识别

最初尝试使用 Dify 文件上传直接接入视觉模型，但本地文件对象无法稳定形成模型可访问 URL。

最终改为后端 Vision Adapter：

```text
image_url
↓
FastAPI Vision Adapter
↓
真实视觉模型
↓
vision_summary
↓
Vision Agent
↓
售后工单 / 人工兜底 / 退款审核
```

### 阶段 6：Bad Case 自动评测

构建 80 条 Bad Case，覆盖：

- 售前 RAG；
- 物流查询；
- 售后定损；
- 投诉人工兜底；
- 弃单挽回；
- 已退款订单边界；
- Vision 图片售后；
- Prompt Injection 幻觉攻击。

最终通过率：**95.00%**。

---

## 4. 目录结构说明

```text
jewelry-agent-mvp/
├── app/
│   ├── agents/
│   ├── tools/
│   ├── db.py
│   ├── main.py
│   ├── orchestrator.py
│   ├── orchestrator_v4.py
│   └── schemas.py
├── data/
│   └── eval_cases/
├── docs/
│   ├── PROJECT_REPORT.md
│   ├── PROJECT_OVERVIEW.md
│   └── eval_reports/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dify.yml
├── requirements.txt
└── README.md
```

### 主要文件夹作用

| 路径 | 作用 |
|---|---|
| `app/` | 后端核心代码目录，包含 FastAPI 服务、Agent 编排、数据库和业务逻辑 |
| `app/agents/` | Multi-Agent 模块，每个 Agent 负责一个业务能力 |
| `app/tools/` | 工具层，包括视觉模型适配器、Shopify Mock、Memory、Evaluation 等 |
| `data/` | 数据目录，存放模拟数据和测试数据，不上传真实数据库 |
| `data/eval_cases/` | Stage 5 的 80 条 Bad Case 测试样例 |
| `docs/` | 项目文档目录 |
| `docs/eval_reports/` | 自动评测报告目录 |
| `scripts/` | 测试脚本、检查脚本、文档生成脚本 |
| `tests/` | 端到端测试脚本 |
| `.env.example` | 环境变量示例，不包含真实 API Key |
| `docker-compose.yml` | 后端 Docker 启动配置 |
| `docker-compose.dify.yml` | Dify 联调相关配置 |
| `README.md` | GitHub 项目首页 |

---

## 5. 核心代码模块说明

| 文件 / 模块 | 作用 |
|---|---|
| `app/main.py` | FastAPI 入口，定义 HTTP 接口 |
| `app/db.py` | SQLite 数据库初始化、模拟订单、工单、购物车等数据 |
| `app/schemas.py` | 请求和响应的数据结构定义 |
| `app/orchestrator.py` | 早期版本的业务编排逻辑 |
| `app/orchestrator_v4.py` | v4 Multi-Agent 闭环编排核心 |
| `app/agents/router_agent.py` | 判断用户意图，例如售前、物流、售后、投诉、弃单 |
| `app/agents/order_agent.py` | 查询订单和物流状态 |
| `app/agents/after_sales_agent.py` | 售后工单创建和风险判断 |
| `app/agents/vision_agent.py` | 根据图片摘要判断商品损坏风险 |
| `app/agents/shopify_agent.py` | 模拟 Shopify 后台动作，例如优惠码、退款审核 |
| `app/agents/memory_agent.py` | 管理多轮对话记忆 |
| `app/agents/evaluation_agent.py` | 支持自动评测 |
| `app/tools/vision_adapter.py` | 调用真实视觉模型，将图片 URL 转换为 vision_summary |
| `app/tools/shopify_mock_tool.py` | 模拟 Shopify 优惠码、退款审核等后台工具 |
| `app/tools/memory_tool.py` | 记忆相关工具 |
| `app/tools/evaluation_tool.py` | 自动评测相关工具 |

---

## 6. 主要接口

| 接口 | 方法 | 作用 |
|---|---|---|
| `/health` | GET | 健康检查 |
| `/tools/handle_message_v4` | POST | v4 Multi-Agent 主入口 |
| `/tools/vision_from_url` | POST | 图片 URL 识别入口 |
| `/tools/tickets` | GET | 查看售后工单 |
| `/tools/handoffs` | GET | 查看人工兜底记录 |
| `/tools/recovery_logs` | GET | 查看弃单挽回记录 |
| `/tools/tasks` | GET | 查看后续任务 |
| `/tools/react_steps` | GET | 查看 ReAct 执行步骤 |
| `/tools/agent_traces` | GET | 查看 Agent 调用轨迹 |
| `/tools/dashboard/summary` | GET | 查看运营统计摘要 |

---

## 7. 核心业务能力

### 7.1 售前导购与 RAG 问答

支持回答：

- 戒指尺寸选择；
- 18K 金是否掉色；
- 银饰氧化发黑；
- 珍珠保养；
- 送礼推荐；
- 跨境物流政策；
- 退换货政策。

### 7.2 订单物流查询

示例模拟订单：

| 订单号 | 商品 | 订单状态 | 物流状态 |
|---|---|---|---|
| ORD1001 | 18K Gold Ring | paid | delivered |
| ORD1002 | Silver Necklace | paid | in_transit |
| ORD1003 | Pearl Earrings | refunded | delivered |

### 7.3 售后定损与工单创建

支持识别：

- 划痕；
- 掉钻；
- 断裂；
- 褪色；
- 氧化；
- 色差；
- 包装破损；
- 高风险退款争议。

处理原则：

| 风险等级 | 系统动作 |
|---|---|
| low | 创建证据补充工单 |
| medium | 创建售后审核工单 |
| high | 创建售后工单并转人工审核 |

### 7.4 Vision 图片售后

用户提供图片 URL 后，后端调用视觉模型生成 `vision_summary`。

Vision Agent 再根据图片摘要判断：

- 是否有明显损坏；
- 损坏类型；
- 风险等级；
- 是否需要人工审核。

### 7.5 弃单挽回

示例购物车：

| 购物车编号 | 商品 | 优惠策略 |
|---|---|---|
| CART2001 | Rose Gold Bracelet | FREE-SHIPPING |
| CART2002 | Moissanite Ring | SAVE10 |

系统不会编造不存在的优惠码。

### 7.6 人工兜底

以下场景会转人工：

- 高风险售后；
- 强投诉；
- 强退款争议；
- 用户明确要求人工客服；
- 订单不存在但用户情绪强烈。

### 7.7 Prompt Injection 防护

系统不会采信用户伪造的：

- 订单状态；
- 退款结果；
- 优惠码；
- 售后工单；
- JSON 字段；
- vision_summary。

所有业务事实以后端结构化结果为准。

---

## 8. 关键难点与解决方案

| 难点 | 问题表现 | 解决方案 |
|---|---|---|
| Dify 无法通过 localhost 调后端 | Dify 在 Docker 内部，访问 localhost 指向容器自身 | 将后端加入 Dify Docker 网络，使用 `customer-tools` 容器名访问 |
| Dify 文件上传不稳定 | 上传文件对象无法稳定形成视觉模型可访问 URL | 改用 `image_url`，后端 Vision Adapter 统一调用视觉模型 |
| 视觉模型接口 404 | Workspace 专属地址或路径不匹配 | 切换 DashScope OpenAI-compatible 共享端点 |
| 识图成功但没进售后 | Router 只看文本，没有使用 vision_summary | 将 vision_summary 注入路由上下文，增加 Vision Fallback Ticket |
| Router 关键词过敏 | “掉色”误判售后，“物流一般多久”误判订单查询 | 增加业务路由提示和 Stage 5 后处理规则 |
| 高风险动作不能由模型决定 | 用户可能诱导模型直接退款或伪造订单 | 退款、工单、优惠、订单状态全部以后端为准 |

---

## 9. 自动评测结果

Stage 5 构建了 80 条 Bad Case 测试样例。

总体结果：

| 指标 | 数值 |
|---|---:|
| 测试样例总数 | 80 |
| 通过样例 | 76 |
| 失败样例 | 4 |
| 通过率 | 95.00% |

分类结果：

| 测试类别 | 通过 / 总数 | 通过率 |
|---|---:|---:|
| 售前导购与 RAG 问答 | 10 / 10 | 100.00% |
| 订单物流查询 | 10 / 10 | 100.00% |
| 售后定损与工单创建 | 19 / 20 | 95.00% |
| 投诉与人工兜底 | 14 / 15 | 93.33% |
| 弃单挽回 | 8 / 10 | 80.00% |
| 已退款订单边界 | 5 / 5 | 100.00% |
| Vision 图片售后 | 5 / 5 | 100.00% |
| Prompt Injection 与幻觉攻击 | 5 / 5 | 100.00% |

---

## 10. 本地运行

### 10.1 启动服务

```bash
docker compose up -d --build
```

### 10.2 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 10.3 测试主接口

```bash
curl -X POST http://127.0.0.1:8000/tools/handle_message_v4 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的戒指掉钻了，订单号 ORD1001，请帮我处理。",
    "session_id": "demo-session",
    "files": [],
    "vision_summary": ""
  }'
```

### 10.4 测试图片 URL 识别

```bash
curl -X POST http://127.0.0.1:8000/tools/vision_from_url \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的戒指有问题，订单号 ORD1001，请帮我看一下。",
    "image_url": "https://example.com/ring_damage.jpg"
  }'
```

---

## 11. 自动评测

生成测试集：

```bash
python scripts/generate_stage5_eval_cases.py
```

运行 80 条 Bad Case：

```bash
python scripts/run_stage5_eval_suite.py
```

导出中文测试报告：

```bash
python scripts/fix_docs_cn.py
```

评测报告位置：

```text
docs/eval_reports/stage5_eval_report_80cases_95pass.md
```

---

## 12. 项目文档

| 文档 | 说明 |
|---|---|
| [项目说明书](docs/PROJECT_REPORT.md) | 完整介绍项目背景、演进过程、图片识别、智能化边界、难点与解决方案 |
| [阶段 5 中文评测报告](docs/eval_reports/stage5_eval_report_80cases_95pass.md) | 80 条 Bad Case 自动评测、幻觉率控制、分类通过率与复盘 |
| [阶段 5 原始 JSON 报告](docs/eval_reports/stage5_eval_report_80cases_95pass.json) | 自动评测脚本生成的结构化结果 |

---

## 13. 安全说明

本仓库不包含真实 API Key。

请使用 `.env.example` 配置本地环境变量，真实 `.env` 文件不会提交到 GitHub。

同时，SQLite 运行时数据库、`.env`、`.venv` 等本地文件均已加入 `.gitignore`。

---

## 14. 项目总结

JewelryCare AI v2 从最小 MVP 出发，逐步补全业务能力、升级 Multi-Agent 架构、接入图片识别、增加 ReAct Trace，并最终通过 80 条 Bad Case 自动评测验证系统稳定性。

它不是一个简单的客服聊天 Demo，而是一个围绕跨境珠宝独立站真实业务问题构建的智能客服与售后风控系统。
