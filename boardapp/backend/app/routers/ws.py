import asyncio
import math
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..access import get_board_or_404, get_role
from ..board_manager import manager
from ..config import settings
from ..database import SessionLocal
from ..models import BoardClient, Edge, Ticket, User, Zone
from ..schemas import ZoneOut
from ..security import decode_token

router = APIRouter(tags=['ws'])

# сколько ждём сообщение auth после открытия сокета; больше — не подключаем
AUTH_TIMEOUT_SECONDS = 10
# потолок изменений в одном board:batch
MAX_BATCH_CHANGES = 200


def _valid_uuid(value) -> str | None:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _origin_allowed(headers) -> bool:
    """Страница, открывшая сокет, — с этого же сайта или из списка CORS.

    Браузер всегда присылает Origin; клиенты без него (тесты, консольные
    утилиты) пропускаются — им всё равно нужен действующий токен.
    Сравнение с Host покрывает и алиасы вроде www.
    """
    origin = headers.get('origin')
    if not origin or origin in settings.cors_origin_list:
        return True
    return urlparse(origin).netloc == headers.get('host', '')


def _clamp(value, lo, hi) -> float:
    return max(lo, min(hi, float(value)))


def _ticket_height(text: str) -> float:
    """Авторост высоты тикета под текст (синхронизировано с фронтендом).
    Под крупный шрифт 24px: 13 знаков/строку, 32px/строка, база 56, потолок 760."""
    lines = 0
    for ln in str(text).split('\n'):
        lines += max(1, math.ceil(len(ln) / 13))
    return min(760.0, max(130.0, 56 + lines * 32))


def _valid_operation(value) -> bool:
    return (
        isinstance(value, dict)
        and _valid_uuid(value.get('clientId')) == value.get('clientId')
        and isinstance(value.get('clientId'), str)
        and type(value.get('sequence')) is int
        and 0 < value['sequence'] <= 2_147_483_647
    )


async def _ticket_zone(session: AsyncSession, board_id: str, value) -> str | None:
    if value is None:
        return None
    zone_id = _valid_uuid(value)
    zone = await session.get(Zone, zone_id) if zone_id else None
    if zone is None or zone.board_id != board_id:
        raise ValueError('Группа не найдена на этой доске')
    return zone_id


async def _apply_change(session: AsyncSession, board_id: str, user_id: str,
                        mtype: str, data: dict) -> dict:
    if mtype == 'ticket:create':
        tid = _valid_uuid(data.get('id'))
        if not tid:
            raise ValueError('Некорректный id тикета')
        else:
            t = Ticket(
                id=tid, board_id=board_id,
                zone_id=await _ticket_zone(session, board_id, data.get('zoneId')),
                x=float(data.get('x', 0)), y=float(data.get('y', 0)),
                width=float(data.get('width', 200)),
                height=float(data.get('height', 100)),
                text=str(data.get('text', ''))[:100],
                color=str(data.get('color', '#FFF3B1'))[:9],
                updated_by=user_id,
            )
            session.add(t)
            out = {'type': 'ticket:created', 'actor': user_id,
                   'data': {'id': t.id, 'x': t.x, 'y': t.y,
                            'width': t.width, 'height': t.height,
                            'text': t.text, 'color': t.color, 'zoneId': t.zone_id}}
    elif mtype == 'ticket:update':
        tid = _valid_uuid(data.get('id'))
        patch = data.get('patch') or {}
        t = await session.get(Ticket, tid) if tid else None
        if t is None or t.board_id != board_id:
            raise ValueError('Тикет не найден')
        else:
            for field_name in ('x', 'y', 'width', 'height'):
                if field_name in patch:
                    setattr(t, field_name, float(patch[field_name]))
            if 'text' in patch:
                t.text = str(patch['text'])[:100]
                t.height = _ticket_height(t.text)
            if 'color' in patch:
                t.color = str(patch['color'])[:9]
            if 'zoneId' in patch:
                t.zone_id = await _ticket_zone(session, board_id, patch['zoneId'])
            t.updated_by = user_id
            out_patch = dict(patch)
            if 'text' in out_patch:
                out_patch['height'] = t.height
            if 'zoneId' in out_patch:
                out_patch['zoneId'] = t.zone_id
            out = {'type': 'ticket:updated', 'actor': user_id,
                   'data': {'id': t.id, 'patch': out_patch}}
    elif mtype == 'ticket:delete':
        tid = _valid_uuid(data.get('id'))
        t = await session.get(Ticket, tid) if tid else None
        if t is None or t.board_id != board_id:
            raise ValueError('Тикет не найден')
        else:
            await session.execute(delete(Edge).where(
                Edge.board_id == board_id,
                (Edge.source_ticket_id == tid) | (Edge.target_ticket_id == tid),
            ))
            await session.delete(t)
            out = {'type': 'ticket:deleted', 'actor': user_id,
                   'data': {'id': tid}}
    elif mtype == 'edge:create':
        eid = _valid_uuid(data.get('id'))
        src = _valid_uuid(data.get('source'))
        tgt = _valid_uuid(data.get('target'))
        if not (eid and src and tgt):
            raise ValueError('Некорректные параметры связи')
        else:
            src_t = await session.get(Ticket, src)
            tgt_t = await session.get(Ticket, tgt)
            if (src_t is None or tgt_t is None
                    or src_t.board_id != board_id
                    or tgt_t.board_id != board_id):
                raise ValueError('Тикет не найден')
            else:
                e = Edge(id=eid, board_id=board_id,
                         source_ticket_id=src, target_ticket_id=tgt,
                         label=str(data.get('label') or '').strip()[:100],
                         updated_by=user_id)
                session.add(e)
                out = {'type': 'edge:created', 'actor': user_id,
                       'data': {'id': e.id, 'source': src, 'target': tgt, 'label': e.label}}
    elif mtype == 'edge:update':
        eid = _valid_uuid(data.get('id'))
        e = await session.get(Edge, eid) if eid else None
        if e is None or e.board_id != board_id:
            raise ValueError('Связь не найдена')
        e.label = str(data.get('label') or '').strip()[:100]
        e.updated_by = user_id
        out = {'type': 'edge:updated', 'actor': user_id,
               'data': {'id': e.id, 'label': e.label}}
    elif mtype == 'edge:delete':
        eid = _valid_uuid(data.get('id'))
        e = await session.get(Edge, eid) if eid else None
        if e is None or e.board_id != board_id:
            raise ValueError('Связь не найдена')
        else:
            await session.delete(e)
            out = {'type': 'edge:deleted', 'actor': user_id,
                   'data': {'id': eid}}
    elif mtype == 'zone:create':
        zid = _valid_uuid(data.get('id'))
        if not zid:
            raise ValueError('Некорректный id группы')
        else:
            z = Zone(
                id=zid, board_id=board_id,
                title=str(data.get('title', ''))[:200],
                color=str(data.get('color', '#7a4a2b'))[:9],
                x=_clamp(data.get('x', 0), -100000, 100000),
                y=_clamp(data.get('y', 0), -100000, 100000),
                width=_clamp(data.get('width', 420), 160, 8000),
                height=_clamp(data.get('height', 280), 100, 8000),
                updated_by=user_id,
            )
            session.add(z)
            out = {'type': 'zone:created', 'actor': user_id,
                   'data': {'id': z.id, 'title': z.title, 'color': z.color,
                            'x': z.x, 'y': z.y, 'width': z.width, 'height': z.height}}
    elif mtype == 'zone:update':
        zid = _valid_uuid(data.get('id'))
        patch = data.get('patch') or {}
        z = await session.get(Zone, zid) if zid else None
        if z is None or z.board_id != board_id:
            raise ValueError('Группа не найдена')
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
            z.updated_by = user_id
            out = {'type': 'zone:updated', 'actor': user_id,
                   'data': {'id': z.id, 'patch': patch}}
    elif mtype == 'zone:delete':
        zid = _valid_uuid(data.get('id'))
        z = await session.get(Zone, zid) if zid else None
        if z is None or z.board_id != board_id:
            raise ValueError('Группа не найдена')
        else:
            await session.execute(update(Ticket).where(
                Ticket.board_id == board_id, Ticket.zone_id == zid,
            ).values(zone_id=None, updated_by=user_id))
            await session.delete(z)
            out = {'type': 'zone:deleted', 'actor': user_id,
                   'data': {'id': zid}}
    else:
        raise ValueError(f'Неизвестный тип сообщения: {mtype}')
    return out


@router.websocket('/ws/boards/{board_id}')
async def board_ws(ws: WebSocket, board_id: str):
    import logging
    log = logging.getLogger('ws')
    if not _origin_allowed(ws.headers):
        log.warning('ws origin reject: %s', ws.headers.get('origin'))
        await ws.close(code=4403)
        return
    await ws.accept()

    # Токен приходит первым сообщением, а не в адресе: адрес сокета попадает
    # в логи прокси и остаётся в истории вкладки. Прежний вход через ?token=
    # закрыт — клиент, который кладёт токен в адрес, не подключается.
    if 'token' in ws.query_params:
        log.warning('ws token in query is not accepted')
        await ws.close(code=4401)
        return
    try:
        first = await asyncio.wait_for(ws.receive_json(), AUTH_TIMEOUT_SECONDS)
    except Exception:
        await ws.close(code=4401)
        return
    if not isinstance(first, dict) or first.get('type') != 'auth' \
            or not isinstance(first.get('token'), str):
        await ws.close(code=4400)
        return
    token = first['token']
    clientId = str(first.get('clientId') or '')

    try:
        user_id = decode_token(token)
    except Exception as e:
        log.warning('token reject: %s', e)
        await ws.close(code=4401)
        return

    async with SessionLocal() as session:
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

    conn = await manager.join(board_id, ws, user.id, user.username)
    client_id = _valid_uuid(clientId)

    try:
        async with manager.lock_changes(board_id):
            # init: полный снимок + presence
            async with SessionLocal() as session:
                tickets = (await session.scalars(
                    select(Ticket).where(Ticket.board_id == board_id))).all()
                edges = (await session.scalars(
                    select(Edge).where(Edge.board_id == board_id))).all()
                zones = (await session.scalars(
                    select(Zone).where(Zone.board_id == board_id))).all()
                receipt = await session.get(BoardClient, (board_id, user.id, client_id)) if client_id else None
                init = {
                    'type': 'init',
                    'data': {
                        'board': {'id': board_id, 'title': board_title},
                        'zones': [ZoneOut.of(z).model_dump() for z in zones],
                        'tickets': [
                            {'id': t.id, 'x': t.x, 'y': t.y, 'width': t.width,
                             'height': t.height, 'text': t.text, 'color': t.color,
                             'zoneId': t.zone_id}
                            for t in tickets
                        ],
                        'edges': [
                            {'id': e.id, 'source': e.source_ticket_id,
                             'target': e.target_ticket_id, 'label': e.label}
                            for e in edges
                        ],
                        'role': role,
                        'lastSequence': receipt.last_sequence if receipt else 0,
                        'presence': manager.presence(board_id) + [{
                            'userId': user.id, 'username': user.username, 'color': conn.color,
                        }],
                    },
                }
            await ws.send_json(init)
            conn.ready = True
            await manager.broadcast(board_id, {
                'type': 'presence:join',
                'data': {'userId': user.id, 'username': user.username, 'color': conn.color},
            })

        async def send_error(message: str, operation=None):
            await ws.send_json({
                'type': 'error', 'data': {'message': message}, 'operation': operation,
            })

        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                await send_error('Некорректное сообщение')
                continue
            mtype = msg.get('type')
            data = msg.get('data') or {}

            if mtype == 'cursor:move':
                await manager.broadcast(board_id, {
                    'type': 'cursor',
                    'actor': user.id,
                    'data': {'userId': user.id, 'x': data.get('x', 0), 'y': data.get('y', 0)},
                })
                continue

            operation = msg.get('operation')
            if operation is not None and (
                not _valid_operation(operation) or (client_id and operation['clientId'] != client_id)
            ):
                await send_error('Некорректный номер операции')
                continue

            async with manager.lock_changes(board_id):
                try:
                    async with SessionLocal() as session:
                        current_board = await get_board_or_404(session, user, board_id)
                        if await get_role(session, user, current_board) not in ('owner', 'editor'):
                            await send_error('Просмотр без права редактирования', operation)
                            continue

                        # One in-flight edit per client. Its sequence advances in
                        # the same transaction as the board change.
                        receipt = None
                        if operation is not None:
                            key = (board_id, user.id, operation['clientId'])
                            receipt = await session.get(BoardClient, key)
                            if receipt is not None and receipt.last_sequence >= operation['sequence']:
                                await ws.send_json({'type': 'op:ack', 'operation': operation})
                                continue

                        if mtype == 'board:batch':
                            changes = data.get('changes')
                            if not isinstance(changes, list) or not changes:
                                raise ValueError('Пустая пакетная операция')
                            if len(changes) > MAX_BATCH_CHANGES:
                                raise ValueError(
                                    f'В одном пакете не больше {MAX_BATCH_CHANGES} изменений')
                            events = []
                            for change in changes:
                                events.append(await _apply_change(
                                    session, board_id, user.id, change['type'], change['data'],
                                ))
                            out = {'type': 'board:batch', 'data': {'events': events}}
                        else:
                            out = await _apply_change(session, board_id, user.id, mtype, data)

                        if operation is not None:
                            if receipt is None:
                                receipt = BoardClient(
                                    board_id=board_id, user_id=user.id,
                                    client_id=operation['clientId'],
                                )
                                session.add(receipt)
                            receipt.last_sequence = operation['sequence']
                            out['operation'] = operation
                        await session.commit()

                    await manager.broadcast(board_id, out)
                except HTTPException as exc:
                    await send_error(str(exc.detail), operation)
                except (ValueError, KeyError, TypeError, AttributeError) as exc:
                    await send_error(str(exc), operation)
                except IntegrityError:
                    await send_error('Операция конфликтует с сохранёнными данными', operation)

    except WebSocketDisconnect:
        pass
    finally:
        await manager.leave(board_id, conn)
        if not any(p['userId'] == user.id for p in manager.presence(board_id)):
            await manager.broadcast(board_id, {
                'type': 'presence:leave',
                'data': {'userId': user.id},
            })
