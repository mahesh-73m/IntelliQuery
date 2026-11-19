from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFound
from app.database.session import get_db
from app.models.models import Conversation, Message, User
from app.schemas.api import ClarificationIn, ConversationCreate, MessageIn
from app.security.rate_limit import rate_limit
from app.services.orchestrator import message_out, process_turn

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _own(db: Session, user: User, conv_id: int) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:  # same 404 for "missing" and "not yours"
        raise NotFound("Conversation not found")
    return conv


def _conv_out(c: Conversation) -> dict:
    phase = (c.state or {}).get("phase")
    return {"id": c.id, "title": c.title, "phase": phase, "awaiting_clarification": phase == "AWAITING_USER",
            "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()}


@router.get("")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Conversation).where(Conversation.user_id == user.id)
                      .order_by(Conversation.updated_at.desc()).limit(100)).scalars().all()
    return [_conv_out(c) for c in rows]


@router.post("", status_code=201)
def create_conversation(body: ConversationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = Conversation(user_id=user.id, title=(body.title or "New conversation"), state={})
    db.add(conv)
    db.commit()
    return _conv_out(conv)


@router.get("/{conv_id}")
def get_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = _own(db, user, conv_id)
    msgs = db.execute(select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)).scalars().all()
    return {**_conv_out(conv), "messages": [message_out(m) for m in msgs]}


@router.delete("/{conv_id}", status_code=204)
def delete_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, user, conv_id))
    db.commit()


@router.post("/{conv_id}/messages", dependencies=[Depends(rate_limit("turn"))])
def send_message(conv_id: int, body: MessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = _own(db, user, conv_id)
    return process_turn(db, user, conv, question=body.content.strip(), provider_name=body.provider)


@router.post("/{conv_id}/clarifications", dependencies=[Depends(rate_limit("turn"))])
def answer_clarification(conv_id: int, body: ClarificationIn, user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    conv = _own(db, user, conv_id)
    return process_turn(db, user, conv, option_id=body.option_id, provider_name=body.provider)
