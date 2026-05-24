# 模块三：智能信息读取与提醒引擎

## 项目说明

**你负责的部分**：数字人智能提醒引擎的后端API服务  
**数字人怎么用**：通过 HTTP API 调用，获取提醒数据并展示

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
cd apps/api && python main.py

# 访问文档
# http://localhost:8000/docs
```

## API 接口说明

数字人通过以下接口获取数据：

### 1. 提醒管理

| 方法 | 路径 | 说明 | 数字人用途 |
|------|------|------|-----------|
| `GET` | `/api/reminders` | 获取所有提醒列表 | 数字人读取今天的提醒 |
| `GET` | `/api/reminders?status=pending` | 获取待处理的提醒 | 数字人只显示未完成的 |
| `GET` | `/api/reminders/{id}` | 获取单个提醒详情 | 点击某条提醒查看详情 |
| `POST` | `/api/reminders` | 创建提醒 | 用户对数字人说"提醒我..." |
| `PATCH` | `/api/reminders/{id}` | 更新提醒 | 修改提醒内容 |
| `DELETE` | `/api/reminders/{id}` | 删除提醒 | 用户说"删掉这个提醒" |
| `POST` | `/api/reminders/{id}/ack` | 确认提醒 | 数字人问"已确认吗" → 用户确认 |
| `POST` | `/api/reminders/{id}/snooze` | 稍后提醒 | 用户说"10分钟后再提醒" |

### 2. AI 自然语言解析

| 方法 | 路径 | 说明 | 数字人用途 |
|------|------|------|-----------|
| `POST` | `/api/agent/message` | 用户说一句话，AI自动创建提醒 | 用户对数字人说"明晚8点提醒我抢票" |

**请求体**：
```json
{"text": "明晚8点提醒我抢周杰伦演唱会门票"}
```
**返回**：
```json
{"ok": true, "message": "已创建提醒：明晚8点抢周杰伦演唱会门票", "reminder": {...}}
```

### 3. 快递管理

| 方法 | 路径 | 说明 | 数字人用途 |
|------|------|------|-----------|
| `GET` | `/api/parcels` | 快递列表 | 数字人显示"你有未取快递" |
| `POST` | `/api/parcels/parse` | 解析快递短信 | 用户转发短信给数字人 |
| `POST` | `/api/parcels/{id}/picked-up` | 标记已取件 | 用户说"取了" |

### 4. 票务管理

| 方法 | 路径 | 说明 | 数字人用途 |
|------|------|------|-----------|
| `GET` | `/api/tickets` | 票务列表 | 数字人提醒"演唱会快开抢了" |
| `POST` | `/api/tickets` | 添加票务 | 用户说"帮我盯着周杰伦演唱会" |

### 5. 统计

| 方法 | 路径 | 说明 | 数字人用途 |
|------|------|------|-----------|
| `GET` | `/api/stats` | 数据概览 | 数字人早上打招呼"你有3条提醒待处理" |

## 数字人集成示例

```python
# 数字人代码中这样调用模块三
import httpx

API_BASE = "http://localhost:8000/api"

async def get_today_reminders():
    """数字人调用此函数获取今天的提醒"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/reminders")
        return resp.json()

async def create_reminder_by_voice(text: str):
    """用户对数字人说一句话，自动创建提醒"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/agent/message", json={"text": text})
        return resp.json()
```

## 数字人对话场景

```
用户: "早上好"
数字人: "早上好！你今天有3条提醒：
    📌 10:00 部门会议
    📌 14:30 取快递(顺丰)
    📌 20:00 抢周杰伦演唱会门票"

用户: "明晚8点提醒我抢周杰伦演唱会门票"
数字人: "已帮你设置提醒！明晚8点我会准时提醒你~"

用户: "快递收到了"
数字人: "好的，已标记为已取件。"
```

## 启动方式

```bash
# 生产环境启动
cd apps/api && python main.py

# 开发模式启动（自动重启）
cd apps/api && uvicorn main:app --reload
```