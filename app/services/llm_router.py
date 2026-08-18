from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass
class LLMResponse:
    text: str
    raw: dict


class LLMRouter:
    async def complete(self, model_alias: str, system: str, user: str, temperature: float = 0.2) -> LLMResponse:
        provider, model = model_alias.split('/', 1)
        if provider == 'openrouter':
            return await self._openrouter_chat(model, system, user, temperature)
        if provider == 'openai':
            return await self._openai_chat(model, system, user, temperature)
        if provider == 'anthropic':
            return await self._anthropic_chat(model, system, user, temperature)
        raise ValueError(f'Unsupported provider: {provider}')

    async def _openrouter_chat(self, model: str, system: str, user: str, temperature: float) -> LLMResponse:
        headers = {'Authorization': f'Bearer {settings.openrouter_api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': temperature,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(f'{settings.openrouter_base_url}/chat/completions', headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        text = data['choices'][0]['message']['content']
        return LLMResponse(text=text, raw=data)

    async def _openai_chat(self, model: str, system: str, user: str, temperature: float) -> LLMResponse:
        headers = {'Authorization': f'Bearer {settings.openai_api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': temperature,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return LLMResponse(text=data['choices'][0]['message']['content'], raw=data)

    async def _anthropic_chat(self, model: str, system: str, user: str, temperature: float) -> LLMResponse:
        headers = {
            'x-api-key': settings.anthropic_api_key or '',
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        payload = {
            'model': model,
            'max_tokens': 900,
            'temperature': temperature,
            'system': system,
            'messages': [{'role': 'user', 'content': user}],
        }
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post('https://api.anthropic.com/v1/messages', headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        text_parts = [block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text']
        return LLMResponse(text='\n'.join(text_parts).strip(), raw=data)

    @staticmethod
    def parse_json(text: str) -> dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            left = text.find('{')
            right = text.rfind('}')
            if left >= 0 and right > left:
                return json.loads(text[left : right + 1])
            raise
