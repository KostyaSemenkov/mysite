"""Bounded GET-only client for a fixed set of public official sources."""
import time
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HOSTS = {'www.kimi.com', 'platform.kimi.ai', 'docs.z.ai', 'qwen.ai', 'api-docs.deepseek.com'}
USER_AGENT = 'NeuroNewsReader/1.0 (+local editorial news reader; hourly)'

def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError('Адрес не входит в список официальных источников')
    return url

class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT, 'Accept-Language':'en-US,en;q=0.9'})
        self.session.mount('https://', HTTPAdapter(max_retries=Retry(total=2, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=['GET'], respect_retry_after_header=False)))
        self.cache = {}
        self.robots = {}
        self.last_request = {}
    def _get(self, url):
        for _ in range(5):
            validate_url(url)
            host=urlparse(url).hostname
            time.sleep(max(0,0.6-(time.monotonic()-self.last_request.get(host,0))))
            self.last_request[host]=time.monotonic()
            with self.session.get(url, timeout=(8,25), allow_redirects=False, stream=True) as response:
                if response.status_code in (301,302,303,307,308):
                    url=urljoin(url,response.headers['Location'])
                    continue
                response.raise_for_status()
                chunks=[]; size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>12_000_000: raise ValueError('Ответ источника слишком большой')
                    chunks.append(chunk)
                return b''.join(chunks).decode('utf-8'), response.headers.get('Content-Type','')
        raise ValueError('Слишком много перенаправлений')
    def get(self, url):
        validate_url(url)
        if url in self.cache: return self.cache[url]
        host=urlparse(url).hostname
        if host not in self.robots:
            try:
                text, kind=self._get('https://'+host+'/robots.txt')
                # Several sites return their HTML homepage at /robots.txt.
                if '<html' in text[:2000].lower(): text=''
            except requests.HTTPError as exc:
                if exc.response.status_code not in (404,410): raise
                text=''
            parser=RobotFileParser();parser.parse(text.splitlines());self.robots[host]=parser
        if not self.robots[host].can_fetch(USER_AGENT,url):
            raise ValueError('robots.txt запрещает сбор этого адреса')
        text,_=self._get(url);self.cache[url]=text
        return text
