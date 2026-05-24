from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import httpx

from packages.shared.config import settings
from packages.shared.models import AgentParseResult, ReminderCategory, Priority


class LLMEngine:
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
        prompt = f"""你是一个智能提醒助手。请从用户的自然语言中提取提醒信息。

用户说: "{text}"

请分析并返回JSON格式，包含:
- intent: 意图 (create_reminder / query / update / delete / other)
- title: 提醒标题
- category: alarm / meeting / parcel / ticket / travel / bill / custom
- start_time: 提醒时间 (ISO格式 YYYY-MM-DD HH:mm)
- remind_offsets: 提前提醒分钟数数组 (例如提前10分钟 [-10])
- priority: low / normal / high / critical
- action_url: 相关链接(如果有)
- description: 备注说明

只返回JSON，不要其他文字。"""

        try:
            client = await self._get_client()
            resp = await client.post("/chat/completions", json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个提醒助手。请从自然语言中提取结构化提醒信息，只返回JSON。"},
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
            print(f"LLM parse error: {e}")
            return None

    def _parse_response(self, content: str) -> Optional[AgentParseResult]:
        try:
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("\n", 1)[0]
                if clean.endswith("```"):
                    clean = clean[:-3].strip()
            parsed = json.loads(clean)
            return AgentParseResult(
                intent=parsed.get("intent", "create_reminder"),
                title=parsed.get("title", "提醒"),
                category=ReminderCategory(parsed.get("category", "custom")),
                start_time=parsed.get("start_time", datetime.now().strftime("%Y-%m-%d %H:%M")),
                remind_offsets=parsed.get("remind_offsets", [-3600, -600, 0]),
                priority=Priority(parsed.get("priority", "normal")),
                action_url=parsed.get("action_url"),
                description=parsed.get("description"),
            )
        except Exception as e:
            print(f"Parse response error: {e}")
            return None


llm_engine = LLMEngine()