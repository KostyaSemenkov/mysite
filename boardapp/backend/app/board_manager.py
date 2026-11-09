"""Connection manager: подписки на доски, presence, broadcast."""
import asyncio
import json
from contextlib import asynccontextmanager
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
    ready: bool = False


@dataclass
class BoardRoom:
    board_id: str
    connections: list[Connection] = field(default_factory=list)
    changes: asyncio.Lock = field(default_factory=asyncio.Lock)
    change_users: int = 0


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
                self._prune(room)

    def _prune(self, room: BoardRoom) -> None:
        if not room.connections and room.change_users == 0:
            self._rooms.pop(room.board_id, None)

    def presence(self, board_id: str) -> list[dict]:
        room = self._rooms.get(board_id)
        if not room:
            return []
        return list({
            c.user_id: {'userId': c.user_id, 'username': c.username, 'color': c.color}
            for c in room.connections if c.ready
        }.values())

    @asynccontextmanager
    async def lock_changes(self, board_id: str):
        async with self._lock:
            room = self._rooms.setdefault(board_id, BoardRoom(board_id=board_id))
            room.change_users += 1
        try:
            async with room.changes:
                yield
        finally:
            async with self._lock:
                room.change_users -= 1
                self._prune(room)

    async def broadcast(self, board_id: str, message: dict) -> None:
        """Послать сообщение всем подписчикам доски, включая отправителя."""
        room = self._rooms.get(board_id)
        if not room:
            return
        payload = json.dumps(message, ensure_ascii=False)
        dead: list[Connection] = []
        for conn in list(room.connections):
            if not conn.ready:
                continue
            try:
                await conn.ws.send_text(payload)
            except Exception:
                dead.append(conn)
        for conn in dead:
            await self.leave(board_id, conn)


manager = BoardManager()
