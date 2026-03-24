import uuid
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[uuid.UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, auction_id: uuid.UUID):
        """Accepts the WebSocket connection and adds it to the specific auction room."""
        await websocket.accept()
        if auction_id not in self.active_connections:
            self.active_connections[auction_id] = []
        self.active_connections[auction_id].append(websocket)

    def disconnect(self, websocket: WebSocket, auction_id: uuid.UUID):
        """Removes the connection when a user leaves the page or loses internet."""
        if auction_id in self.active_connections:
            self.active_connections[auction_id].remove(websocket)

            if not self.active_connections[auction_id]:
                del self.active_connections[auction_id]

    async def broadcast_to_auction(self, auction_id: uuid.UUID, message: dict):
        """Pushes a JSON message to everyone actively watching this specific auction."""
        if auction_id in self.active_connections:
            for connection in list(self.active_connections[auction_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    self.disconnect(connection, auction_id)

manager = ConnectionManager()