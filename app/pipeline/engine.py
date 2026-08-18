from __future__ import annotations

from app.core.config import settings
from app.models.entities import LeadStatus
from app.pipeline.types import InboundEvent
from app.prompts.templates import DIALOG_SYSTEM, FILTER_SYSTEM, SCORE_SYSTEM, SUMMARY_SYSTEM
from app.services.llm_router import LLMRouter
from app.services.repositories import LeadRepo, MemoryRepo, MessageRepo, PlaybookRepo


class PipelineEngine:
    def __init__(
        self,
        msg_repo: MessageRepo,
        lead_repo: LeadRepo,
        memory_repo: MemoryRepo,
        playbook_repo: PlaybookRepo,
        llm: LLMRouter,
    ):
        self.msg_repo = msg_repo
        self.lead_repo = lead_repo
        self.memory_repo = memory_repo
        self.playbook_repo = playbook_repo
        self.llm = llm

    async def process(self, event: InboundEvent) -> dict:
        self.msg_repo.save(event.tg_message_id, event.tg_user_id, event.tg_chat_id, role='user', text=event.text)
        lead = self.lead_repo.get_or_create(event.tg_user_id, event.tg_chat_id)

        lead_check = await self.llm.complete(
            model_alias=settings.model_filter,
            system=FILTER_SYSTEM,
            user=event.text,
            temperature=0,
        )
        lead_json = self.llm.parse_json(lead_check.text)
        if not lead_json.get('is_lead', False):
            return {'action': 'skip', 'reason': lead_json.get('reason', 'not a lead')}

        score_resp = await self.llm.complete(
            model_alias=settings.model_score,
            system=SCORE_SYSTEM,
            user=event.text,
            temperature=0,
        )
        score_json = self.llm.parse_json(score_resp.text)
        score = int(score_json.get('score', 0))
        bucket = score_json.get('bucket', 'warm')

        status = LeadStatus.WARM
        if bucket == 'hot' or score >= settings.hot_score_threshold:
            status = LeadStatus.HOT
        elif bucket == 'trash':
            status = LeadStatus.TRASH
        self.lead_repo.update_status(lead, status, score)
        if status == LeadStatus.TRASH:
            return {'action': 'skip', 'reason': 'trash lead'}

        recent_messages = self.msg_repo.last_messages(event.tg_chat_id, limit=settings.max_context_messages)
        context = '\n'.join([f'[{m.role}] {m.text}' for m in recent_messages])

        summary_resp = await self.llm.complete(
            model_alias=settings.model_summary,
            system=SUMMARY_SYSTEM,
            user=context,
            temperature=0.1,
        )
        summary_json = self.llm.parse_json(summary_resp.text)

        self.lead_repo.update_summary(
            lead,
            summary=f"{summary_json.get('who', '')}. {summary_json.get('need', '')}",
            pain=summary_json.get('pain', ''),
            next_step=summary_json.get('next_reply', ''),
        )
        for fact in summary_json.get('facts', [])[:5]:
            self.memory_repo.add_fact(lead.id, fact)

        lead_facts = self.memory_repo.recent_facts(lead.id, limit=settings.max_facts_in_prompt)
        playbook_snippets = self.playbook_repo.find_relevant(event.text, limit=4)

        hard_keywords = [k.strip().lower() for k in settings.hard_trigger_keywords.split(',') if k.strip()]
        has_hard_keyword = any(k in event.text.lower() for k in hard_keywords)
        use_hard_model = score >= settings.handoff_score_threshold or has_hard_keyword

        dialog_prompt = (
            f"Контекст чата (последние {settings.max_context_messages}):\n{context}\n\n"
            f"Карточка лида:\n{summary_json}\n\n"
            f"Факты по лиду:\n{lead_facts}\n\n"
            f"Релевантные примеры из playbook:\n{playbook_snippets}\n\n"
            'Напиши один следующий ответ пользователю, чтобы продвинуть к согласию на созвон. '
            'Если рано звать на созвон, задай уточняющий вопрос, который двигает к нему.'
        )
        model_alias = settings.model_hard_dialog if use_hard_model else settings.model_dialog
        reply = await self.llm.complete(model_alias=model_alias, system=DIALOG_SYSTEM, user=dialog_prompt)
        answer = reply.text.strip()
        if len(answer) > settings.max_reply_chars:
            answer = answer[: settings.max_reply_chars].rstrip() + '...'

        self.msg_repo.save(f'out-{event.tg_message_id}', event.tg_user_id, event.tg_chat_id, role='assistant', text=answer)

        handoff = status == LeadStatus.HOT and score >= settings.handoff_score_threshold
        if handoff:
            self.lead_repo.update_status(lead, LeadStatus.HANDOFF, score)

        return {
            'action': 'reply',
            'reply_text': answer,
            'handoff': handoff,
            'lead_id': lead.id,
            'score': score,
            'status': status.value,
            'used_model': model_alias,
        }
