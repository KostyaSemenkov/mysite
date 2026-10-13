from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..access import get_board_or_404, get_role, get_user_by_username, require_editor
from ..database import get_session
from ..models import Board, BoardMember, Edge, Ticket, User
from ..schemas import (
    BoardCreate, BoardOut, BoardPatch, BoardSnapshot, BoardWithRole, BoardsList,
    EdgeOut, MemberIn, MemberOut, TicketOut, UserOut,
)
from ..security import get_current_user

router = APIRouter(prefix='/api/boards', tags=['boards'])


@router.get('', response_model=BoardsList)
async def list_boards(user: User = Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)):
    own = (await session.scalars(
        select(Board).where(Board.owner_id == user.id).order_by(Board.updated_at.desc())
    )).all()
    shared_rows = (await session.execute(
        select(Board, BoardMember.role)
        .join(BoardMember, BoardMember.board_id == Board.id)
        .where(BoardMember.user_id == user.id)
        .order_by(Board.updated_at.desc())
    )).all()
    return BoardsList(
        own=[BoardOut.of(b) for b in own],
        shared=[BoardWithRole.of(b, role) for b, role in shared_rows],
    )


@router.post('', response_model=BoardOut, status_code=201)
async def create_board(body: BoardCreate,
                       user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    board = Board(title=body.title.strip(), owner_id=user.id)
    session.add(board)
    await session.commit()
    await session.refresh(board)
    return BoardOut.of(board)


@router.get('/{board_id}', response_model=BoardSnapshot)
async def board_snapshot(board_id: str,
                         user: User = Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)):
    board = await get_board_or_404(session, user, board_id)
    role = await get_role(session, user, board)
    tickets = (await session.scalars(
        select(Ticket).where(Ticket.board_id == board.id)
    )).all()
    edges = (await session.scalars(
        select(Edge).where(Edge.board_id == board.id)
    )).all()
    member_rows = (await session.execute(
        select(BoardMember, User)
        .join(User, User.id == BoardMember.user_id)
        .where(BoardMember.board_id == board.id)
    )).all()
    return BoardSnapshot(
        board=BoardWithRole.of(board, role),
        tickets=[TicketOut.of(t) for t in tickets],
        edges=[EdgeOut.of(e) for e in edges],
        members=[MemberOut(user=UserOut.of(u), role=m.role) for m, u in member_rows],
    )


@router.patch('/{board_id}', response_model=BoardOut)
async def rename_board(board_id: str, body: BoardPatch,
                       user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    board = await get_board_or_404(session, user, board_id)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Только владелец может переименовывать доску')
    board.title = body.title.strip()
    await session.commit()
    await session.refresh(board)
    return BoardOut.of(board)


@router.delete('/{board_id}', status_code=204)
async def delete_board(board_id: str,
                       user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    board = await get_board_or_404(session, user, board_id)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Только владелец может удалить доску')
    await session.delete(board)
    await session.commit()
    return Response(status_code=204)


@router.post('/{board_id}/members', response_model=MemberOut, status_code=201)
async def add_member(board_id: str, body: MemberIn,
                     user: User = Depends(get_current_user),
                     session: AsyncSession = Depends(get_session)):
    board = await get_board_or_404(session, user, board_id)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Только владелец может приглашать')
    invitee = await get_user_by_username(session, body.username)
    if invitee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Пользователь не найден')
    if invitee.id == board.owner_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Владелец уже имеет доступ')
    member = await session.get(BoardMember, (board_id, invitee.id))
    if member is None:
        member = BoardMember(board_id=board_id, user_id=invitee.id, role=body.role)
        session.add(member)
    else:
        member.role = body.role
    await session.commit()
    return MemberOut(user=UserOut.of(invitee), role=member.role)


@router.delete('/{board_id}/members/{user_id}', status_code=204)
async def remove_member(board_id: str, user_id: str,
                        user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    board = await get_board_or_404(session, user, board_id)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Только владелец может удалять участников')
    member = await session.get(BoardMember, (board_id, user_id))
    if member is not None:
        await session.delete(member)
        await session.commit()
    return Response(status_code=204)
