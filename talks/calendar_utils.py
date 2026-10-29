"""Календарь выступлений: страница месяца и iCal-фид."""
import calendar as _cal
import datetime as _dt

from django.http import HttpResponse
from django.shortcuts import render

from .models import CalendarEvent, Talk

WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
MONTH_NAMES = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
               'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']


def _month_weeks(year, month):
    _cal.setfirstweekday(_cal.MONDAY)
    return _cal.monthcalendar(year, month)


def _events_for_month(year, month):
    """CalendarEvent за месяц + анонсы Talk как псевдо-события."""
    start = _dt.date(year, month, 1)
    if month == 12:
        end = _dt.date(year + 1, 1, 1) - _dt.timedelta(days=1)
    else:
        end = _dt.date(year, month + 1, 1) - _dt.timedelta(days=1)

    events = []
    for ev in CalendarEvent.objects.filter(is_published=True, date__range=(start, end)):
        links = []
        if ev.link1_url:
            links.append((ev.link1_url, ev.link1_label or 'Ссылка'))
        if ev.link2_url:
            links.append((ev.link2_url, ev.link2_label or 'Ссылка'))
        events.append({
            'date': ev.date, 'time': ev.time, 'kind': ev.kind,
            'title': ev.title, 'text': ev.text, 'links': links, 'talk': ev.talk,
        })

    for talk in Talk.objects.upcoming().filter(spoke_at__range=(start, end)):
        links = []
        if talk.registration_url:
            links.append((talk.registration_url, 'Регистрация'))
        events.append({
            'date': talk.spoke_at, 'time': None, 'kind': 'talk',
            'title': talk.title,
            'text': (talk.event + ' — анонс выступления') if talk.event else 'Анонс выступления',
            'links': links, 'talk': talk,
        })
    return events


def calendar_page(request):
    today = _dt.date.today()
    try:
        year = int(request.GET.get('y', today.year))
        month = int(request.GET.get('m', today.month))
        if not (1 <= month <= 12 and 1900 <= year <= 2100):
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    events = _events_for_month(year, month)
    by_day = {}
    for ev in events:
        by_day.setdefault(ev['date'].day, []).append(ev)

    if month == 1:
        prev_y, prev_m = year - 1, 12
    else:
        prev_y, prev_m = year, month - 1
    if month == 12:
        next_y, next_m = year + 1, 1
    else:
        next_y, next_m = year, month + 1

    upcoming = list(CalendarEvent.objects.filter(
        is_published=True, date__gte=today).order_by('date', 'time')[:6])

    return render(request, 'talks/calendar.html', {
        'year': year, 'month': month, 'month_name': MONTH_NAMES[month - 1],
        'weeks': _month_weeks(year, month), 'by_day': by_day,
        'weekdays': WEEKDAYS, 'today': today,
        'prev': (prev_y, prev_m), 'next': (next_y, next_m),
        'month_events': sorted(events, key=lambda e: (e['date'], e['time'] or _dt.time(0, 0))),
        'upcoming': upcoming,
    })


def _ical_escape(text):
    return (str(text)
            .replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\r\n', '\\n')
            .replace('\n', '\\n'))


def ical_feed(request):
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0',
             'PRODID:-//lemurqa.ru//Calendar//RU', 'CALSCALE:GREGORIAN',
             'X-WR-CALNAME:Календарь Лемурзильни']
    stamp = today = _dt.datetime.now().strftime('%Y%m%dT%H%M%SZ')

    for ev in CalendarEvent.objects.filter(is_published=True).order_by('date', 'time'):
        lines.append('BEGIN:VEVENT')
        lines.append(f'UID:event-{ev.id}@lemurqa.ru')
        lines.append(f'DTSTAMP:{stamp}')
        if ev.time:
            lines.append('DTSTART:' + ev.date.strftime('%Y%m%d') + 'T'
                         + ev.time.strftime('%H%M%S'))
            end_dt = _dt.datetime.combine(ev.date, ev.time) + _dt.timedelta(hours=1)
            lines.append('DTEND:' + end_dt.strftime('%Y%m%dT%H%M%S'))
        else:
            lines.append('DTSTART;VALUE=DATE:' + ev.date.strftime('%Y%m%d'))
            lines.append('DTEND;VALUE=DATE:'
                         + (ev.date + _dt.timedelta(days=1)).strftime('%Y%m%d'))
        lines.append('SUMMARY:' + _ical_escape(ev.title))
        desc = ev.text or ''
        if ev.link1_url:
            desc += '\n' + (ev.link1_label or 'Ссылка') + ': ' + ev.link1_url
        if ev.link2_url:
            desc += '\n' + (ev.link2_label or 'Ссылка') + ': ' + ev.link2_url
        if desc:
            lines.append('DESCRIPTION:' + _ical_escape(desc))
        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')
    body = '\r\n'.join(lines)
    resp = HttpResponse(body, content_type='text/calendar; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="lemurqa-calendar.ics"'
    return resp
