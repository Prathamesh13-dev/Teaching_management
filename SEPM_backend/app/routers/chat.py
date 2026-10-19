from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
import json
from .. import models, dependencies

router = APIRouter(prefix="/chat", tags=["Study Groups & Chat"])

# --- WEBSOCKET CONNECTION MANAGER ---
# This acts like a telephone operator, keeping track of who is in which group chat
class ConnectionManager:
    def __init__(self):
        # Dictionary format: { group_id: [connection1, connection2, ...] }
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_id: int):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: int):
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)

    async def broadcast(self, message: str, group_id: int):
        """Sends a message to every single person currently looking at this group."""
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                await connection.send_text(message)

manager = ConnectionManager()

# --- REST ENDPOINTS (Creating and Viewing Groups) ---

@router.post("/groups")
def create_group(
    name: str, 
    description: str = "", 
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_teacher) # Only teachers can create groups
):
    """Creates a new WhatsApp-style Study Group."""
    new_group = models.StudyGroup(name=name, description=description, created_by_id=current_user.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

@router.get("/groups")
def get_groups(db: Session = Depends(dependencies.get_db)):
    """Fetches all available groups so students can join them."""
    return db.query(models.StudyGroup).all()


# --- REAL-TIME WEBSOCKET ENDPOINT ---

@router.websocket("/ws/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: int, db: Session = Depends(dependencies.get_db)):
    """The open tunnel where instant messages fly back and forth!"""
    await manager.connect(websocket, group_id)
    try:
        while True:
            # 1. Wait for a message to arrive from someone's browser
            data = await websocket.receive_text()
            message_data = json.loads(data) 
            
            # 2. Save the message to the database so it's there if they refresh
            new_msg = models.Message(
                content=message_data["content"], 
                sender_id=message_data["sender_id"], 
                group_id=group_id
            )
            db.add(new_msg)
            db.commit()
            
            # 3. Instantly blast that message out to everyone else in the group!
            await manager.broadcast(data, group_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)