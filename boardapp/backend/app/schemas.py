from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- auth ---

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str

    @classmethod
    def of(cls, user) -> 'UserOut':
        return cls(id=user.id, username=user.username)


class AuthOut(BaseModel):
    token: str
    user: UserOut


# --- boards ---

class BoardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class BoardPatch(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class BoardOut(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, board) -> 'BoardOut':
        return cls(
            id=board.id, title=board.title, owner_id=board.owner_id,
            created_at=board.created_at, updated_at=board.updated_at,
        )


class BoardWithRole(BoardOut):
    role: str  # owner | editor | viewer

    @classmethod
    def of(cls, board, role: str) -> 'BoardWithRole':
        data = BoardOut.of(board).model_dump()
        return cls(**data, role=role)


class BoardsList(BaseModel):
    own: list[BoardOut]
    shared: list[BoardWithRole]


class MemberIn(BaseModel):
    username: str
    role: Literal['editor', 'viewer']


class MemberOut(BaseModel):
    user: UserOut
    role: str


# --- board snapshot ---

class TicketOut(BaseModel):
    id: str
    x: float
    y: float
    width: float
    height: float
    text: str
    color: str
    updated_at: datetime

    @classmethod
    def of(cls, t) -> 'TicketOut':
        return cls(
            id=t.id, x=t.x, y=t.y, width=t.width, height=t.height,
            text=t.text, color=t.color, updated_at=t.updated_at,
        )


class EdgeOut(BaseModel):
    id: str
    source: str
    target: str
    updated_at: datetime

    @classmethod
    def of(cls, e) -> 'EdgeOut':
        return cls(
            id=e.id, source=e.source_ticket_id, target=e.target_ticket_id,
            updated_at=e.updated_at,
        )


class BoardSnapshot(BaseModel):
    board: BoardWithRole
    tickets: list[TicketOut]
    edges: list[EdgeOut]
    members: list[MemberOut]
