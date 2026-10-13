"""Права доступа к доскам: owner всегда, участники — по роли."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Board, BoardMember, User


async def get_board_or_404(session: AsyncSession, user: User, board_id: str) -> Board:
    """Доска, доступная пользователю. Чужая/несуществующая → 404 (не раскрываем)."""
    board = await session.get(Board, board_id)
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Доска не найдена')
    if board.owner_id != user.id:
        member = await session.get(BoardMember, (board_id, user.id))
        if member is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Доска не найдена')
    return board


async def get_role(session: AsyncSession, user: User, board: Board) -> str:
    if board.owner_id == user.id:
        return 'owner'
    member = await session.get(BoardMember, (board.id, user.id))
    return member.role if member else ''


async def require_editor(session: AsyncSession, user: User, board_id: str) -> Board:
    board = await get_board_or_404(session, user, board_id)
    role = await get_role(session, user, board)
    if role not in ('owner', 'editor'):
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Недостаточно прав')
    return board


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(select(User).where(User.username == username))
