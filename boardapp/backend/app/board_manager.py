"""Connection manager: подписки на доски, presence, broadcast."""
import asyncio
import json
from dataclasses import dataclass, field

from fastapi import WebSocket

# Палитра присутствия — выдаётся по кругу
PRESENCE_COLORS = ['#E23E3E', '#F5A623', '#3E9BE3', '#37B679', '#9B51E0', '#E23EA8']


@dataclass
class Connection:
    ws: WebSocket
    user_id: str
    username: str
    color: str


@dataclass
class BoardRoom:
    board_id: str
    connections: list[Connection] = field(default_factory=list)


class BoardManager:
    def __init__(self) -> None:
        self._rooms: dict[str, BoardRoom] = {}
        self._lock = asyncio.Lock()
        self._color_cursor = 0

    def _next_color(self) -> str:
        color = PRESENCE_COLORS[self._color_cursor % len(PRESENCE_COLORS)]
        self._color_cursor += 1
        return color

    async def join(self, board_id: str, ws: WebSocket, user_id: str, username: str) -> Connection:
        conn = Connection(ws=ws, user_id=user_id, username=username,
                          color=self._next_color())
        async with self._lock:
            room = self._rooms.setdefault(board_id, BoardRoom(board_id=board_id))
            room.connections.append(conn)
        return conn

    async def leave(self, board_id: str, conn: Connection) -> None:
        async with self._lock:
            room = self._rooms.get(board_id)
            if room and conn in room.connections:
                room.connections.remove(conn)
                if not room.connections:
                    self._rooms.pop(board_id, None)

    def presence(self, board_id: str) -> list[dict]:
        room = self._rooms.get(board_id)
        if not room:
            return []
        return [
            {'userId': c.user_id, 'username': c.username, 'color': c.color}
            for c in room.connections
        ]

    async def broadcast(self, board_id: str, message: dict) -> None:
        """Послать сообщение всем подписчикам доски, включая отправителя."""
        room = self._rooms.get(board_id)
        if not room:
            return
        payload = json.dumps(message, ensure_ascii=False)
        dead: list[Connection] = []
        for conn in list(room.connections):
            try:
                await conn.ws.send_text(payload)
            except Exception:
                dead.append(conn)
        for conn in dead:
            await self.leave(board_id, conn)


manager = BoardManager()
