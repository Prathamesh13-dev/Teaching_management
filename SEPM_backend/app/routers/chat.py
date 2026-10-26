from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Dict, Optional
from pydantic import BaseModel
import json
from datetime import datetime
from .. import models, dependencies
from ..database import SessionLocal

router = APIRouter(prefix="/chat", tags=["Study Groups & Chat"])

# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # group_id -> list of WebSockets
        self.active_group_connections: Dict[int, List[WebSocket]] = {}
        # user_id -> list of WebSockets
        self.active_user_connections: Dict[int, List[WebSocket]] = {}

    async def connect_group(self, websocket: WebSocket, group_id: int):
        await websocket.accept()
        if group_id not in self.active_group_connections:
            self.active_group_connections[group_id] = []
        self.active_group_connections[group_id].append(websocket)

    def disconnect_group(self, websocket: WebSocket, group_id: int):
        if group_id in self.active_group_connections:
            if websocket in self.active_group_connections[group_id]:
                self.active_group_connections[group_id].remove(websocket)

    async def broadcast_group(self, payload: dict, group_id: int):
        if group_id in self.active_group_connections:
            dead_connections = []
            for connection in self.active_group_connections[group_id]:
                try:
                    await connection.send_json(payload)
                except Exception:
                    dead_connections.append(connection)
            for dc in dead_connections:
                self.disconnect_group(dc, group_id)

manager = ConnectionManager()

# --- PYDANTIC SCHEMAS ---
class MessageCreate(BaseModel):
    content: str

# --- REST ENDPOINTS FOR GROUPS ---

@router.post("/groups")
def create_group(
    name: str, 
    description: str = "", 
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Creates a new WhatsApp-style Study Group (Teachers, Admins, or Students)."""
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Group name is required")

    new_group = models.StudyGroup(name=clean_name, description=description.strip(), created_by_id=current_user.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    # Automatically add creator as group member
    membership = models.GroupMember(user_id=current_user.id, group_id=new_group.id)
    db.add(membership)
    db.commit()

    return {
        "id": new_group.id,
        "name": new_group.name,
        "description": new_group.description,
        "created_by_id": new_group.created_by_id,
        "creator_name": current_user.username
    }

@router.get("/groups")
def get_groups(db: Session = Depends(dependencies.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    """Fetches all available study groups with member counts."""
    groups = db.query(models.StudyGroup).order_by(models.StudyGroup.id.asc()).all()
    results = []
    for g in groups:
        results.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "created_by_id": g.created_by_id,
            "creator_name": g.creator.username if g.creator else "Unknown",
            "message_count": len(g.messages) if g.messages else 0
        })
    return results

@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher_or_admin)
):
    """Moderation: Teachers/Admins can delete study groups."""
    group = db.query(models.StudyGroup).filter(models.StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")
        
    db.delete(group)
    db.commit()
    return {"message": f"Group '{group.name}' and all its messages have been removed by moderator."}

@router.get("/groups/{group_id}/messages")
def get_group_messages(
    group_id: int,
    limit: int = 100,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Loads historical messages for a group."""
    group = db.query(models.StudyGroup).filter(models.StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    messages = db.query(models.Message).filter(
        models.Message.group_id == group_id
    ).order_by(models.Message.id.asc()).limit(limit).all()

    return [
        {
            "id": m.id,
            "content": m.content,
            "sender_id": m.sender_id,
            "sender_name": m.sender.username if m.sender else "Anonymous",
            "sender_role": m.sender.role.value if m.sender else "student",
            "time_sent": m.time_sent.isoformat() if m.time_sent else None,
            "can_delete": (current_user.role in [models.UserRole.teacher, models.UserRole.admin]) or (m.sender_id == current_user.id)
        }
        for m in messages
    ]

@router.post("/groups/{group_id}/messages")
def post_group_message(
    group_id: int,
    body: MessageCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """REST fallback to post a message into a study group."""
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    new_msg = models.Message(
        content=content,
        sender_id=current_user.id,
        group_id=group_id,
        is_direct=False
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    payload = {
        "id": new_msg.id,
        "content": new_msg.content,
        "sender_id": current_user.id,
        "sender_name": current_user.username,
        "sender_role": current_user.role.value,
        "time_sent": new_msg.time_sent.isoformat() if new_msg.time_sent else datetime.now().isoformat(),
        "group_id": group_id
    }
    return payload

@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Moderation: Delete a message (by author or teacher/admin)."""
    msg = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    is_mod = current_user.role in [models.UserRole.teacher, models.UserRole.admin]
    if not is_mod and msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this message")

    db.delete(msg)
    db.commit()
    return {"message": "Message deleted successfully."}

# --- 1-ON-1 DIRECT MESSAGING ---

@router.get("/direct/{other_user_id}/messages")
def get_direct_messages(
    other_user_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetches private conversation between current user and another classmate/teacher."""
    other = db.query(models.User).filter(models.User.id == other_user_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    messages = db.query(models.Message).filter(
        models.Message.is_direct == True,
        or_(
            and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == other_user_id),
            and_(models.Message.sender_id == other_user_id, models.Message.receiver_id == current_user.id)
        )
    ).order_by(models.Message.id.asc()).all()

    return [
        {
            "id": m.id,
            "content": m.content,
            "sender_id": m.sender_id,
            "sender_name": m.sender.username if m.sender else "User",
            "receiver_id": m.receiver_id,
            "time_sent": m.time_sent.isoformat() if m.time_sent else None,
            "is_self": m.sender_id == current_user.id
        }
        for m in messages
    ]

@router.post("/direct/{other_user_id}")
def send_direct_message(
    other_user_id: int,
    body: MessageCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Sends a private 1-on-1 direct message."""
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    other = db.query(models.User).filter(models.User.id == other_user_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    new_msg = models.Message(
        content=content,
        sender_id=current_user.id,
        receiver_id=other_user_id,
        is_direct=True
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    return {
        "id": new_msg.id,
        "content": new_msg.content,
        "sender_id": current_user.id,
        "sender_name": current_user.username,
        "receiver_id": other_user_id,
        "time_sent": new_msg.time_sent.isoformat() if new_msg.time_sent else datetime.now().isoformat()
    }

# --- REAL-TIME WEBSOCKET ENDPOINT ---

@router.websocket("/ws/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: int):
    """Instant WebSocket connection for real-time study group conversations."""
    await manager.connect_group(websocket, group_id)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except Exception:
                continue

            content = data.get("content", "").strip()
            sender_id = data.get("sender_id")
            sender_name = data.get("sender_name", "Anonymous")

            if not content or not sender_id:
                continue

            # Persist to database in a clean local session
            db = SessionLocal()
            try:
                new_msg = models.Message(
                    content=content, 
                    sender_id=int(sender_id), 
                    group_id=group_id,
                    is_direct=False
                )
                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)

                msg_id = new_msg.id
                time_sent = new_msg.time_sent.isoformat() if new_msg.time_sent else datetime.now().isoformat()
            finally:
                db.close()

            # Broadcast to everyone in group
            payload = {
                "id": msg_id,
                "content": content,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "group_id": group_id,
                "time_sent": time_sent
            }
            await manager.broadcast_group(payload, group_id)

    except WebSocketDisconnect:
        manager.disconnect_group(websocket, group_id)
    except Exception:
        manager.disconnect_group(websocket, group_id)