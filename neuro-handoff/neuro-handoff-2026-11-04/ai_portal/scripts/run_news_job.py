"""Silent hourly job entry point; never calls a paid LLM API."""
from pathlib import Path
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
(ROOT/'logs').mkdir(exist_ok=True)
log=logging.getLogger('china-news')
log.setLevel(logging.INFO)
handler=RotatingFileHandler(ROOT/'logs'/'china-news.log',maxBytes=1_000_000,backupCount=3,encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.addHandler(handler)
class Output:
    def write(self,message):
        if message.strip(): log.info(message.strip())
    def flush(self): pass

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django
    django.setup()
    from django.core.management import call_command
    log.info('Hourly collection started')
    try:call_command('import_china_news',stdout=Output(),stderr=Output())
    except Exception:
        log.exception('Collection failed; see source status in Django admin')
        return 1
    log.info('Hourly collection finished')
    return 0
if __name__=='__main__':sys.exit(main())
