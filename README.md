# JewelryCare AI v2：闭环 Multi-Agent 跨境珠宝客服与运营系统

JewelryCare AI 是一个面向 Shopify 珠宝类跨境独立站的智能客服与售后风控系统。

项目从最小 MVP 开始，逐步演进为支持售前导购、订单物流查询、售后定损、弃单挽回、人工兜底、真实图片识别、ReAct Trace 和 Bad Case 自动评测的 v2 Multi-Agent 智能客服系统。

本项目重点体现从 0 到 1 解决真实业务问题的过程，而不是简单搭建一个聊天机器人 Demo。

## 一、项目文档

- [项目说明书：从最小 MVP 到 v2 Multi-Agent 系统](docs/PROJECT_REPORT.md)
- [阶段 5 中文 Bad Case 评测报告](docs/eval_reports/stage5_eval_report_80cases_95pass.md)

## 二、核心能力

- 售前导购与 RAG 珠宝知识问答
- 订单物流查询
- 售后定损与工单创建
- Vision Adapter 图片 URL 识别
- 弃单挽回与优惠策略
- 高风险问题人工兜底
- ReAct Trace 可解释执行链路
- Prompt Injection 与业务幻觉控制
- 80 条 Bad Case 自动评测，通过率 95.00%

## 三、技术栈

- FastAPI
- Dify Chatflow
- SQLite
- Multi-Agent Orchestrator
- RAG Knowledge Base
- Vision Adapter
- Docker
- Python

## 四、最终评测结果

| 指标 | 数值 |
|---|---:|
| 测试样例总数 | 80 |
| 通过样例 | 76 |
| 失败样例 | 4 |
| 通过率 | 95.00% |

## 五、本地启动

运行 Docker 服务：

    docker compose up -d --build

健康检查：

    curl http://127.0.0.1:8000/health

## 六、安全说明

本仓库不包含真实 API Key。

请使用 .env.example 配置本地环境变量，真实 .env 文件不会提交到 GitHub。
