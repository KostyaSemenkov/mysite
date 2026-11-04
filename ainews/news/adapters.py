from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, quote
import json
import re
from bs4 import BeautifulSoup
from .fetch import validate_url

@dataclass
class Entry:
    key: str
    url: str
    title: str
    date: datetime
    text: str = ''
    event: str = 'model'

def date(value):
    value=value.strip().replace('Z','+00:00')
    dt=datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def clean(html):
    soup=BeautifulSoup(str(html),'html.parser')
    for node in soup.select('script,style,nav,footer,header,svg,button,noscript'): node.decompose()
    return re.sub(r'\n{3,}','\n\n',soup.get_text('\n',strip=True)).replace('\u200b','').strip()

def article_text(html):
    soup=BeautifulSoup(html,'html.parser')
    body=soup.select_one('.post-content, .markdown, .prose, article, main')
    if not body: raise ValueError('Не найден основной текст публикации')
    text=clean(body)
    if len(text)<100: raise ValueError('Не удалось извлечь полный текст публикации')
    return text

def relevant(title):
    t=title.casefold()
    # Conservative rules; uncertainty stays in the editor queue, never auto-published.
    if re.search(r'hiring|career|recruit|vacanc|giveaway|coupon|sale|discount|promotion|benchmark|bench\b|worldvqa|perception|verifier|scaling pain|infrastructure|tutorial|guide|office hour|recap|sapo|gspo|moba|muon',t): return False
    return bool(re.search(r'kimi|qwen|glm|deepseek|agent|api|pricing|price|feature|update|release|playground|cogvideo|cogview|autoglm',t))

def event_for(title):
    if re.search(r'api|pric|billing|cache',title,re.I): return 'api'
    if re.search(r'agent swarm|playground|function|feature',title,re.I): return 'feature'
    return 'model'

def kimi(fetch):
    url='https://www.kimi.com/en/blog/'
    soup=BeautifulSoup(fetch.get(url),'html.parser')
    entries={}
    for heading in soup.select('main h4'):
        container=heading.find_parent(class_='menu-card')
        if not container: continue
        link=container.select_one('a[href*="/blog/"]')
        day=container.select_one('.card-date')
        if not link or not day: continue
        target=urljoin(url,link['href']);title=heading.get_text(' ',strip=True)
        if relevant(title): entries[target]=Entry(target,target,title,date(day.get_text(strip=True)),event=event_for(title))
    # API/product posts supplement the model announcements.
    platform='https://platform.kimi.ai/blog'
    platform_soup=BeautifulSoup(fetch.get(platform),'html.parser')
    for h in platform_soup.select('h2,h3'):
        title=h.get_text(' ',strip=True)
        if not relevant(title) or 'release log' in title.casefold(): continue
        parent=h.parent
        for _ in range(4):
            if parent.find('time'): break
            parent=parent.parent
        link=h.find('a',href=True) or parent.find('a',href=True)
        time_tag=parent.find('time')
        if link and time_tag:
            target=urljoin(platform,link['href'])
            entries[target]=Entry(target,target,title,date(time_tag.get('datetime') or time_tag.get_text(strip=True)),event=event_for(title))
    changelog='https://platform.kimi.ai/blog/posts/changelog'
    log_soup=BeautifulSoup(fetch.get(changelog),'html.parser')
    for heading in log_soup.select('h2'):
        label=heading.get_text(' ',strip=True).strip('# ')
        try: stamp=datetime.strptime(label,'%B %d, %Y').replace(tzinfo=timezone.utc)
        except ValueError: continue
        nodes=[]
        for sibling in heading.next_siblings:
            if getattr(sibling,'name',None)=='h2': break
            nodes.append(str(sibling))
        text=clean(''.join(nodes))
        if len(text)<100: continue
        key='platform-update-'+stamp.date().isoformat()
        anchor=heading.get('id','')
        target=changelog+('#'+anchor if anchor else '')
        entries[key]=Entry(key,target,'Kimi API update: '+stamp.date().isoformat(),stamp,text,'api')
    return sorted(entries.values(),key=lambda x:x.date,reverse=True)

def zai(fetch):
    url='https://docs.z.ai/release-notes/new-released'
    soup=BeautifulSoup(fetch.get(url),'html.parser')
    entries=[]
    for block in soup.select('#content .update[id]'):
        stamp=block['id']
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',stamp): continue
        text=clean(block)
        # The first substantive line after the date is the release name.
        lines=[x.strip() for x in text.splitlines() if x.strip() and x.strip()!=stamp]
        if not lines: continue
        title=lines[0]
        if relevant(title): entries.append(Entry(stamp,url+'#'+stamp,title,date(stamp),text,event_for(title)))
    return sorted(entries,key=lambda x:x.date,reverse=True)

def deepseek(fetch):
    url='https://api-docs.deepseek.com/updates/'
    soup=BeautifulSoup(fetch.get(url),'html.parser')
    entries=[]
    for heading in soup.select('article h2'):
        match=re.search(r'\d{4}-\d{2}-\d{2}',heading.get_text())
        if not match: continue
        nodes=[]
        for sibling in heading.next_siblings:
            if getattr(sibling,'name',None)=='h2': break
            nodes.append(str(sibling))
        body=BeautifulSoup(''.join(nodes),'html.parser')
        title_tag=body.find('h3')
        if not title_tag: continue
        title=title_tag.get_text(' ',strip=True).replace('\u200b','').strip()
        stamp=match.group();anchor=heading.get('id','date-'+stamp)
        entries.append(Entry(stamp,url+'#'+anchor,title,date(stamp),clean(body),event_for(title)))
    return sorted(entries,key=lambda x:x.date,reverse=True)

def qwen(fetch):
    # Public read-only endpoint used by qwen.ai/research. No API key or model calls.
    url='https://qwen.ai/api/v2/article/retrieval?type=qwen_ai&language=en-US'
    data=json.loads(fetch.get(url))
    rows=data.get('data',{}).get('articles')
    if not data.get('success') or not isinstance(rows,list): raise ValueError('Изменился формат публичной ленты Qwen')
    entries=[]
    for row in rows:
        extra=row.get('extra') or {}
        title=row.get('title','')
        if not relevant(title): continue
        key=row.get('path') or row['id']
        entries.append(Entry(key,'https://qwen.ai/blog?id='+quote(key,safe=''),title,date(extra['date']),article_text(row['content']),event_for(title)))
    return sorted(entries,key=lambda x:x.date,reverse=True)

ADAPTERS={'kimi':kimi,'zai':zai,'qwen':qwen,'deepseek':deepseek}

def discover(company,fetch):
    rows=ADAPTERS[company](fetch)
    if not rows: raise ValueError('Источник не вернул публикаций: требуется проверка формата')
    seen=set();result=[]
    for row in rows:
        validate_url(row.url)
        if row.date>datetime.now(timezone.utc) or row.key in seen: continue
        seen.add(row.key);result.append(row)
    if not result: raise ValueError('Не найдены публикации с корректной датой')
    return result
