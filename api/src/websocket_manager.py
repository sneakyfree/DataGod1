"""
DataGod WebSocket Manager
Connection management and room-based broadcasting for real-time events
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("datagod.websocket")


class ConnectionManager:
    """
    Manages WebSocket connections with user-level tracking and
    room-based broadcasting for real-time events.
    """

    def __init__(self):
        # user_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}
        # room_name -> set of user_ids
        self._rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info(
            f"WebSocket connected: user={user_id}, total={self.connection_count}"
        )

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a disconnected WebSocket."""
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws != websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
                # Remove from all rooms
                for room in list(self._rooms.keys()):
                    self._rooms[room].discard(user_id)
        logger.info(f"WebSocket disconnected: user={user_id}")

    def join_room(self, user_id: str, room: str):
        """Add a user to a broadcast room."""
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(user_id)

    def leave_room(self, user_id: str, room: str):
        """Remove a user from a broadcast room."""
        if room in self._rooms:
            self._rooms[room].discard(user_id)

    async def send_personal(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user (all their connections)."""
        if user_id in self._connections:
            payload = json.dumps(message)
            dead_connections = []
            for ws in self._connections[user_id]:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_connections.append(ws)
            # Clean up dead connections
            for ws in dead_connections:
                self._connections[user_id].remove(ws)

    async def broadcast_room(self, room: str, message: Dict[str, Any]):
        """Broadcast a message to all users in a room."""
        if room not in self._rooms:
            return
        for user_id in self._rooms[room]:
            await self.send_personal(user_id, message)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users."""
        for user_id in list(self._connections.keys()):
            await self.send_personal(user_id, message)

    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Send a structured notification event to a user."""
        payload = {
            "event": "notification",
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_personal(user_id, payload)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    @property
    def user_count(self) -> int:
        return len(self._connections)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_connections": self.connection_count,
            "unique_users": self.user_count,
            "rooms": {room: len(users) for room, users in self._rooms.items()},
        }


# Global singleton
ws_manager = ConnectionManager()
