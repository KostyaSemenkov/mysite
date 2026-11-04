from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import json
import requests
from bs4 import BeautifulSoup
OUT=Path(__file__).resolve().parent.parent/'.source-cache'
OUT.mkdir(exist_ok=True)
URLS={'kimi':'https://www.kimi.com/en/blog/','kimi_platform':'https://platform.kimi.ai/blog','zai':'https://z.ai/sitemap.xml','zai_news':'https://z.ai/model-api','zai_updates':'https://docs.z.ai/release-notes/new-released','qwen':'https://qwen.ai/research','qwen_map':'https://qwen.ai/sitemap.xml','deepseek':'https://api-docs.deepseek.com/updates/'}
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=35);r.encoding='utf-8';(OUT/(name+'.html')).write_text(r.text,encoding='utf-8');s=BeautifulSoup(r.text,'html.parser')
  return {'name':name,'status':r.status_code,'url':r.url,'size':len(r.content),'text':s.get_text(' ',strip=True)[:500],'links':[(a.get_text(' ',strip=True)[:100],urljoin(r.url,a['href'])) for a in s.select('a[href]') if any(t in a['href'] for t in ['blog','research','news','update'])][:35],'scripts':[urljoin(r.url,a['src']) for a in s.select('script[src]')][-8:]}
 except Exception as e:return {'name':name,'error':str(e)}
if __name__=='__main__':
 for result in ThreadPoolExecutor(max_workers=4).map(probe,URLS.items()): print(json.dumps(result,ensure_ascii=True))
