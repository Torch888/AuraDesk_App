"""LLM 自然语言解析引擎"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import httpx

from packages.shared.config import settings
from packages.shared.models import AgentParseResult, ReminderCategory, Priority


class LLMEngine:
    """使用大模型从自然语言中提取提醒信息"""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def parse_reminder(self, text: str) -> Optional[AgentParseResult]:
        """从自然语言中解析提醒意图和信息"""
        now = datetime.now()
        prompt = f"""你是一个智能提醒助手。当前时间是 {now.strftime('%Y年%m月%d日 %H:%M')}（{now.strftime('%A')}）。

请从用户的自然语言中提取提醒信息，返回严格 JSON 格式。

用户说: "{text}"

分析规则：
- intent: 意图类型 (create_reminder / query / update / delete / other)
- title: 提醒标题（简洁明了，如"部门晨会"、"抢周杰伦演唱会门票"）
- description: 补充说明（如会议链接、取件码等）
- category: 分类 (alarm/meeting/parcel/ticket/travel/bill/calendar/email/feishu/custom)
- start_time: 提醒触发时间 (ISO格式 "YYYY-MM-DD HH:MM")
- remind_offsets: 提前提醒的秒数数组（如提前30分钟 [-1800]、提前10分钟 [-600]、准时 [0]）
- priority: 优先级 (low/normal/high/critical)
- action_url: 相关操作链接（如有）
- recurrence: 重复规则 daily/weekly/monthly/yearly（无则为null）

只返回JSON，不要其他文字。"""

        try:
            client = await self._get_client()
            resp = await client.post("/chat/completions", json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个智能提醒助手。从用户输入中精确提取结构化提醒信息，只返回合法JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 500,
            })
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except Exception as e:
            print(f"[LLM] 解析失败: {e}")
            return None

    def _parse_response(self, content: str) -> Optional[AgentParseResult]:
        """解析LLM返回的JSON内容"""
        try:
            clean = content.strip()
            # 去掉可能的markdown代码块标记
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:]) if len(lines) > 1 else clean
                if clean.endswith("```"):
                    clean = clean[:-3].strip()
            parsed = json.loads(clean)
            return AgentParseResult(
                intent=parsed.get("intent", "create_reminder"),
                title=parsed.get("title", "提醒"),
                description=parsed.get("description"),
                category=ReminderCategory(parsed.get("category", "custom")),
                start_time=parsed.get("start_time", datetime.now().strftime("%Y-%m-%d %H:%M")),
                remind_offsets=parsed.get("remind_offsets", [-1800, -600, 0]),
                priority=Priority(parsed.get("priority", "normal")),
                action_url=parsed.get("action_url"),
            )
        except Exception as e:
            print(f"[LLM] JSON解析失败: {e}\n原始内容: {content}")
            return None


llm_engine = LLMEngine()