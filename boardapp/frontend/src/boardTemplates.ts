import type { XYPosition } from '@xyflow/react'
import { insertBoardElements } from './boardActions'
import type { TicketMsg, ZoneMsg } from './boardEvents'
import { STICKER_COLORS, ZONE_COLORS, ticketAutoHeight } from './store'

export const BOARD_TEMPLATES = [
  { id: 'retro', name: 'Ретро' },
  { id: 'bug', name: 'Разбор бага' },
] as const

export type BoardTemplate = (typeof BOARD_TEMPLATES)[number]['id']

export function insertBoardTemplate(template: BoardTemplate, center: XYPosition) {
  const x = Math.round(center.x / 20) * 20 - 400
  const y = Math.round(center.y / 20) * 20 - 140
  const ticket = (text: string, zoneId: string, index: number): TicketMsg => ({
    id: crypto.randomUUID(), text, zoneId, x: x + 20 + index * 280, y: y + 60,
    color: STICKER_COLORS[index], width: 200, height: ticketAutoHeight(text),
  })

  if (template === 'retro') {
    const columns = [
      ['Что получилось', 'Что стоит повторить?'],
      ['Что мешало', 'Что замедляло работу?'],
      ['Следующий шаг', 'Что попробуем в следующий раз?'],
    ]
    const zones: ZoneMsg[] = columns.map(([title], index) => ({
      id: crypto.randomUUID(), title, x: x + index * 280, y, width: 240, height: 280,
      color: ZONE_COLORS[index],
    }))
    const tickets = columns.map(([, text], index) => ticket(text, zones[index].id, index))
    insertBoardElements({ zones, tickets })
    return zones.map(({ id }) => id)
  }

  const zone: ZoneMsg = {
    id: crypto.randomUUID(), title: 'Разбор бага', x, y, width: 820, height: 280,
    color: ZONE_COLORS[0],
  }
  const tickets = [
    'Шаги воспроизведения',
    'Ожидание и фактический результат',
    'Причина и следующее действие',
  ].map((text, index) => ticket(text, zone.id, index))
  const edges = [
    { id: crypto.randomUUID(), source: tickets[0].id, target: tickets[1].id, label: 'наблюдаем' },
    { id: crypto.randomUUID(), source: tickets[1].id, target: tickets[2].id, label: 'разбираем' },
  ]
  insertBoardElements({ zones: [zone], tickets, edges })
  return [zone.id]
}
