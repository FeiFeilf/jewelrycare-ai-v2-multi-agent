# JewelryCare AI v2：闭环 Multi-Agent 跨境珠宝客服与运营系统

这是一个可以直接用 PyCharm 打开的 FastAPI 后端项目。它在 v1 智能客服 MVP 的基础上，升级为闭环 Multi-Agent 架构。

## 项目结构

```text
jewelry-agent-mvp-v2/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── schemas.py
│   ├── orchestrator.py
│   ├── agents/
│   │   ├── router_agent.py
│   │   ├── knowledge_agent.py
│   │   ├── order_agent.py
│   │   ├── after_sales_agent.py
│   │   ├── recovery_agent.py
│   │   ├── handoff_agent.py
│   │   ├── task_agent.py
│   │   └── ops_agent.py
│   └── tools/
│       ├── order_tool.py
│       ├── ticket_tool.py
│       ├── recovery_tool.py
│       ├── handoff_tool.py
│       └── task_tool.py
├── data/
├── tests/
├── scripts/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dify.yml
└── requirements.txt
```

## 1. PyCharm 打开方式

打开 PyCharm，选择：

```text
File → Open → 选择 jewelry-agent-mvp-v2 文件夹
```

建议解释器使用 Python 3.11。

在 WSL 终端中创建虚拟环境：

```bash
cd ~/jewelry-agent-mvp-v2
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PyCharm 解释器路径选择：

```text
/home/feifei/jewelry-agent-mvp-v2/.venv/bin/python
```

## 2. 本地运行

```bash
cd ~/jewelry-agent-mvp-v2
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问：

```text
http://localhost:8000/health
http://localhost:8000/docs
```

## 3. Docker 运行

```bash
cd ~/jewelry-agent-mvp-v2
sudo docker rm -f customer-tools 2>/dev/null || true
sudo docker compose up -d --build
curl http://localhost:8000/health
```

## 4. Dify 联调运行

如果你要让 Dify 通过容器名 `customer-tools` 访问后端，使用：

```bash
cd ~/jewelry-agent-mvp-v2
sudo docker rm -f customer-tools 2>/dev/null || true
sudo docker compose -f docker-compose.dify.yml up -d --build
```

Dify HTTP 节点 URL：

```text
http://customer-tools/tools/handle_message_v3
```

Method：POST

Body：

```json
{
  "message": "{{#userinput.query#}}",
  "session_id": "dify-v2",
  "files": []
}
```

## 5. 核心接口

```text
GET  /health
POST /tools/handle_message_v3
GET  /tools/orders
GET  /tools/tickets
GET  /tools/handoffs
GET  /tools/recovery_logs
GET  /tools/tasks
GET  /tools/conversations
GET  /tools/agent_traces
GET  /tools/dashboard/summary
```

## 6. 闭环测试

售后闭环：

```bash
curl -X POST http://localhost:8000/tools/handle_message_v3 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的戒指掉钻了，订单号 ORD1001，请帮我处理。",
    "session_id": "test-after-sales",
    "files": []
  }'
```

弃单挽回闭环：

```bash
curl -X POST http://localhost:8000/tools/handle_message_v3 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I left CART2001 in my cart. Do you have any discount?",
    "session_id": "test-cart",
    "files": []
  }'
```

投诉兜底闭环：

```bash
curl -X POST http://localhost:8000/tools/handle_message_v3 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你们欺骗消费者，我要投诉，订单号 ORD9999。",
    "session_id": "test-complaint",
    "files": []
  }'
```

## 7. 自动测试

```bash
python tests/smoke_test_v2.py
```

预期全部 PASS。

## 8. 数据库说明

项目使用 SQLite，启动时自动创建并初始化测试数据。默认数据库路径：

```text
data/customer_service.db
```

测试订单：

```text
ORD1001：paid + delivered
ORD1002：paid + in_transit
ORD1003：refunded + delivered
```

测试购物车：

```text
CART2001：FREE-SHIPPING
CART2002：SAVE10
```

## 9. v2 新增闭环表

```text
conversations：记录对话
agent_traces：记录 Agent 决策轨迹
tasks：记录后续待办任务
```

这三个表是证明项目从普通客服接口升级为闭环 Multi-Agent 系统的关键。

## Project Documentation

- [完整项目说明书：从最小 MVP 到 v2 Multi-Agent 系统](docs/PROJECT_OVERVIEW.md)
- [项目演进说明](docs/PROJECT_EVOLUTION.md)
- [阶段 5 Bad Case 评测报告](docs/eval_reports/stage5_eval_report_80cases_95pass.md)

