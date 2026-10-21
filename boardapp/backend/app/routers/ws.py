import math
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ..access import get_board_or_404, get_role
from ..board_manager import manager
from ..database import SessionLocal
from ..models import Board, Edge, Ticket, Zone
from ..security import decode_token

router = APIRouter(tags=['ws'])


def _valid_uuid(value) -> str | None:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError):
        return None


def _clamp(value, lo, hi) -> float:
    return max(lo, min(hi, float(value)))


def _ticket_height(text: str) -> float:
    """Авторост высоты тикета под текст (синхронизировано с фронтендом)."""
    lines = 0
    for ln in str(text).split('\n'):
        lines += max(1, math.ceil(len(ln) / 22))
    return max(100.0, 34 + lines * 21)


@router.websocket('/ws/boards/{board_id}')
async def board_ws(ws: WebSocket, board_id: str, token: str = ''):
    import logging
    log = logging.getLogger('ws')
    user_id = None
    try:
        user_id = decode_token(token)
    except Exception as e:
        log.warning('token reject: %s', e)
        await ws.close(code=4401)
        return

    async with SessionLocal() as session:
        from ..models import User
        user = await session.get(User, user_id)
        if user is None:
            log.warning('user not found: %s', user_id)
            await ws.close(code=4401)
            return
        try:
            board = await get_board_or_404(session, user, board_id)
        except Exception as e:
            log.warning('board access reject user=%s board=%s: %s', user_id, board_id, e)
            await ws.close(code=4404)
            return
        role = await get_role(session, user, board)
        board_title = board.title

    await ws.accept()
    conn = await manager.join(board_id, ws, user.id, user.username)

    # init: полный снимок + presence
    async with SessionLocal() as session:
        tickets = (await session.scalars(
            select(Ticket).where(Ticket.board_id == board_id))).all()
        edges = (await session.scalars(
            select(Edge).where(Edge.board_id == board_id))).all()
        zones = (await session.scalars(
            select(Zone).where(Zone.board_id == board_id))).all()
        init = {
            'type': 'init',
            'data': {
                'board': {'id': board_id, 'title': board_title},
                'zones': [
                    {'id': z.id, 'title': z.title, 'color': z.color,
                     'x': z.x, 'y': z.y, 'width': z.width, 'height': z.height}
                    for z in zones
                ],
                'tickets': [
                    {'id': t.id, 'x': t.x, 'y': t.y, 'width': t.width,
                     'height': t.height, 'text': t.text, 'color': t.color}
                    for t in tickets
                ],
                'edges': [
                    {'id': e.id, 'source': e.source_ticket_id, 'target': e.target_ticket_id}
                    for e in edges
                ],
                'role': role,
                'presence': manager.presence(board_id),
            },
        }
    await ws.send_json(init)
    await manager.broadcast(board_id, {
        'type': 'presence:join',
        'data': {'userId': user.id, 'username': user.username, 'color': conn.color},
    })

    async def send_error(message: str):
        await ws.send_json({'type': 'error', 'data': {'message': message}})

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get('type')
            data = msg.get('data') or {}

            if mtype == 'cursor:move':
                # не персистится: переслать остальным
                await manager.broadcast(board_id, {
                    'type': 'cursor',
                    'actor': user.id,
                    'data': {'userId': user.id, 'x': data.get('x', 0), 'y': data.get('y', 0)},
                })
                continue

            if role == 'viewer':
                await send_error('Просмотр без права редактирования')
                continue

            async with SessionLocal() as session:
                out = None
                if mtype == 'ticket:create':
                    tid = _valid_uuid(data.get('id'))
                    if not tid:
                        await send_error('Некорректный id тикета')
                    else:
                        t = Ticket(
                            id=tid, board_id=board_id,
                            x=float(data.get('x', 0)), y=float(data.get('y', 0)),
                            width=float(data.get('width', 200)),
                            height=float(data.get('height', 100)),
                            text=str(data.get('text', ''))[:100],
                            color=str(data.get('color', '#FFF3B1'))[:9],
                            updated_by=user.id,
                        )
                        session.add(t)
                        await session.commit()
                        out = {'type': 'ticket:created', 'actor': user.id,
                               'data': {'id': t.id, 'x': t.x, 'y': t.y,
                                        'width': t.width, 'height': t.height,
                                        'text': t.text, 'color': t.color}}
                elif mtype == 'ticket:update':
                    tid = _valid_uuid(data.get('id'))
                    patch = data.get('patch') or {}
                    t = await session.get(Ticket, tid) if tid else None
                    if t is None or t.board_id != board_id:
                        await send_error('Тикет не найден')
                    else:
                        for field_name in ('x', 'y', 'width', 'height'):
                            if field_name in patch:
                                setattr(t, field_name, float(patch[field_name]))
                        if 'text' in patch:
                            t.text = str(patch['text'])[:100]
                            t.height = _ticket_height(t.text)
                        if 'color' in patch:
                            t.color = str(patch['color'])[:9]
                        t.updated_by = user.id
                        await session.commit()
                        out_patch = dict(patch)
                        if 'text' in out_patch:
                            out_patch['height'] = t.height
                        out = {'type': 'ticket:updated', 'actor': user.id,
                               'data': {'id': t.id, 'patch': out_patch}}
                elif mtype == 'ticket:delete':
                    tid = _valid_uuid(data.get('id'))
                    t = await session.get(Ticket, tid) if tid else None
                    if t is None or t.board_id != board_id:
                        await send_error('Тикет не найден')
                    else:
                        await session.delete(t)
                        await session.commit()
                        out = {'type': 'ticket:deleted', 'actor': user.id,
                               'data': {'id': tid}}
                elif mtype == 'edge:create':
                    eid = _valid_uuid(data.get('id'))
                    src = _valid_uuid(data.get('source'))
                    tgt = _valid_uuid(data.get('target'))
                    if not (eid and src and tgt):
                        await send_error('Некорректные параметры связи')
                    else:
                        src_t = await session.get(Ticket, src)
                        tgt_t = await session.get(Ticket, tgt)
                        if (src_t is None or tgt_t is None
                                or src_t.board_id != board_id
                                or tgt_t.board_id != board_id):
                            await send_error('Тикет не найден')
                        else:
                            e = Edge(id=eid, board_id=board_id,
                                     source_ticket_id=src, target_ticket_id=tgt,
                                     updated_by=user.id)
                            session.add(e)
                            await session.commit()
                            out = {'type': 'edge:created', 'actor': user.id,
                                   'data': {'id': e.id, 'source': src, 'target': tgt}}
                elif mtype == 'edge:delete':
                    eid = _valid_uuid(data.get('id'))
                    e = await session.get(Edge, eid) if eid else None
                    if e is None or e.board_id != board_id:
                        await send_error('Связь не найдена')
                    else:
                        await session.delete(e)
                        await session.commit()
                        out = {'type': 'edge:deleted', 'actor': user.id,
                               'data': {'id': eid}}
                elif mtype == 'zone:create':
                    zid = _valid_uuid(data.get('id'))
                    if not zid:
                        await send_error('Некорректный id зоны')
                    else:
                        z = Zone(
                            id=zid, board_id=board_id,
                            title=str(data.get('title', ''))[:200],
                            color=str(data.get('color', '#7a4a2b'))[:9],
                            x=_clamp(data.get('x', 0), -100000, 100000),
                            y=_clamp(data.get('y', 0), -100000, 100000),
                            width=_clamp(data.get('width', 420), 160, 8000),
                            height=_clamp(data.get('height', 280), 100, 8000),
                            updated_by=user.id,
                        )
                        session.add(z)
                        await session.commit()
                        out = {'type': 'zone:created', 'actor': user.id,
                               'data': {'id': z.id, 'title': z.title, 'color': z.color,
                                        'x': z.x, 'y': z.y, 'width': z.width, 'height': z.height}}
                elif mtype == 'zone:update':
                    zid = _valid_uuid(data.get('id'))
                    patch = data.get('patch') or {}
                    z = await session.get(Zone, zid) if zid else None
                    if z is None or z.board_id != board_id:
                        await send_error('Зона не найдена')
                    else:
                        for field_name in ('x', 'y'):
                            if field_name in patch:
                                setattr(z, field_name,
                                        _clamp(patch[field_name], -100000, 100000))
                        for field_name in ('width', 'height'):
                            if field_name in patch:
                                setattr(z, field_name,
                                        _clamp(patch[field_name], 100, 8000))
                        if 'title' in patch:
                            z.title = str(patch['title'])[:200]
                        if 'color' in patch:
                            z.color = str(patch['color'])[:9]
                        z.updated_by = user.id
                        await session.commit()
                        out = {'type': 'zone:updated', 'actor': user.id,
                               'data': {'id': z.id, 'patch': patch}}
                elif mtype == 'zone:delete':
                    zid = _valid_uuid(data.get('id'))
                    z = await session.get(Zone, zid) if zid else None
                    if z is None or z.board_id != board_id:
                        await send_error('Зона не найдена')
                    else:
                        await session.delete(z)
                        await session.commit()
                        out = {'type': 'zone:deleted', 'actor': user.id,
                               'data': {'id': zid}}
                else:
                    await send_error(f'Неизвестный тип сообщения: {mtype}')

            if out is not None:
                await manager.broadcast(board_id, out)

    except WebSocketDisconnect:
        pass
    finally:
        await manager.leave(board_id, conn)
        await manager.broadcast(board_id, {
            'type': 'presence:leave',
            'data': {'userId': user.id},
        })
