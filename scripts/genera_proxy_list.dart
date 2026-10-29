// Hiddify ITA MOD - Proxy List v0.4: UN SOLO JSON mondiale e tutti i 22 Paesi arabi
// Nessuna dipendenza esterna: utilizza il Dart incluso in Flutter 3.38.5.
// Fonti:
//  - https://github.com/Au1rxx/free-vpn-subscriptions
//  - https://github.com/rtwo2/FastNodes
//  - https://github.com/litportnet/free-proxy-list (proxy HTTP-HTTPS e SOCKS4/5)
//  - proxy/Hiddify_IR.json (se presente, elenco manuale preservato)
// Nota: paese indicativo, non verifica l'IP di uscita.
import 'dart:convert';
import 'dart:io';

const freeBase = 'https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output';
const fastBase = 'https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub';
const litportAll = 'https://raw.githubusercontent.com/litportnet/free-proxy-list/live/proxies/all.json';

// 22 Stati membri della Lega Araba (riconoscimento dei nomi, non prova di presenza server).
const arabCountries = <String>[
  'AE','BH','DZ','DJ','EG','IQ','JO','KM','KW','LB','LY',
  'MA','MR','OM','PS','QA','SA','SD','SO','SY','TN','YE',
];
const knownCountries = <String, String>{
  'AD':'Andorra','AE':'Emirati Arabi Uniti','AF':'Afghanistan','AL':'Albania',
  'AM':'Armenia','AR':'Argentina','AT':'Austria','AU':'Australia','AZ':'Azerbaigian',
  'BA':'Bosnia','BD':'Bangladesh','BE':'Belgio','BG':'Bulgaria','BH':'Bahrein',
  'BO':'Bolivia','BR':'Brasile','BY':'Bielorussia','CA':'Canada','CH':'Svizzera',
  'CL':'Cile','CN':'Cina','CO':'Colombia','CR':'Costa Rica','CY':'Cipro',
  'CZ':'Repubblica Ceca','DE':'Germania','DJ':'Gibuti','DK':'Danimarca','DO':'Repubblica Dominicana',
  'DZ':'Algeria','EC':'Ecuador','EE':'Estonia','EG':'Egitto','ES':'Spagna',
  'FI':'Finlandia','FR':'Francia','GB':'Regno Unito','GE':'Georgia','GH':'Ghana',
  'GR':'Grecia','HK':'Hong Kong','HR':'Croazia','HU':'Ungheria','ID':'Indonesia',
  'IE':'Irlanda','IL':'Israele','IN':'India','IQ':'Iraq','IR':'Iran','IS':'Islanda',
  'IT':'Italia','JO':'Giordania','JP':'Giappone','KE':'Kenya','KG':'Kirghizistan','KM':'Comore','KR':'Corea del Sud',
  'KW':'Kuwait','KZ':'Kazakistan','LB':'Libano','LK':'Sri Lanka','LT':'Lituania','LU':'Lussemburgo','LY':'Libia',
  'LV':'Lettonia','MA':'Marocco','MD':'Moldavia','ME':'Montenegro','MK':'Macedonia del Nord','MR':'Mauritania',
  'MM':'Myanmar','MN':'Mongolia','MX':'Messico','MY':'Malaysia','NG':'Nigeria',
  'NL':'Paesi Bassi','NO':'Norvegia','NP':'Nepal','NZ':'Nuova Zelanda','OM':'Oman',
  'PA':'Panama','PE':'Peru','PH':'Filippine','PK':'Pakistan','PL':'Polonia','PS':'Palestina',
  'PT':'Portogallo','PY':'Paraguay','QA':'Qatar','RO':'Romania','RS':'Serbia',
  'RU':'Russia','SA':'Arabia Saudita','SD':'Sudan','SE':'Svezia','SG':'Singapore','SO':'Somalia',
  'SI':'Slovenia','SK':'Slovacchia','SY':'Siria','TH':'Thailandia','TN':'Tunisia',
  'TR':'Turchia','TW':'Taiwan','UA':'Ucraina','US':'Stati Uniti',
  'UY':'Uruguay','UZ':'Uzbekistan','VE':'Venezuela','VN':'Vietnam','YE':'Yemen','ZA':'Sudafrica',
};

const aliases = <String,String>{
  'iran':'IR', 'tehran':'IR','teheran':'IR', 'iranian':'IR',
  'italy':'IT','italia':'IT','milano':'IT','rome':'IT',
  'germany':'DE','frankfurt':'DE','deutschland':'DE',
  'japan':'JP','tokyo':'JP','osaka':'JP',
  'united states':'US','usa':'US','america':'US','new york':'US',
  'united kingdom':'GB','great britain':'GB','london':'GB','britain':'GB',
  'france':'FR','paris':'FR','spain':'ES',
  'netherlands':'NL','holland':'NL','amsterdam':'NL',
  'switzerland':'CH','china':'CN','russia':'RU','moscow':'RU',
  'canada':'CA','brazil':'BR','brasil':'BR','singapore':'SG',
  'turkey':'TR','turkiye':'TR','korea':'KR','india':'IN',
  'australia':'AU','sydney':'AU','hong kong':'HK',
  'poland':'PL','taiwan':'TW','thailand':'TH','indonesia':'ID',
  'finland':'FI','ukraine':'UA','austria':'AT','portugal':'PT',
  'sweden':'SE','norway':'NO','belgium':'BE','ireland':'IE',
  'romania':'RO','serbia':'RS','bulgaria':'BG','czechia':'CZ',
  'saudi arabia':'SA','united arab emirates':'AE','uae':'AE',
  'dubai':'AE','abu dhabi':'AE','emirates':'AE',
  'kuwait':'KW','qatar':'QA','doha':'QA','bahrain':'BH','manama':'BH',
  'oman':'OM','muscat':'OM','yemen':'YE','sanaa':'YE',
  'iraq':'IQ','baghdad':'IQ','jordan':'JO','amman':'JO',
  'lebanon':'LB','beirut':'LB','syria':'SY','damascus':'SY',
  'palestine':'PS','ramallah':'PS',
  'egypt':'EG','cairo':'EG','libya':'LY','tripoli':'LY',
  'tunisia':'TN','tunis':'TN','algeria':'DZ','algiers':'DZ',
  'morocco':'MA','maroc':'MA','casablanca':'MA','mauritania':'MR',
  'sudan':'SD','khartoum':'SD','somalia':'SO','mogadishu':'SO',
  'djibouti':'DJ','comoros':'KM',
  'south africa':'ZA','argentina':'AR','mexico':'MX',
};

String flagFor(String code) {
  if (code.length != 2 || !knownCountries.containsKey(code)) return '🌐';
  return String.fromCharCodes([
    0x1f1e6 + code.codeUnitAt(0) - 65,
    0x1f1e6 + code.codeUnitAt(1) - 65,
  ]);
}

String countryFromLabel(String text) {
  final chars = text.runes.toList();
  for (var i=0; i+1<chars.length; i++) {
    final a=chars[i], b=chars[i+1];
    if (a>=0x1f1e6 && a<=0x1f1ff && b>=0x1f1e6 && b<=0x1f1ff) {
      final code = String.fromCharCodes([65+a-0x1f1e6,65+b-0x1f1e6]);
      final fixed = code == 'UK' ? 'GB' : code;
      if (knownCountries.containsKey(fixed)) return fixed;
    }
  }
  final lower=text.toLowerCase();
  for (final entry in aliases.entries) {
    if (RegExp('(^|[^a-z])${RegExp.escape(entry.key)}([^a-z]|\$)').hasMatch(lower)) {
      return entry.value;
    }
  }
  for (final code in knownCountries.keys) {
    if (RegExp('(^|[^a-z])${code.toLowerCase()}([^a-z]|\$)').hasMatch(lower)) return code;
  }
  return '??';
}

String value(dynamic item, [String fallback='']) => item == null ? fallback : item.toString().trim();
int number(dynamic v, [int orElse=0]) => int.tryParse(value(v)) ?? orElse;
bool truthy(dynamic v) => const ['1','true','yes','on'].contains(value(v).toLowerCase());
String shortLabel(String input) {
  var text = input.replaceAll(RegExp(r'[\r\n\t]'), ' ').trim();
  text = text.replaceAll(RegExp(r'\s+'), ' ');
  return text.length > 85 ? '${text.substring(0,85)}…' : text;
}
String decodedFragment(Uri uri) {
  try { return Uri.decodeComponent(uri.fragment); } catch (_) { return uri.fragment; }
}

Map<String,dynamic>? extractTransport(String transport, String host, String path, String service) {
  switch (transport.toLowerCase()) {
    case '': case 'tcp': case 'none': case 'raw': return null;
    case 'ws':
      return {'type':'ws', 'path':path.isEmpty?'/':path, if(host.isNotEmpty) 'headers':{'Host':host}};
    case 'grpc':
      return {'type':'grpc','service_name':service};
    case 'http': case 'h2':
      return {'type':'http','path':path.isEmpty?'/':path,if(host.isNotEmpty)'host':[host]};
    default: return {'unsupported':transport};
  }
}

Map<String,dynamic>? tlsFromParams(Map<String,String> q, String security, String server) {
  final type=security.toLowerCase();
  if (type != 'tls' && type != 'reality') return null;
  final tls=<String,dynamic>{'enabled':true};
  final sni=value(q['sni'], server);
  if(sni.isNotEmpty) tls['server_name']=sni;
  if(truthy(q['allowInsecure']) || truthy(q['insecure'])) tls['insecure']=true;
  final fingerprint=value(q['fp']);
  if (fingerprint.isNotEmpty && fingerprint != 'none') tls['utls']={'enabled':true,'fingerprint':fingerprint};
  if (type=='reality') {
    final pbk=value(q['pbk']);
    if(pbk.isEmpty) return null;
    tls['reality']={'enabled':true,'public_key':pbk,
      if(value(q['sid']).isNotEmpty) 'short_id':q['sid']};
  }
  final alpn=value(q['alpn']);
  if(alpn.isNotEmpty) tls['alpn']=alpn.split(',');
  return tls;
}

Map<String,dynamic>? uriToOutbound(String raw) {
  try {
    final line=raw.trim();
    if(line.isEmpty || line.startsWith('#')) return null;
    final scheme = line.split('://').first.toLowerCase();
    if (scheme=='vmess') {
      var b64=line.substring(line.indexOf('://')+3).split('#').first;
      b64=base64.normalize(b64.replaceAll('-', '+').replaceAll('_','/'));
      final obj=jsonDecode(utf8.decode(base64.decode(b64)));
      if(obj is! Map) return null;
      final o=Map<String,dynamic>.from(obj);
      final server=value(o['add']), port=number(o['port']), uuid=value(o['id']);
      if(server.isEmpty || port<=0 || uuid.isEmpty) return null;
      final transport=extractTransport(value(o['net'],'tcp'),value(o['host']),value(o['path']),value(o['path']));
      if(transport?.containsKey('unsupported') == true) return null;
      final tlsEnabled=value(o['tls']).toLowerCase()=='tls';
      final tls=tlsEnabled? <String,dynamic>{'enabled':true,
        if(value(o['sni']).isNotEmpty) 'server_name':o['sni']}:null;
      return {'type':'vmess','server':server,'server_port':port,'uuid':uuid,
        'security': value(o['scy'],'auto'),'alter_id':number(o['aid']),
        if(tls!=null)'tls':tls,if(transport!=null)'transport':transport,
        '_label':value(o['ps'],'VMess $server:$port')};
    }
    final uri=Uri.parse(line);
    final q=uri.queryParameters;
    final server=uri.host;
    final port=uri.hasPort?uri.port:0;
    if(server.isEmpty || port<=0 || port>65535) return null;
    final label=decodedFragment(uri).trim();
    final display=label.isEmpty ? '$scheme $server:$port' : label;
    final auth=uri.userInfo;
    final base={'server':server,'server_port':port,'_label':display};
    if(scheme=='vless') {
      final uuid=auth.split(':').first;
      if(uuid.isEmpty) return null;
      final security=value(q['security'],'none');
      final tls=tlsFromParams(q,security,server);
      if(security=='reality' && tls==null) return null;
      final trans=extractTransport(value(q['type'],'tcp'),value(q['host']),value(q['path']),value(q['serviceName']));
      if(trans?.containsKey('unsupported')==true) return null;
      return {...base,'type':'vless','uuid':uuid,
        if(value(q['flow']).isNotEmpty)'flow':q['flow'],
        if(tls!=null)'tls':tls,if(trans!=null)'transport':trans};
    }
    if(scheme=='trojan') {
      if(auth.isEmpty) return null;
      final tls=tlsFromParams(q,'tls',server);
      final trans=extractTransport(value(q['type'],'tcp'),value(q['host']),value(q['path']),value(q['serviceName']));
      if(trans?.containsKey('unsupported')==true) return null;
      return {...base,'type':'trojan','password':auth,
        if(tls!=null)'tls':tls,if(trans!=null)'transport':trans};
    }
    if(scheme=='hy2' || scheme=='hysteria2') {
      final tls=tlsFromParams(q,'tls',server);
      if(auth.isEmpty) return null;
      return {...base,'type':'hysteria2','password':auth,'tls':tls};
    }
    if(scheme=='tuic') {
      final authParts=auth.split(':');
      if(authParts.length<2 || authParts[0].isEmpty || authParts[1].isEmpty) return null;
      final tls=tlsFromParams(q,'tls',server);
      return {...base,'type':'tuic','uuid':authParts[0],
        'password':authParts.sublist(1).join(':'),'tls':tls,
        if(value(q['congestion_control']).isNotEmpty)'congestion_control':q['congestion_control']};
    }
    if(scheme=='ss') {
      // Formati SIP002: ss://base64(method:password)@host:port oppure metodo:password@host:port
      var credential=auth;
      if(!credential.contains(':')) {
        try {credential=utf8.decode(base64.decode(base64.normalize(credential)));}
        catch (_) {return null;}
      }
      final colon=credential.indexOf(':');
      if(colon<=0) return null;
      final method=credential.substring(0,colon), pass=credential.substring(colon+1);
      if(pass.isEmpty || q.containsKey('plugin')) return null;
      return {...base,'type':'shadowsocks','method':method,'password':pass};
    }
    if(scheme=='socks' || scheme=='socks5') {
      final parts=auth.split(':');
      return {...base,'type':'socks','version':'5',
        if(parts.isNotEmpty && parts[0].isNotEmpty)'username':parts[0],
        if(parts.length>1)'password':parts.sublist(1).join(':')};
    }
    return null;
  } catch (_) {return null;}
}

dynamic canonicalJson(dynamic input) {
  if (input is Map) {
    final keys=input.keys.map((e)=>e.toString()).toList()..sort();
    return {for (final key in keys) key:canonicalJson(input[key])};
  }
  if (input is List) return input.map(canonicalJson).toList();
  return input;
}

class NodeCollector {
  final nodes=<Map<String,dynamic>>[];
  final keys=<String>{};
  final tags=<String>{};
  final countries=<String,int>{};
  final origins=<String,int>{};
  final nodeCountries=<String,String>{};
  int duplicates=0;
  int invalid=0;

  bool add(Map<String,dynamic> original, String origin, String country, String originalName,
      {int? countryLimit, String? limitOrigin}) {
    final cc=knownCountries.containsKey(country)?country:'??';
    if(countryLimit!=null && (origins['$limitOrigin/$cc']??0)>=countryLimit) return false;
    final node=Map<String,dynamic>.from(original);
    node.remove('_label');
    node.remove('tag');
    if(!node.containsKey('server') || !node.containsKey('server_port')) {invalid++;return false;}
    final key=jsonEncode(canonicalJson(node)); // dedup stabile anche se i campi sono ordinati diversamente
    if(!keys.add(key)) {duplicates++;return false;}
    final flag=flagFor(cc);
    final label=shortLabel(originalName);
    final stem='$flag ${cc=='??'?'ZZ':cc} | $origin | $label';
    var tag=stem;
    var num=2;
    while(!tags.add(tag)) {tag='$stem #${num++}';}
    node['tag']=tag;
    nodes.add(node);
    nodeCountries[tag]=cc;
    countries[cc]=(countries[cc]??0)+1;
    origins[origin]=(origins[origin]??0)+1;
    if(limitOrigin!=null) origins['$limitOrigin/$cc']=(origins['$limitOrigin/$cc']??0)+1;
    return true;
  }
}

String? parseTagCountry(Map<String,dynamic> item, Map<String,String> countryByTag) {
  final tag=value(item['tag']);
  return countryByTag[tag];
}

Future<String> httpText(HttpClient client, String url, {Duration timeout=const Duration(seconds:100)}) async {
  final req=await client.getUrl(Uri.parse(url)).timeout(timeout);
  req.headers.set(HttpHeaders.userAgentHeader,'Hiddify-ITA-MOD-ProxyList/0.4');
  final response=await req.close().timeout(timeout);
  if(response.statusCode!=200) {
    await response.drain<void>();
    throw HttpException('HTTP ${response.statusCode} per $url');
  }
  return response.transform(utf8.decoder).join().timeout(timeout);
}

// Litport: il campo `https` indica che il proxy HTTP accetta CONNECT verso
// destinazioni HTTPS. Non significa TLS fra client e proxy.
// SOCKS4 e SOCKS5 supportano TCP; il SOCKS4 viene limitato esplicitamente a TCP.
Map<String,dynamic>? litportToOutbound(Map<String,dynamic> item, DateTime now) {
  final protocol=value(item['protocol']).toLowerCase();
  final ip=value(item['ip']);
  final parsed=InternetAddress.tryParse(ip);
  final port=number(item['port']);
  if(parsed==null || parsed.isLoopback || parsed.isLinkLocal || parsed.isMulticast ||
      port<1 || port>65535) return null;
  final checked=DateTime.tryParse(value(item['last_checked']));
  if(checked==null) return null;
  final age=now.toUtc().difference(checked.toUtc());
  if(age>const Duration(hours:3) || age< const Duration(minutes:-10)) return null;
  if(protocol=='http') {
    if(item['https']!=true) return null;
    return {'type':'http','server':ip,'server_port':port};
  }
  if(protocol=='socks4') {
    return {'type':'socks','server':ip,'server_port':port,'version':'4','network':'tcp'};
  }
  if(protocol=='socks5') {
    return {'type':'socks','server':ip,'server_port':port,'version':'5'};
  }
  return null;
}

// Conserva i proxy Litport già pubblicati se la fonte GitHub `live`
// è temporaneamente irraggiungibile. Non ricarica in memoria tutti gli altri nodi.
Future<int> recoverPreviousLitport(NodeCollector collector) async {
  final file=File('proxy/Proxy_List.json');
  if(!await file.exists()) return 0;
  final old=jsonDecode(await file.readAsString());
  if(old is! Map || old['outbounds'] is! List) return 0;
  var added=0;
  for(final entry in (old['outbounds'] as List).whereType<Map>()) {
    final tag=value(entry['tag']);
    if(!tag.contains(' | LITPORT | ')) continue;
    final node=Map<String,dynamic>.from(entry);
    final cc=countryFromLabel(tag);
    final label=tag.split(' | LITPORT | ').last;
    if(collector.add(node,'LITPORT',cc,label)) added++;
  }
  return added;
}

// Integra tutti i proxy Litport correnti idonei a HTTPS o SOCKS;
// nessuna soglia artificiale sui Paesi: se c'è un proxy in Kuwait,
// Siria, Libia, ecc. è incluso al pari degli altri.
Future<(int,int,String)> loadLitport(HttpClient http, NodeCollector collector) async {
  try {
    final parsed=jsonDecode(await httpText(http,litportAll,timeout:const Duration(minutes:2)));
    if(parsed is! List || parsed.length<20) {
      throw StateError('Feed Litport troppo piccolo o formato cambiato');
    }
    final now=DateTime.now().toUtc();
    var converted=0, skipped=0;
    for(final record in parsed) {
      if(record is! Map) {skipped++;continue;}
      final obj=Map<String,dynamic>.from(record);
      final outbound=litportToOutbound(obj,now);
      if(outbound==null) {skipped++;continue;}
      final cc=value(obj['country']).toUpperCase();
      final code=knownCountries.containsKey(cc)?cc:'??';
      final type=value(obj['protocol']).toUpperCase();
      final label='$type | ${value(obj['ip'])}:${number(obj['port'])}';
      if(collector.add(outbound,'LITPORT',code,label)) converted++;
    }
    if(converted<1) throw StateError('Nessun proxy Litport valido');
    print('Fonte Litport: $converted nodi nuovi, $skipped non idonei (es. HTTP senza HTTPS o test scaduto)');
    return (converted,skipped,'LIVE');
  } catch(err) {
    print('  AVVISO: Litport live non disponibile: $err');
    final recovered=await recoverPreviousLitport(collector);
    if(recovered==0) {
      // Protezione: evita una pubblicazione che cancelli la fonte Litport
      // senza che esista già un elenco precedente da conservare.
      throw StateError('Litport non disponibile e nessun backup in proxy/Proxy_List.json');
    }
    print('  Ripristinati $recovered nodi Litport dal JSON pubblico precedente.');
    return (recovered,0,'RECUPERO DAL FILE PRECEDENTE');
  }
}

// Mantiene i cinque proxy originali (e quelli che l'utente aggiungerà)
// nel file proxy/Hiddify_IR.json. Questo non sostituisce la fonte Litport live.
Future<int> addManualIran(NodeCollector collector) async {
  final file=File('proxy/Hiddify_IR.json');
  if(!await file.exists()) {
    print('  File Hiddify_IR.json assente: nessun nodo manuale aggiunto.');
    return 0;
  }
  final data=jsonDecode(await file.readAsString());
  if(data is! Map || data['outbounds'] is! List) {
    throw FormatException('proxy/Hiddify_IR.json: formato outbounds non valido');
  }
  var added=0;
  for(final entry in (data['outbounds'] as List).whereType<Map>()) {
    final node=Map<String,dynamic>.from(entry);
    final typ=value(node['type']);
    const accepted={'vless','vmess','trojan','shadowsocks','hysteria2','tuic','http','socks'};
    if(!accepted.contains(typ) || value(node['server']).isEmpty ||
       number(node['server_port'])<1 || number(node['server_port'])>65535) continue;
    node['server_port']=number(node['server_port']);
    final originalTag=value(node['tag']);
    final cc=countryFromLabel(originalTag);
    final label=originalTag.isNotEmpty ? originalTag :
      '$typ ${value(node['server'])}:${number(node['server_port'])}';
    if(collector.add(node,'IR-MANUALE',cc=='??'?'IR':cc,label)) added++;
  }
  return added;
}

Future<void> writeConfig(String filename, List<Map<String,dynamic>> nodes) async {
  if(nodes.isEmpty) throw StateError('Nessun server convertibile');
  final sorted=[...nodes]..sort((a,b)=>value(a['tag']).compareTo(value(b['tag'])));
  final tagList=sorted.map((x)=>x['tag'] as String).toList(growable:false);
  // Selector: il profilo contiene solo nodi realmente importati dalle fonti.
  final json={'outbounds':[
    {'type':'selector','tag':'MEGA-SCELTA','outbounds':tagList,'default':tagList.first},
    ...sorted,
  ],'route':{'final':'MEGA-SCELTA'}};
  final path=File(filename);
  await path.parent.create(recursive:true);
  await path.writeAsString(const JsonEncoder.withIndent('  ').convert(json),flush:true);
  print('[OK] ${path.path}: ${nodes.length} nodi, ${(await path.length()/1048576).toStringAsFixed(2)} MiB');
}

Future<void> selfTest() async {
  const sample='vless://11111111-1111-4111-8111-111111111111@test.example:443?security=reality&pbk=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&fp=chrome&sni=example.com&type=tcp#%F0%9F%87%AE%F0%9F%87%B7%20Iran';
  final v=uriToOutbound(sample);
  if(v==null || v['type']!='vless' || countryFromLabel(value(v['_label']))!='IR') {
    throw StateError('Conversione VLESS/paese non valida');
  }
  final x=uriToOutbound('trojan://password@host.example:443?security=tls&type=ws&path=%2Fvpn#%F0%9F%87%AE%F0%9F%87%B9%20Italia');
  if(x==null || x['transport']?['type']!='ws' || countryFromLabel(value(x['_label']))!='IT') {
    throw StateError('Conversione Trojan/paese non valida');
  }
  final ss=uriToOutbound('ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@example.com:8388#Japan');
  if(ss==null || ss['type']!='shadowsocks' || countryFromLabel(value(ss['_label']))!='JP'){
    throw StateError('Conversione Shadowsocks non valida');
  }
  for(final cc in arabCountries) {
    if(!knownCountries.containsKey(cc)) throw StateError('Nazione araba senza riconoscimento: $cc');
    if(countryFromLabel('${flagFor(cc)} $cc')!=cc) {
      throw StateError('Bandiera nazione araba non riconosciuta: $cc');
    }
  }
  final now=DateTime.utc(2026,10,29,15,0);
  final demo={'protocol':'http','ip':'46.209.30.11','port':8080,
    'last_checked':'2026-10-29T14:50:00Z','country':'ir','https':true};
  if(litportToOutbound(demo,now)?['type']!='http' ||
      litportToOutbound({...demo,'https':false},now)!=null ||
      litportToOutbound({...demo,'protocol':'socks4','https':false},now)?['version']!='4' ||
      litportToOutbound({...demo,'protocol':'socks5','https':false},now)?['version']!='5' ||
      litportToOutbound({...demo,'last_checked':'2026-10-28T03:00:00Z'},now)!=null) {
    throw StateError('Autotest conversione Litport fallito');
  }
  if(countryFromLabel('Dubai VPN')!='AE' || countryFromLabel('Kuwait')!='KW') {
    throw StateError('Alias Paesi arabi non funzionanti');
  }
  print('[OK] Autotest VLESS/Trojan/Shadowsocks/Litport e 22 nazioni arabe superati');
}

Future<void> main(List<String> args) async {
  if(args.contains('--self-test')) {await selfTest();return;}
  var perCountry=50;
  final ix=args.indexOf('--max-per-country');
  if(ix>=0 && ix+1<args.length) perCountry=int.tryParse(args[ix+1])??50;
  perCountry=perCountry.clamp(1,1000).toInt();
  final full=args.contains('--completa');
  final outputIndex=args.indexOf('--output');
  final outputDir=outputIndex>=0 && outputIndex+1<args.length ? args[outputIndex+1] : 'OUTPUT';
  await selfTest();
  final http=HttpClient()..connectionTimeout=const Duration(seconds:30);
  try {
    print('Fonte 1: Au1rxx Free VPN Subscriptions (sing-box)');
    final mainData=jsonDecode(await httpText(http,'$freeBase/singbox.json'));
    if(mainData is! Map || mainData['outbounds'] is! List) throw StateError('Formato Free VPN cambiato');
    final mainNodes=(mainData['outbounds'] as List).whereType<Map>().toList();
    final manifest=jsonDecode(await httpText(http,'$freeBase/manifest.json'));
    final collections=manifest is Map && manifest['collections'] is Map ? manifest['collections'] as Map : <dynamic,dynamic>{};
    final codes=collections.keys.map((e)=>value(e)).where((x)=>x.startsWith('country/'))
      .map((x)=>x.substring('country/'.length)).where((x)=>knownCountries.containsKey(x)).toSet().toList()..sort();
    print('  Catalogazione per Paese: ${codes.length} fonti geografiche');
    final byTag=<String,String>{};
    var geoOk=0;
    for(var k=0;k<codes.length;k+=8){
      final block=codes.skip(k).take(8).toList();
      final response=await Future.wait(block.map((code) async {
        try {
          final obj=jsonDecode(await httpText(http,'$freeBase/by-country/singbox-$code.json',timeout:const Duration(seconds:30)));
          if(obj is! Map || obj['outbounds'] is! List) return <String>[];
          return (obj['outbounds'] as List).whereType<Map>().map((x)=>value(x['tag']))
             .where((s)=>s.isNotEmpty).map((s)=>'$code|$s').toList();
        } catch (_) {return <String>[];}
      }));
      for(final entries in response) {
        for(final entry in entries){
          final sep=entry.indexOf('|');
          final code=entry.substring(0,sep), tag=entry.substring(sep+1);
          byTag[tag]=code;
          geoOk++;
        }
      }
    }
    print('  ${byTag.length} nodi con nazione ricavata dai file ufficiali per Paese');
    final collector=NodeCollector();
    final accepted={'vless','vmess','trojan','shadowsocks','hysteria2','tuic','http','socks'};
    for(final item in mainNodes){
      final type=value(item['type']);
      if(!accepted.contains(type)) continue;
      final node=Map<String,dynamic>.from(item);
      final tag=value(node['tag']);
      final code=parseTagCountry(node,byTag)??countryFromLabel(tag);
      collector.add(node,'FVS',code,tag);
    }
    print('  ${collector.nodes.length} nodi Free VPN aggiunti (wireguard endpoint esclusi)');
    print('Fonte 2: FastNodes (verified - verifica dichiarata dai gestori)');
    final verified=await httpText(http,'$fastBase/verified.txt');
    var rejected=0;
    for(final line in const LineSplitter().convert(verified)){
      final node=uriToOutbound(line);
      if(node==null){rejected++;continue;}
      final label=value(node['_label']);
      final code=countryFromLabel(label);
      collector.add(node,'FNV',code,label);
    }
    print('  Nodi iniziali Au1rxx + FastNodes Verified: ${collector.nodes.length}, URI non convertiti: $rejected');
    print('Fonte 3: FastNodes mondiale - Everything (fallback Top se vuoto)');
    var all='';
    var worldSource='everything.txt';
    try {
      all=await httpText(http,'$fastBase/everything.txt',timeout:const Duration(minutes:4));
    } catch (e) {
      print('  Everything non disponibile: $e');
    }
    if (all.trim().isEmpty) {
      worldSource='top.txt';
      print('  Everything e vuoto/non raggiungibile. Uso top.txt.');
      try {
        all=await httpText(http,'$fastBase/top.txt',timeout:const Duration(minutes:2));
      } catch (e) {
        print('  AVVISO: top.txt non disponibile: $e. Continuo con verified e fonti nazionali.');
      }
    }
    var parsed=0, skipped=0;
    final worldwideLimit=full?null:perCountry;
    for(final line in const LineSplitter().convert(all)){
      if(line.trim().isEmpty) continue;
      // In modalità normale si scartano presto i Paesi già al limite.
      String label='';
      final hash=line.indexOf('#');
      if(hash>=0) {
        try{label=Uri.decodeComponent(line.substring(hash+1));}
        catch(_){label=line.substring(hash+1);}
      }
      final cc=countryFromLabel(label);
      if(worldwideLimit!=null && (collector.origins['MONDO/$cc']??0)>=worldwideLimit){skipped++;continue;}
      final node=uriToOutbound(line);
      if(node==null){rejected++;continue;}
      final actualLabel=value(node['_label'],label);
      if(collector.add(node,'FNM',cc,actualLabel,countryLimit:worldwideLimit,limitOrigin:'MONDO')) parsed++;
    }
    print('  $worldSource aggiunti: $parsed; URI scartati/unsupported: $rejected');
    print('  Voci oltre limite per Paese: $skipped');
    // Recupera anche gli elenchi per nazione: possono contenere nodi assenti
    // da verified.txt ed everything.txt. Non assumere che i nodi siano funzionanti!
    print('Fonte 4: FastNodes - elenchi dedicati ai 22 Paesi arabi');
    final perCountryStatus=<String,String>{};
    for(final cc in arabCountries) {
      final url='$fastBase/countries/$cc.txt';
      String content;
      try {
        content=await httpText(http,url,timeout:const Duration(seconds:25));
      } catch (err) {
        perCountryStatus[cc]='Non disponibile nella fonte';
        print('  $cc: file non disponibile');
        continue;
      }
      var added=0;
      var total=0;
      for(final line in const LineSplitter().convert(content)) {
        if(line.trim().isEmpty || line.trim().startsWith('#')) continue;
        total++;
        if(!full && added>=perCountry) break;
        final node=uriToOutbound(line);
        if(node==null){rejected++;continue;}
        final label=value(node['_label']);
        final claimed=countryFromLabel(label);
        // Scarta etichette palesemente discordanti dalla nazione del file.
        if(claimed!='??' && claimed!=cc){skipped++;continue;}
        if(collector.add(node,'FNA',cc,label)) added++;
      }
      perCountryStatus[cc]='$total righe lette, $added nodi nuovi';
      print('  $cc ${knownCountries[cc]}: $added aggiunti ($total righe lette)');
    }
    // Fonte aggiuntiva mondiale Litport, con classificazione per IP di uscita
    // pubblicata dalla fonte. Esclude HTTP senza supporto HTTPS CONNECT.
    print('Fonte 5: Litport free proxy list (HTTP CONNECT, SOCKS4, SOCKS5)');
    final litportResult=await loadLitport(http,collector);
    print('Fonte 6: lista manuale Hiddify_IR.json (facoltativa)');
    final manualIran=await addManualIran(collector);
    print('  Proxy manuali nuovi: $manualIran (i duplicati sono eliminati)');
    // UN SOLO FILE JSON: contiene tutti i nodi senza distinguere
    // "qualita", "mondiale" o "solo arabi". Le fonti sono cumulative.
    await writeConfig('$outputDir${Platform.pathSeparator}Proxy_List.json',collector.nodes);
    final sorted=collector.countries.entries.toList()..sort((a,b)=>a.key.compareTo(b.key));
    final report=StringBuffer()
      ..writeln('HIDDIFY ITA MOD - PROXY LIST (UNICO JSON)')
      ..writeln('Generato: ${DateTime.now().toIso8601String()}')
      ..writeln('Au1rxx: $freeBase/singbox.json')
      ..writeln('FastNodes: $fastBase/verified.txt + $worldSource + countries/XX.txt per Paesi arabi')
      ..writeln('Litport: $litportAll')
      ..writeln('Litport nel nuovo JSON: ${litportResult.$1} nuovi/ripristinati; scartati ${litportResult.$2}; modalita ${litportResult.$3}')
      ..writeln('Proxy manuali in proxy/Hiddify_IR.json aggiunti: $manualIran')
      ..writeln('Nodi nel file Proxy_List.json: ${collector.nodes.length}')
      ..writeln('Nazioni etichettate: ${collector.countries.length}')
      ..writeln('Duplicati scartati: ${collector.duplicates}')
      ..writeln('URI non convertibili o protocollo non supportato: $rejected')
      ..writeln('ATTENZIONE: paese solo dedotto da feed/etichette, nessuna verifica IP reale.')
      ..writeln('ATTENZIONE: nessuna garanzia di funzionamento o affidabilita dei proxy.')
      ..writeln('Litport HTTP: importati solo quelli indicati HTTPS CONNECT; non prova la navigazione reale.')
      ..writeln('WireGuard endpoints del feed Au1rxx NON importati, per compatibilita MOD v0.1.')
      ..writeln('MODALITA: ${full?'COMPLETA/SPERIMENTALE':'CAMPIONATA'}')
      ..writeln('');
    for(final e in sorted){
      report.writeln('${e.key.padRight(3)} ${(knownCountries[e.key]??'Sconosciuti').padRight(26)} ${e.value}');
    }
    report.writeln('');
    report.writeln('=== TUTTI I 22 PAESI ARABI (numero nodi nel JSON finale) ===');
    for(final cc in arabCountries) {
      report.writeln('$cc ${(knownCountries[cc]??cc).padRight(25)} '
          '${(collector.countries[cc]??0).toString().padLeft(5)} nodi | '
          'FastNodes dedicato: ${perCountryStatus[cc]??'non esaminato'}');
    }
    report.writeln('');
    report.writeln('IL NUMERO DI NODI NON EQUIVALE A NODI FUNZIONANTI.');
    report.writeln('Bandiere/etichette non certificano IP di uscita o navigazione HTTPS.');
    final f=File('$outputDir${Platform.pathSeparator}RIEPILOGO_PAESI.txt');
    await f.writeAsString(report.toString());
    print('[OK] Riepilogo: ${f.path}');
    print('[OK] Profilo UNICO: $outputDir${Platform.pathSeparator}Proxy_List.json');
    print('IMPORTANTE: GitHub Actions aggiorna il file ogni 6 ore; Hiddify deve aggiornare il profilo remoto.');
  } finally {http.close(force:true);}
}
