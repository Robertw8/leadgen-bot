from dataclasses import dataclass


@dataclass
class InboundEvent:
    tg_message_id: str
    tg_chat_id: str
    tg_user_id: str
    text: str
