from pathlib import Path
from contextlib import contextmanager
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from portal.news_models import NewsSource, COMPANIES
from portal.news.service import collect

@contextmanager
def process_lock():
    # OS lock is released even after a crash; works on Windows and Linux.
    handle=open(Path(settings.BASE_DIR)/'.china-news.lock','a+b')
    handle.seek(0,2)
    if handle.tell()==0: handle.write(b'0');handle.flush()
    handle.seek(0)
    try:
        if __import__('os').name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close();raise CommandError('Другой сбор новостей уже выполняется')
    try: yield
    finally: handle.close()

class Command(BaseCommand):
    help='Собрать официальные новости в очередь редактора, без перевода через API и без публикации.'
    def add_arguments(self,parser):
        parser.add_argument('--source',choices=[v for v,_ in COMPANIES])
        parser.add_argument('--initial-limit',type=int,default=4,choices=range(3,6))
    def handle(self,*args,**options):
        errors=[]
        with process_lock():
            for company,_ in COMPANIES:
                if options['source'] and company!=options['source']: continue
                source,_=NewsSource.objects.get_or_create(company=company)
                if not source.enabled: continue
                run=collect(source,options['initial_limit'])
                self.stdout.write(f'{company}: new={run.created}, changed={run.changed}, unchanged={run.skipped}, error={run.error or "none"}')
                if run.error: errors.append(company)
        if errors: raise CommandError('Проверьте журнал источников: '+', '.join(errors))
