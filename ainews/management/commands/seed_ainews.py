"""Перенос данных из SQLite-дампа НЕЙРО в ainews (lemurqa.ru)."""
import json
import os
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Переносит данные из SQLite НЕЙРО в модели ainews'

    def add_arguments(self, parser):
        parser.add_argument('--db', type=str,
                            default='neuro-handoff/neuro-handoff-2026-11-04/ai_portal/db.sqlite3',
                            help='Путь к SQLite-файлу НЕЙРО')

    def handle(self, *args, **options):
        db_path = options['db']
        if not os.path.exists(db_path):
            self.stdout.write(self.style.ERROR(f'Файл не найден: {db_path}'))
            return

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        from ainews.models import Course, ImportRun, IncomingNews, NewsSource, Publication

        # --- Publication ---
        pubs = conn.execute('SELECT * FROM portal_publication').fetchall()
        created_pubs = 0
        for row in pubs:
            _, is_new = Publication.objects.get_or_create(
                slug=row['slug'],
                defaults={
                    'title': row['title'],
                    'kind': row['kind'],
                    'topic': row['topic'],
                    'company': row['company'] or '',
                    'summary': row['summary'] or '',
                    'body': row['body'],
                    'author': row['author'] or 'Редакция',
                    'image_url': row['image_url'] or '',
                    'source_url': row['source_url'] or '',
                    'published': bool(row['published']),
                    'demo': bool(row['demo']),
                    'featured': bool(row['featured']),
                    'published_at': timezone.now(),
                })
            created_pubs += int(is_new)
        self.stdout.write(f'Публикаций: {created_pubs} создано '
                          f'(всего {Publication.objects.count()})')

        # --- Course ---
        courses = conn.execute('SELECT * FROM portal_course').fetchall()
        created_courses = 0
        for row in courses:
            _, is_new = Course.objects.get_or_create(
                slug=row['slug'],
                defaults={
                    'title': row['title'],
                    'provider': row['provider'],
                    'summary': row['summary'],
                    'audience': row['audience'] or '',
                    'program': row['program'] or '',
                    'level': row['level'],
                    'direction': row['direction'],
                    'duration': row['duration'] or '',
                    'price': row['price'] or 0,
                    'fmt': row['format'] or 'Онлайн',
                    'external_url': row['external_url'] or '',
                    'published': bool(row['published']),
                    'demo': bool(row['demo']),
                })
            created_courses += int(is_new)
        self.stdout.write(f'Курсов: {created_courses} создано '
                          f'(всего {Course.objects.count()})')

        # --- NewsSource ---
        sources = conn.execute('SELECT * FROM portal_newssource').fetchall()
        created_sources = 0
        for row in sources:
            seen = json.loads(row['seen_keys']) if row['seen_keys'] else []
            _, is_new = NewsSource.objects.get_or_create(
                company=row['company'],
                defaults={
                    'enabled': bool(row['enabled']),
                    'initialized': bool(row['initialized']),
                    'seen_keys': seen,
                })
            created_sources += int(is_new)
        self.stdout.write(f'Источников: {created_sources} создано '
                          f'(всего {NewsSource.objects.count()})')

        # --- IncomingNews ---
        incoming = conn.execute('SELECT * FROM portal_incomingnews').fetchall()
        created_incoming = 0
        for row in incoming:
            src = NewsSource.objects.filter(company=row['source_id']).first()
            if not src:
                continue
            pub = Publication.objects.filter(
                slug=conn.execute(
                    'SELECT slug FROM portal_publication WHERE id=?',
                    (row['publication_id'],)
                ).fetchone()[0]
            ).first() if row['publication_id'] else None

            _, is_new = IncomingNews.objects.get_or_create(
                source=src, source_key=row['source_key'],
                defaults={
                    'source_url': row['source_url'],
                    'original_title': row['original_title'],
                    'original_text': row['original_text'],
                    'previous_text': row['previous_text'] or '',
                    'source_date': timezone.now(),
                    'content_hash': row['content_hash'],
                    'title_ru': row['title_ru'] or '',
                    'summary_ru': row['summary_ru'] or '',
                    'body_ru': row['body_ru'] or '',
                    'event': row['event'],
                    'status': row['status'],
                    'publication': pub,
                })
            created_incoming += int(is_new)
        self.stdout.write(f'Входящих: {created_incoming} создано '
                          f'(всего {IncomingNews.objects.count()})')

        conn.close()
        self.stdout.write(self.style.SUCCESS('Перенос завершён.'))
