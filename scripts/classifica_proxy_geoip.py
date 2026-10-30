#!/usr/bin/env python3
"""Completa i Paesi ZZ in Proxy_List.json tramite GeoIP offline (solo IP del server).

Fonte: sapics/ip-location-db, server-country, PDDL v1.0.
Usa le etichette già pubblicate per ogni Paese come prioritarie: GeoIP è fallback.
Dipendenze: soltanto Python 3 (stdlib). Non modifica i file MEGA/Hiddify_IR.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from ipaddress import ip_address
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

GEOIP_BASE = 'https://github.com/sapics/ip-location-db/releases/download/latest'
DATABASES = {
    4: f'{GEOIP_BASE}/server-country-ipv4.csv',
    6: f'{GEOIP_BASE}/server-country-ipv6.csv',
}
ORIGINS = {'FVS', 'FNV', 'FNM', 'FNA', 'LITPORT', 'IR-MANUALE'}
TAG_PATTERN = re.compile(r'^🌐 ZZ \| ([^|]+) \| (.+)$')
COUNTRY_LINE = re.compile(r'^(\?\?|[A-Z]{2})\s{2,}(.+?)\s+(\d+)\s*$')
ARAB_COUNT_LINE = re.compile(r'^(?P<code>[A-Z]{2})(?P<between>\s+.*?\s+)(?P<count>\d+)(?P<tail> nodi \|.*)$')


def flag(code: str) -> str:
    return ''.join(chr(0x1F1E6 + ord(char) - ord('A')) for char in code)


def names_from_generator(path: Path) -> dict[str, str]:
    """Riusa l'elenco ufficiale dei Paesi del generatore Dart, senza duplicarlo."""
    if not path.is_file():
        raise FileNotFoundError(f'Manca {path}, impossibile verificare i codici ISO riconosciuti')
    data = path.read_text(encoding='utf-8')
    match = re.search(r'const knownCountries\s*=\s*<String,\s*String>\s*\{(.*?)\};', data, re.S)
    if not match:
        raise ValueError('Mappa knownCountries non trovata nel generatore Dart')
    result = dict(re.findall(r"'([A-Z]{2})'\s*:\s*'([^']+)'", match.group(1)))
    if not {'IT', 'US', 'IR', 'GB'}.issubset(result):
        raise ValueError('Mappa dei Paesi non valida: controllo di sicurezza fallito')
    return result


@dataclass
class GeoDb:
    starts: list[int]
    ends: list[int]
    codes: list[str]

    def get(self, number: int) -> str | None:
        pos = bisect_right(self.starts, number) - 1
        if pos >= 0 and number <= self.ends[pos]:
            return self.codes[pos]
        return None


def parse_database(rows, version: int, accepted: set[str]) -> GeoDb:
    starts: list[int] = []
    ends: list[int] = []
    codes: list[str] = []
    for raw in rows:
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        fields = [part.strip(' "\r') for part in raw.split(',')]
        if len(fields) < 3:
            continue
        start_text, end_text, code = fields[:3]
        if code not in accepted:
            continue
        try:
            start, end = ip_address(start_text), ip_address(end_text)
        except ValueError:
            continue
        if start.version != version or end.version != version or int(start) > int(end):
            continue
        starts.append(int(start))
        ends.append(int(end))
        codes.append(code)
    if len(starts) < 100:
        raise ValueError(f'Database IPv{version} incompleto: soltanto {len(starts)} intervalli')
    if any(starts[i] < starts[i-1] for i in range(1, len(starts))):
        records = sorted(zip(starts, ends, codes))
        starts, ends, codes = map(list, zip(*records))
    return GeoDb(starts, ends, codes)


def download_database(version: int, accepted: set[str]) -> GeoDb:
    url = DATABASES[version]
    req = Request(url, headers={'User-Agent': 'Proxy-List-GeoIP/1.0 (GitHub Actions)'})
    print(f'[GEOIP] Scarico IPv{version}: {url}', flush=True)
    with urlopen(req, timeout=90) as response:
        # 9 MB / 16 MB, lettura streaming in memoria temporanea; niente pacchetti Python.
        rows = (row.decode('utf-8-sig', errors='replace') for row in response)
        db = parse_database(rows, version, accepted)
    print(f'[GEOIP] IPv{version}: {len(db.starts)} intervalli geografici validi', flush=True)
    return db


def geolocate(server: object, databases: dict[int, GeoDb]) -> tuple[str | None, str]:
    if not isinstance(server, str) or not server.strip():
        return None, 'server_mancante'
    value = server.strip().strip('[]')
    try:
        ip = ip_address(value)
    except ValueError:
        # Non si geolocalizza il dominio con query DNS: CDN e proxy possono usare
        # risoluzioni diverse; una posizione indovinata non è affidabile.
        return None, 'hostname'
    if not ip.is_global:
        return None, 'non_pubblico'
    db = databases.get(ip.version)
    if db is None:
        return None, 'db_non_disponibile'
    return db.get(int(ip)), 'ip'


def classify(document: dict, databases: dict[int, GeoDb]) -> tuple[Counter, dict[str, str], Counter]:
    outbounds = document.get('outbounds')
    if not isinstance(outbounds, list):
        raise ValueError('JSON non sing-box: outbounds non è una lista')
    nodes = [x for x in outbounds if isinstance(x, dict) and x.get('type') != 'selector']
    all_tags = [x.get('tag') for x in outbounds if isinstance(x, dict)]
    if len(all_tags) != len(set(all_tags)):
        raise ValueError('Tag duplicati nel JSON prima della riclassificazione')
    # Riserviamo i tag che rimarranno invariati; nessuna collisione dopo la conversione.
    used = {str(tag) for tag in all_tags if isinstance(tag, str) and not TAG_PATTERN.match(tag)}
    remap: dict[str, str] = {}
    reasons: Counter = Counter()
    new_countries: Counter = Counter()
    for node in nodes:
        original_tag = node.get('tag')
        if not isinstance(original_tag, str):
            continue
        match = TAG_PATTERN.match(original_tag)
        if not match:
            continue
        code, reason = geolocate(node.get('server'), databases)
        if code is None:
            reasons[reason] += 1
            continue
        origin, label = match.groups()
        if origin.strip() not in ORIGINS:
            reasons['origine_sconosciuta'] += 1
            continue
        stem = f'{flag(code)} {code} | {origin} | {label}'
        tag = stem
        suffix = 2
        while tag in used:
            tag = f'{stem} #{suffix}'
            suffix += 1
        used.add(tag)
        remap[original_tag] = tag
        node['tag'] = tag
        new_countries[code] += 1
    # Aggiorna tutte le referenze: selector contiene i vecchi nomi e deve restare valido.
    for item in outbounds:
        if not isinstance(item, dict):
            continue
        if item.get('type') == 'selector':
            if isinstance(item.get('outbounds'), list):
                item['outbounds'] = [remap.get(t, t) for t in item['outbounds']]
            if isinstance(item.get('default'), str):
                item['default'] = remap.get(item['default'], item['default'])
    return new_countries, remap, reasons


def update_report(path: Path, document: dict, new_countries: Counter, reasons: Counter, status: dict[int, bool]) -> None:
    if not path.is_file():
        raise FileNotFoundError(f'Report mancante: {path}')
    content = path.read_text(encoding='utf-8')
    # Rielabora il riepilogo dai tag finali, non dai vecchi contatori.
    counts: Counter = Counter()
    for item in document['outbounds']:
        if not isinstance(item, dict) or item.get('type') == 'selector':
            continue
        tag = item.get('tag', '')
        match = re.match(r'^(?:🌐 ZZ|[^ ]+ ([A-Z]{2})) \| ', str(tag))
        if match:
            counts[match.group(1) or '??'] += 1
    names = names_from_generator(Path('scripts/genera_proxy_list.dart'))
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith('Nazioni etichettate:'):
            lines[index] = f'Nazioni etichettate: {sum(1 for cc, qty in counts.items() if cc != "??" and qty > 0)}'
        match = ARAB_COUNT_LINE.match(line)
        if match and 'FastNodes dedicato:' in line:
            cc = match.group('code')
            lines[index] = f'{cc}{match.group("between")}{counts.get(cc, 0)}{match.group("tail")}'
    # Sostituiamo solo il blocco geografico: tra MODALITA e la sezione Stati arabi.
    first = next((i for i, line in enumerate(lines) if line.startswith('MODALITA:')), None)
    last = next((i for i, line in enumerate(lines) if line.startswith('=== TUTTI I 22 PAESI ARABI')), None)
    if first is None or last is None or last <= first:
        raise ValueError('Formato riepilogo cambiato: impossibile aggiornare il blocco Paesi')
    section = [f'??  Sconosciuti                {counts.get("??", 0)}'] if counts.get('??') else []
    for cc in sorted(code for code in counts if code != '??'):
        section.append(f'{cc}  {names.get(cc, "Paese " + cc):<27} {counts[cc]}')
    lines = lines[:first+1] + [''] + section + [''] + lines[last:]
    # Elimina eventuale sezione GeoIP precedente (idempotenza).
    header = '=== GEOIP - COMPLETAMENTO AUTOMATICO PAESI ==='
    try:
        pos = lines.index(header)
        lines = lines[:pos]
    except ValueError:
        pass
    lines.extend(['', header,
        'Banca dati: sapics/ip-location-db / server-country (PDDL v1.0)',
        'Verifica: localizzazione IP del SERVER, NON dell’IP di uscita VPN',
        f'IPv4 disponibile: {"SI" if status.get(4) else "NO"}',
        f'IPv6 disponibile: {"SI" if status.get(6) else "NO"}',
        f'Proxy prima ZZ riclassificati: {sum(new_countries.values())}',
        f'Proxy ancora non classificati: {counts.get("??", 0)}',
        'Nazioni assegnate mediante GeoIP: ' + (', '.join(f'{cc}={n}' for cc,n in sorted(new_countries.items())) or 'nessuna'),
        'Motivi non classificati: ' + (', '.join(f'{reason}={n}' for reason,n in sorted(reasons.items())) or 'nessuno'),
        'Nota: per hostname o dati ambigui non viene inventato alcun Paese.',
    ])
    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def self_test() -> None:
    # Evita la rete, prova cache, IPv4/IPv6, collisioni, selettori e priorità Paesi noti.
    v4 = GeoDb([int(ip_address('8.8.8.0'))], [int(ip_address('8.8.8.255'))], ['US'])
    v6 = GeoDb([int(ip_address('2001:4860::'))], [int(ip_address('2001:4860:ffff:ffff:ffff:ffff:ffff:ffff'))], ['US'])
    tag1 = '🌐 ZZ | FNM | demo'
    tag2 = '🌐 ZZ | FNV | prova IPv6'
    doc = {'outbounds': [
        {'type': 'selector', 'tag': 'MEGA-SCELTA', 'outbounds': [tag1, tag2, '🇮🇹 IT | FVS | valido'], 'default': tag1},
        {'type': 'http', 'tag': tag1, 'server': '8.8.8.8', 'server_port': 80},
        {'type': 'socks', 'tag': tag2, 'server': '2001:4860::8888', 'server_port': 1080},
        {'type': 'http', 'tag': '🇮🇹 IT | FVS | valido', 'server': '8.8.8.8', 'server_port': 80},
    ]}
    result, mapping, reasons = classify(doc, {4:v4, 6:v6})
    assert result == {'US': 2}, (result, reasons)
    assert doc['outbounds'][0]['default'] == mapping[tag1]
    assert doc['outbounds'][0]['outbounds'][1] == mapping[tag2]
    assert doc['outbounds'][-1]['tag'] == '🇮🇹 IT | FVS | valido'
    assert geolocate('example.com', {4:v4}) == (None, 'hostname')
    assert geolocate('192.168.1.1', {4:v4}) == (None, 'non_pubblico')
    print('[OK] Autotest GeoIP: IPv4, IPv6, tag, selector, Paesi originali')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='.proxy-list-temp/Proxy_List.json')
    parser.add_argument('--report', default='.proxy-list-temp/RIEPILOGO_PAESI.txt')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    config = Path(args.config)
    if not config.is_file():
        parser.error(f'Manca il file {config}')
    # Nomi da Dart: vietato introdurre codici Paese non supportati dal generatore/app.
    countries = names_from_generator(Path('scripts/genera_proxy_list.dart'))
    document = json.loads(config.read_text(encoding='utf-8'))
    status: dict[int, bool] = {}
    databases: dict[int, GeoDb] = {}
    for version in (4, 6):
        try:
            databases[version] = download_database(version, set(countries))
            status[version] = True
        except Exception as exc:
            status[version] = False
            print(f'[AVVISO] GeoIP IPv{version} non disponibile: {exc}', file=sys.stderr)
    if not databases:
        print('[AVVISO] Database GeoIP non disponibili: conservo senza modifiche i Paesi originali', file=sys.stderr)
    codes, mapping, reasons = classify(document, databases)
    if mapping:
        # Scrittura solo dopo avere validato le referenze del selector.
        tags = {x.get('tag') for x in document['outbounds'] if isinstance(x, dict)}
        for node in document['outbounds']:
            if node.get('type') == 'selector':
                assert all(t in tags for t in node.get('outbounds', [])), 'Selector con tag mancante'
        temp = config.with_name(config.name + '.tmp')
        temp.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(config)
    update_report(Path(args.report), document, codes, reasons, status)
    print(f'[GEOIP] Riclassificati {len(mapping)} proxy; senza Paese {sum(reasons.values())}')
    print(f'[GEOIP] Nuovi Paesi: {dict(sorted(codes.items()))}')
    print('[GEOIP] File generato e riepilogo coerenti; nessun file MEGA modificato')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
