#!/usr/bin/env python3
"""Proxy List V06: 6 fonti aggiuntive, test HTTPS reali per HTTP/SOCKS.

Esegue un controllo TLS + HTTP attraverso ogni candidato HTTP/SOCKS selezionato.
Non considera un ping o una porta aperta come prova. I nodi V2Ray/Reality
provenienti da NodesRadar non sono provati da questo script: conta la verifica
esterna dichiarata da quella fonte, non una verifica locale.

Non modifica i file MEGA, Hiddify_IR.json o i parametri originali dei nodi.
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import json
import re
import socket
import ssl
import struct
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = 'https://raw.githubusercontent.com'
URLS = {
    'MN': f'{BASE}/monosans/proxy-list/main/proxies.json',
    'PF': f'{BASE}/proxifly/free-proxy-list/main/proxies/all/data.csv',
    'PS': f'{BASE}/ProxyScrape/free-proxy-list/main/proxies/all/data.csv',
    'HP': f'{BASE}/hproxy-com/free-proxy-list/main/live.csv',
    'SP_HTTP': 'https://spys.me/proxy.txt',
    'SP_SOCKS': 'https://spys.me/socks.txt',
    'NR': 'https://radarhub.top/sing-box.json',
}
# ISO 3166-1 alpha-2 + Kosovo XK; generati da uno snapshot ISO; mai inferire
# il paese da abbreviazioni ambigue all'interno di parole.
COUNTRIES = set('''AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW XK'''.split())
RAW_TYPES = {'http', 'https', 'socks4', 'socks5'}
NR_TYPES = {'vless', 'vmess', 'trojan', 'shadowsocks', 'hysteria2', 'tuic'}
TARGET = 'www.example.com'
PORT = 443
GEO_NAMES = {
  'kuwait':'KW','seychelles':'SC','united states':'US','usa':'US','america':'US',
  'united kingdom':'GB','great britain':'GB','britain':'GB','uk':'GB',
  'italia':'IT','italy':'IT','germany':'DE','france':'FR','saudi arabia':'SA',
  'bahrain':'BH','oman':'OM','qatar':'QA','jordan':'JO','iraq':'IQ','iran':'IR',
  'united arab emirates':'AE','emirates':'AE','dubai':'AE','palestine':'PS',
  'syria':'SY','yemen':'YE','somalia':'SO','sudan':'SD','libya':'LY',
  'lebanon':'LB','turkey':'TR','türkiye':'TR','netherlands':'NL',
  'south korea':'KR','japan':'JP','china':'CN','singapore':'SG',
  'taiwan':'TW','hong kong':'HK','india':'IN','australia':'AU',
}


def label_country(value: object) -> str:
    name = str(value or '').strip()
    if not name:
        return 'ZZ'
    # Bandiera Unicode: indicatori regionali consecutivi.
    chars = [ord(c) for c in name]
    for i in range(len(chars) - 1):
        if 0x1F1E6 <= chars[i] <= 0x1F1FF and 0x1F1E6 <= chars[i+1] <= 0x1F1FF:
            c = chr(65+chars[i]-0x1F1E6)+chr(65+chars[i+1]-0x1F1E6)
            return 'GB' if c == 'UK' else c if c in COUNTRIES else 'ZZ'
    # "ZZ" va ignorato: il testo a destra puo avere il nome corretto.
    name = re.sub(r'^🌐\s*ZZ\s*\|', ' ', name)
    for n, country in sorted(GEO_NAMES.items(), key=lambda x: -len(x[0])):
        if re.search(r'(?<![\w])'+re.escape(n)+r'(?![\w])', name, re.I):
            return country
    # Limita il riconoscimento ISO ai campi singoli, non a parole casuali.
    for field in re.split(r'\s*[|#;,]\s*', name):
        field = field.strip().upper()
        if field in COUNTRIES:
            return field
        match = re.match(r'^([A-Z]{2})(?:\s+[-:])', field)
        if match and match.group(1) in COUNTRIES:
            return match.group(1)
    return 'ZZ'


def cc(raw: object, fallback: str = '') -> str:
    candidate = str(raw or '').strip().upper()
    if candidate == 'UK': candidate='GB'
    if candidate in COUNTRIES: return candidate
    return label_country(fallback)


def flag(code: str) -> str:
    if code not in COUNTRIES or code == 'XK':
        return '🇽🇰' if code == 'XK' else '🌐'
    return ''.join(chr(0x1F1E6 + ord(x) - 65) for x in code)


def endpoint(host: object, port: object):
    try:
        host = str(host).strip().strip('[]')
        address = ipaddress.ip_address(host)
        port = int(port)
        if not address.is_global or not (1 <= port <= 65535):
            return None
        return host, port
    except (ValueError, TypeError):
        return None


def feed(url: str, max_bytes: int = 14_000_000) -> str:
    req=Request(url, headers={'User-Agent':'ProxyList-V06/1.0 (free-open-source-aggregator)'})
    with urlopen(req, timeout=35) as resp:
        data=resp.read(max_bytes+1)
    if len(data)>max_bytes: raise ValueError('Feed oltre limite dimensione')
    return data.decode('utf-8-sig',errors='replace')


def candidate(proto, host, port, country, origin, label='', latency=9999):
    norm = 'http' if proto in ('http', 'https') else str(proto).lower()
    if norm not in ('http','socks4','socks5'): return None
    ep=endpoint(host,port)
    if not ep: return None
    try: latency=float(latency)
    except (ValueError, TypeError): latency=9999
    return {'proto':norm,'ip':ep[0],'port':ep[1], 'country':cc(country, label),
            'origin':origin,'name':str(label)[:96],'latency':latency}


def parse_spys(text: str, socks: bool) -> list[dict]:
    entries=[]
    for line in text.splitlines():
        # Esempi ufficiali: 1.2.3.4:8080 US-H-S + / 1.2.3.4:1080 DE-H -
        m=re.match(r'^\s*(\d{1,3}(?:\.\d{1,3}){3}):(\d+)\s+([A-Z]{2})-([A-Z!\-]+)(?:\s+[+\-])?',line)
        if not m: continue
        host, port, country, quality=m.groups()
        if socks:
            # Il feed non dichiara il protocollo SOCKS: si provano entrambi.
            for proto in ('socks5','socks4'):
                c=candidate(proto,host,port,country,'SP','SPYS SOCKS')
                if c:entries.append(c)
        else:
            # -S nell'indicatore significa supporto HTTPS dichiarato.
            if '-S' not in line.split()[1]:continue
            c=candidate('http',host,port,country,'SP','SPYS HTTPS')
            if c:entries.append(c)
    return entries


def parse_csv_source(source: str, data: str) -> list[dict]:
    out=[]
    if source=='PF':
        for row in csv.reader(io.StringIO(data)):
            if len(row)<2:continue
            m=re.match(r'^(https?|socks4|socks5)://(\d{1,3}(?:\.\d{1,3}){3}):(\d+)$',row[0].strip(),re.I)
            if not m:continue
            c=candidate(m.group(1).lower(),m.group(2),m.group(3),row[1],'PF',row[2] if len(row)>2 else '')
            if c:out.append(c)
    else:
        for row in csv.DictReader(io.StringIO(data)):
            if source=='PS':
                proto=str(row.get('protocol','')).lower()
                c=candidate(proto,row.get('ip'),row.get('port'),row.get('country_code'),'PS',row.get('country',''),row.get('latency_ms'))
                if c:out.append(c)
            elif source=='HP':
                if row.get('alive','').lower()!='true':continue
                for proto in row.get('protocols','').lower().split('|'):
                    c=candidate(proto,row.get('ip'),row.get('port'),row.get('country'),'HP',row.get('city',''),row.get('latency_ms'))
                    if c:out.append(c)
    return out


def parse_monosans(data: str) -> list[dict]:
    rows=json.loads(data)
    if not isinstance(rows,list):raise ValueError('Monosans: JSON non lista')
    out=[]
    for row in rows:
        if not isinstance(row,dict):continue
        country=(row.get('geolocation') or {}).get('country') or {}
        c=candidate(row.get('protocol'),row.get('host'),row.get('port'),country.get('iso_code'),'MN','',row.get('timeout'))
        if c:out.append(c)
    return out


def parse_nodesradar(data: str) -> list[dict]:
    try: obj=json.loads(data)
    except json.JSONDecodeError: return []
    outs=obj.get('outbounds', []) if isinstance(obj,dict) else []
    out=[]
    for item in outs:
        if not isinstance(item,dict) or item.get('type') not in NR_TYPES:continue
        host=item.get('server')
        # Evita endpoint privati/localhost. I nomi DNS pubblici sono ammessi per V2Ray.
        if not isinstance(host,str) or not host.strip():continue
        if host.strip().lower() in ('localhost','127.0.0.1','::1'):continue
        try:
            ip=ipaddress.ip_address(host)
            if not ip.is_global:continue
        except ValueError:
            if len(host)>253 or '.' not in host or any(x in host for x in ['/', '@',' ']):continue
        try:
            p=int(item.get('server_port',0))
            if p<1 or p>65535:continue
        except (ValueError,TypeError):continue
        fixed=dict(item)
        fixed['server_port']=p
        out.append(fixed)
    return out


def recv_exact(sock, count):
    data=b''
    while len(data)<count:
        chunk=sock.recv(count-len(data))
        if not chunk: raise ConnectionError('Connessione chiusa')
        data+=chunk
    return data


def check_https(node:dict, timeout:float=4.5) -> bool:
    """Prova proxy -> www.example.com:443 -> TLS valido -> GET HTTPS -> HTTP response.
    Il test parte da GitHub Actions: NON certifica disponibilita dal telefono.
    """
    try:
        with socket.create_connection((node['ip'],node['port']),timeout=timeout) as s:
            s.settimeout(timeout)
            proto=node['proto']
            if proto=='http':
                s.sendall(f'CONNECT {TARGET}:443 HTTP/1.1\r\nHost: {TARGET}:443\r\nProxy-Connection: close\r\n\r\n'.encode('ascii'))
                reply=b''
                while b'\r\n\r\n' not in reply and len(reply)<8192:
                    part=s.recv(1024)
                    if not part:break
                    reply+=part
                if not re.search(rb'^HTTP/1\.[01] 200\b',reply):return False
            elif proto=='socks5':
                s.sendall(b'\x05\x01\x00')
                if recv_exact(s,2)!=b'\x05\x00':return False
                name=TARGET.encode('ascii')
                s.sendall(b'\x05\x01\x00\x03'+bytes([len(name)])+name+struct.pack('!H',PORT))
                head=recv_exact(s,4)
                if head[:2]!=b'\x05\x00':return False
                typ=head[3]
                n=4 if typ==1 else 16 if typ==4 else recv_exact(s,1)[0] if typ==3 else 0
                if not n:return False
                recv_exact(s,n+2)
            elif proto=='socks4':
                name=TARGET.encode('ascii')
                s.sendall(b'\x04\x01'+struct.pack('!H',PORT)+b'\x00\x00\x00\x01\x00'+name+b'\x00')
                res=recv_exact(s,8)
                if res[1]!=0x5a:return False
            else:return False
            ctx=ssl.create_default_context()
            with ctx.wrap_socket(s,server_hostname=TARGET) as tls:
                tls.settimeout(timeout)
                tls.sendall(f'GET / HTTP/1.1\r\nHost: {TARGET}\r\nConnection: close\r\n\r\n'.encode('ascii'))
                head=tls.recv(128)
                match=re.match(rb'HTTP/1\.[01] (\d{3})\b',head)
                return bool(match and 200<=int(match.group(1))<500)
    except (OSError,ssl.SSLError,ValueError,ConnectionError):
        return False


def proxy_key(node:dict):
    kind=str(node.get('type','')).lower()
    if kind=='socks': return ('socks',str(node.get('server','')).lower(),str(node.get('server_port')),str(node.get('version','5')))
    if kind=='http': return ('http',str(node.get('server','')).lower(),str(node.get('server_port')))
    return (kind,json.dumps({k:v for k,v in node.items() if k!='tag'},sort_keys=True,ensure_ascii=False))


def add_to_profile(doc:dict, accepted:list[dict], radar:list[dict]) -> Counter:
    nodes=doc.get('outbounds')
    if not isinstance(nodes,list):raise ValueError('outbounds mancante')
    selectors=[x for x in nodes if isinstance(x,dict) and x.get('type')=='selector' and x.get('tag')=='MEGA-SCELTA']
    if len(selectors)!=1:raise ValueError('Selector MEGA-SCELTA non trovato una sola volta')
    sel=selectors[0]
    seen={proxy_key(x) for x in nodes if isinstance(x,dict) and x.get('type')!='selector'}
    tags={x.get('tag') for x in nodes if isinstance(x,dict)}
    results=Counter()
    for candidate_node in accepted:
        protocol=candidate_node['proto']
        outbound={'type':'http','server':candidate_node['ip'],'server_port':candidate_node['port']} if protocol=='http' else {
            'type':'socks','server':candidate_node['ip'],'server_port':candidate_node['port'],'version':'4' if protocol=='socks4' else '5',
            **({'network':'tcp'} if protocol=='socks4' else {})}
        key=proxy_key(outbound)
        if key in seen:continue
        country=candidate_node['country']
        origin=candidate_node['origin']
        label=f'{protocol.upper()} {candidate_node["ip"]}:{candidate_node["port"]}'
        stem=f'{flag(country)} {country} | {origin} | {label}'
        tag=stem
        i=2
        while tag in tags:
            tag=f'{stem} #{i}';i+=1
        tags.add(tag)
        outbound['tag']=tag
        nodes.append(outbound)
        sel['outbounds'].append(tag)
        seen.add(key)
        results[origin]+=1
    for node in radar:
        origin='NR'
        country=label_country(node.get('tag',''))
        outbound=dict(node)
        label=str(outbound.pop('tag','NR V2Ray'))
        key=proxy_key(outbound)
        if key in seen:continue
        stem=f'{flag(country)} {country} | {origin} | {label[:75]}'
        tag=stem
        i=2
        while tag in tags:
            tag=f'{stem} #{i}';i+=1
        tags.add(tag)
        outbound['tag']=tag
        nodes.append(outbound)
        sel['outbounds'].append(tag)
        seen.add(key)
        results[origin]+=1
    return results


def parse_sources() -> tuple[list[dict],list[dict],dict[str,str]]:
    candidates=[]
    radar=[]
    statuses={}
    for origin in ('MN','PF','PS','HP','SP_HTTP','SP_SOCKS','NR'):
        try:
            contents=feed(URLS[origin])
            if origin=='MN': parsed=parse_monosans(contents)
            elif origin in ('PF','PS','HP'): parsed=parse_csv_source(origin,contents)
            elif origin.startswith('SP'): parsed=parse_spys(contents, origin=='SP_SOCKS')
            else:
                parsed=parse_nodesradar(contents)
                if len(parsed)>120:parsed=parsed[:120]
                radar=parsed
                statuses[origin]=f'Letti {len(parsed)} V2Ray (verifica fonte, non verificati localmente)'
                print('[V06]',origin,statuses[origin],flush=True)
                continue
            statuses[origin]=f'Letti {len(parsed)} candidati HTTP/SOCKS'
            candidates.extend(parsed)
            print('[V06]',origin,statuses[origin],flush=True)
        except Exception as exc:
            statuses[origin]=f'NON DISPONIBILE: {type(exc).__name__}: {exc}'
            print('[V06] AVVISO',origin,statuses[origin],flush=True)
    return candidates,radar,statuses


def choose_candidates(candidates:list[dict],existing:Counter,limit:int) -> list[dict]:
    # Privilegia paesi con pochi nodi e dati di latenza, evitando che US/BR monopolizzino.
    rank={ 'MN':0, 'HP':1, 'PS':2, 'PF':3, 'SP':4 }
    candidates.sort(key=lambda x:(min(existing.get(x['country'],9999),1000),rank.get(x['origin'],9),x['latency']))
    seen=set()
    percountry=Counter()
    picked=[]
    for c in candidates:
        k=(c['proto'],c['ip'],c['port'])
        if k in seen:continue
        seen.add(k)
        if percountry[c['country']]>=max(10,limit//30):continue
        percountry[c['country']]+=1
        picked.append(c)
        if len(picked)>=limit:break
    return picked


def totals(doc:dict)->Counter:
    ret=Counter()
    for x in doc.get('outbounds',[]):
        if not isinstance(x,dict) or x.get('type')=='selector':continue
        tag=str(x.get('tag',''))
        country=label_country(tag)
        if re.match(r'^🌐 ZZ\s*\|',tag):country='ZZ'
        ret[country]+=1
    return ret


def update_report(report:Path,doc:dict,stats:dict,accepted:Counter):
    text=report.read_text(encoding='utf-8')
    total=sum(1 for n in doc['outbounds'] if isinstance(n,dict) and n.get('type')!='selector')
    text=re.sub(r'(?m)^Nodi nel file Proxy_List\.json:.*$',f'Nodi nel file Proxy_List.json: {total}',text)
    if '=== V06 - NUOVE FONTI ===' in text:
        text=text.split('=== V06 - NUOVE FONTI ===')[0].rstrip()+'\n'
    appendix=['','=== V06 - NUOVE FONTI ===',
      'HTTP/SOCKS nuovi: verificati con TLS e richiesta HTTPS da GitHub Actions',
      'Questo NON prova il funzionamento dal telefono o in ogni nazione',
      'NodesRadar: verifica dichiarata dalla fonte; non verificata qui con client V2Ray',
      'GeoLite Data (campi Paese Monosans) di MaxMind: https://www.maxmind.com (CC BY-SA 4.0)',
    ]
    appendix.extend(f'{k}: {value}; aggiunti: {accepted.get(k.replace("SP_HTTP","SP").replace("SP_SOCKS","SP"),0) if not k.startswith("SP_") else "vedi SP"}' for k,value in stats.items())
    appendix.append(f'Nodi totali finali: {total}')
    report.write_text(text.rstrip()+'\n'+'\n'.join(appendix)+'\n',encoding='utf-8')


def self_test():
    assert label_country('🌐 ZZ | FNV | 🇰🇼 Kuwait')=='KW'
    assert label_country('🌐 ZZ | FNM | Seychelles')=='SC'
    assert label_country('🇺🇸 US | FNV | test')=='US'
    assert label_country('US')=='US'
    assert label_country('Server sconosciuto')=='ZZ'
    assert len(parse_spys('1.2.3.4:8080 US-H-S +\n2.2.2.2:8080 KR-H -',False))==1
    assert len(parse_spys('1.2.3.4:1080 US-H +',True))==2
    assert len(parse_csv_source('PF','socks5://8.8.8.8:1080,US,Unknown\n'))==1
    assert len(parse_csv_source('PS','protocol,ip,port,country,country_code\nsocks5,8.8.8.8,1080,US,US\n'))==1
    assert len(parse_csv_source('HP','ip,port,protocols,country,alive\n8.8.8.8,80,socks4|socks5,US,true\n'))==2
    node={'proto':'socks5','ip':'8.8.8.8','port':1080,'country':'KW','origin':'MN'}
    doc={'outbounds':[{'type':'selector','tag':'MEGA-SCELTA','outbounds':['original'],'default':'original'},
          {'type':'http','tag':'original','server':'9.9.9.9','server_port':443}]}
    counts=add_to_profile(doc,[node],[])
    assert counts['MN']==1
    assert doc['outbounds'][0]['outbounds'][-1].startswith('🇰🇼 KW | MN |')
    assert doc['outbounds'][0]['default']=='original'
    assert len(set(x['tag'] for x in doc['outbounds']))==len(doc['outbounds'])
    print('[OK] V06 AUTOTEST: Paesi, SPYS, CSV, deduplica, selector',flush=True)


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument('--config',default='.proxy-list-temp/Proxy_List.json')
    arg.add_argument('--report',default='.proxy-list-temp/RIEPILOGO_PAESI.txt')
    arg.add_argument('--self-test',action='store_true')
    arg.add_argument('--max-checks',type=int,default=700)
    arg.add_argument('--workers',type=int,default=48)
    args=arg.parse_args()
    if args.self_test:
        self_test();return 0
    config=Path(args.config)
    report=Path(args.report)
    if not config.is_file() or not report.is_file():
        arg.error('Config o riepilogo non trovati')
    doc=json.loads(config.read_text(encoding='utf-8'))
    existing=totals(doc)
    candidates,radar,status=parse_sources()
    checks=choose_candidates(candidates,existing,min(1400,max(1,args.max_checks)))
    print('[V06] Test HTTPS su',len(checks),'candidati; massimo 4.5s per richiesta',flush=True)
    accepted=[]
    passed=Counter()
    if checks:
        with ThreadPoolExecutor(max_workers=max(1,min(args.workers,64))) as pool:
            jobs={pool.submit(check_https,x):x for x in checks}
            for job in as_completed(jobs):
                c=jobs[job]
                try: good=job.result()
                except Exception:good=False
                if good:
                    accepted.append(c);passed[c['origin']]+=1
    print('[V06] Superati test HTTPS:',dict(passed),'totale',len(accepted),flush=True)
    inserted=add_to_profile(doc,accepted,radar)
    # Non pubblica niente se tutte le fonti aggiuntive sono fuori servizio:
    # conserva il JSON originario prodotto dal generatore (lo step Dart rimane valido).
    updated=sum(inserted.values())
    update_report(report,doc,status,inserted)
    if updated:
        config.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('[V06] Aggiunti:',dict(inserted),'totale:',updated,flush=True)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
