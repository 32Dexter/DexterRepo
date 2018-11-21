# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# streamondemand.- XBMC Plugin
# Canale  per http://animeinstreaming.net/
# http://www.mimediacenter.info/foro/viewforum.php?f=36
# ------------------------------------------------------------
import re
import urlparse

import xbmc
from core import config, httptools, scrapertools
from core.item import Item
from core.tmdb import infoSod
from platformcode import logger

__channel__ = "animeworld"

host = "https://www.animeworld.it"

PERPAGE = 100


# -----------------------------------------------------------------
def mainlist(item):
    log("mainlist", "mainlist")
    itemlist = [
        Item(
            channel=__channel__,
            action="lista_anime",
            title=
            "[COLOR azure]Anime [/COLOR]- [COLOR orange]Lista Completa[/COLOR]",
            url=host + "/az-list",
            thumbnail=CategoriaThumbnail,
            fanart=CategoriaFanart),
        Item(
            channel=__channel__,
            action="ultimiep",
            title="[COLOR azure]Ultimi Episodi[/COLOR]",
            url=host + "/fetch_pages?request=episodes",
            thumbnail=CategoriaThumbnail,
            fanart=CategoriaFanart),
        Item(
            channel=__channel__,
            action="search",
            title="[COLOR yellow]Cerca ...[/COLOR]",
            thumbnail=
            "http://dc467.4shared.com/img/fEbJqOum/s7/13feaf0c8c0/Search")
    ]

    return itemlist


# =================================================================

# -----------------------------------------------------------------
def newest(categoria):
    log("newest", "newest" + categoria)
    itemlist = []
    item = Item()
    try:
        if categoria == "anime":
            item.url = "%s/fetch_pages?request=episodes" % host
            item.action = "ultimiep"
            itemlist = ultimiep(item)

            if itemlist[-1].action == "ultimiep":
                itemlist.pop()
    # Continua la ricerca in caso di errore 
    except:
        import sys
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        return []

    return itemlist


# =================================================================

# -----------------------------------------------------------------
def search(item, texto):
    log("search", "search")
    item.url = texto
    try:
        return search_anime(item)
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


# =================================================================


# -----------------------------------------------------------------
def search_anime(item):
    log("search_anime", "search_anime")
    itemlist = []

    data = httptools.downloadpage(host + "/animelist?load_all=1").data
    data = scrapertools.decodeHtmlentities(data)

    texto = item.url.lower().split('+')

    patron = r'<a href="([^"]+)"[^>]*?>[^>]*?>(.+?)<'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle in [(scrapedurl, scrapedtitle)
                                     for scrapedurl, scrapedtitle in matches
                                     if all(t in scrapedtitle.lower()
                                            for t in texto)]:
        itemlist.append(
            Item(
                channel=__channel__,
                action="episodios",
                title=scrapedtitle,
                url=scrapedurl,
                fulltitle=scrapedtitle,
                show=scrapedtitle,
                thumbnail=""))

    return itemlist


# =================================================================


# -----------------------------------------------------------------
def lista_anime(item):
    log("lista_anime", "lista_anime")

    itemlist = []

    p = 1
    if '{}' in item.url:
        item.url, p = item.url.split('{}')
        p = int(p)

    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAaa")
    print item.url

    # Carica la pagina
    data = httptools.downloadpage(item.url).data


    # print data

    # Estrae i contenuti
    patron = r"<a\sclass=\"name\" .* href=\"([^\"]+)\">(.+?)<"
    matches = re.finditer(patron, data)

    scrapedplot = ""
    scrapedthumbnail = ""
    for i, match in enumerate(matches):
        if (p - 1) * PERPAGE > i: continue
        if i >= p * PERPAGE: break

        scrapedtitle = match.group(2)
        scrapedurl = match.group(1)

        title = scrapertools.decodeHtmlentities(scrapedtitle).strip()
        itemlist.append(
            infoSod(
                Item(
                    channel=__channel__,
                    extra=item.extra,
                    action="episodios",
                    title=title,
                    url=scrapedurl,
                    thumbnail=scrapedthumbnail,
                    fulltitle=title,
                    show=title,
                    plot=scrapedplot,
                    folder=True),
                tipo='movie'))

    if len(itemlist) > 0:
        itemlist.append(
            Item(
                channel=__channel__,
                action="HomePage",
                title="[COLOR yellow]Torna Home[/COLOR]",
                folder=True)),

    if len(list(matches)) >= p * PERPAGE:
        scrapedurl = item.url + '{}' + str(p + 1)
        itemlist.append(
            Item(
                channel=__channel__,
                extra=item.extra,
                action="lista_anime",
                title="[COLOR orange]Successivo >>[/COLOR]",
                url=scrapedurl,
                thumbnail=
                "http://2.bp.blogspot.com/-fE9tzwmjaeQ/UcM2apxDtjI/AAAAAAAAeeg/WKSGM2TADLM/s1600/pager+old.png",
                folder=True))

    return itemlist


# =================================================================


# -----------------------------------------------------------------
def ultimiep(item):
    log("ultimiep", "ultimiep")
    itemlist = []

    post = "page=%s" % item.extra if item.extra else None

    data = httptools.downloadpage(
        item.url, post=post, headers={
            'X-Requested-With': 'XMLHttpRequest'
        }).data

    patron = r"""<a href='[^']+'><div class="locandina"><img alt="[^"]+" src="([^"]+)" title="[^"]+" class="grandezza"></div></a>\s*"""
    patron += r"""<a href='([^']+)'><div class="testo">(.+?)</div></a>\s*"""
    patron += r"""<a href='[^']+'><div class="testo2">(.+?)</div></a>"""
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedthumbnail, scrapedurl, scrapedtitle1, scrapedtitle2 in matches:
        scrapedtitle1 = scrapertools.decodeHtmlentities(scrapedtitle1)
        scrapedtitle2 = scrapertools.decodeHtmlentities(scrapedtitle2)
        scrapedtitle = scrapedtitle1 + ' - [COLOR azure]' + scrapedtitle2 + '[/COLOR]'
        itemlist.append(
            infoSod(
                Item(
                    channel=__channel__,
                    action="findvideos",
                    title=scrapedtitle,
                    url=scrapedurl,
                    fulltitle=scrapedtitle1,
                    show=re.sub(r'[Ee]pisodio\s*', '', scrapedtitle).strip(),
                    thumbnail=scrapedthumbnail),
                tipo="tv"))

    # Pagine
    patronvideos = r'data-page="(\d+)" title="Next">Pagina Successiva'
    next_page = scrapertools.find_single_match(data, patronvideos)

    if next_page:
        itemlist.append(
            Item(
                channel=__channel__,
                action="HomePage",
                title="[COLOR yellow]Torna Home[/COLOR]",
                folder=True)),
        itemlist.append(
            Item(
                channel=__channel__,
                action="ultimiep",
                title="[COLOR orange]Successivo >>[/COLOR]",
                url=host + "/fetch_pages?request=episodes",
                thumbnail=
                "http://2.bp.blogspot.com/-fE9tzwmjaeQ/UcM2apxDtjI/AAAAAAAAeeg/WKSGM2TADLM/s1600/pager+old.png",
                extra=next_page,
                folder=True))

    return itemlist


# =================================================================


# -----------------------------------------------------------------
def episodios(item):
    itemlist = []

    data = httptools.downloadpage(item.url).data

    anime_id = scrapertools.find_single_match(data, r'\?anime_id=(\d+)')

    data = httptools.downloadpage(
        host + "/loading_anime?anime_id=" + anime_id,
        headers={
            'X-Requested-With': 'XMLHttpRequest'
        }).data

    patron = r'<td style="[^"]+"><b><strong" style="[^"]+">(.+?)</b></strong></td>\s*'
    patron += r'<td style="[^"]+"><a href="([^"]+)"'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedtitle, scrapedurl in matches:

        scrapedtitle = scrapertools.decodeHtmlentities(scrapedtitle)
        scrapedtitle = re.sub(r'<[^>]*?>', '', scrapedtitle)
        scrapedtitle = '[COLOR azure][B]' + scrapedtitle + '[/B][/COLOR]'
        itemlist.append(
            Item(
                channel=__channel__,
                action="findvideos",
                contentType="episode",
                title=scrapedtitle,
                url=urlparse.urljoin(host, scrapedurl),
                fulltitle=scrapedtitle,
                show=scrapedtitle,
                plot=item.plot,
                fanart=item.thumbnail,
                thumbnail=item.thumbnail))

    # Comandi di servizio
    if config.get_library_support() and len(itemlist) != 0:
        itemlist.append(
            Item(
                channel=__channel__,
                title="Aggiungi alla libreria",
                url=item.url,
                action="add_serie_to_library",
                extra="episodios",
                show=item.show))

    return itemlist


# ==================================================================


# -----------------------------------------------------------------
def findvideos(item):
    logger.info("streamondemand.animeforce findvideos")

    itemlist = []

    data = httptools.downloadpage(item.url).data
    patron = r'<a href="([^"]+)"><div class="downloadestreaming">'
    url = scrapertools.find_single_match(data, patron)

    data = httptools.downloadpage(url).data
    patron = r"""<source\s*src=(?:"|')([^"']+?)(?:"|')\s*type=(?:"|')video/mp4(?:"|')>"""
    matches = re.compile(patron, re.DOTALL).findall(data)
    for video in matches:
        itemlist.append(
            Item(
                channel=__channel__,
                action="play",
                title=item.title + " [[COLOR orange]Diretto[/COLOR]]",
                url=video,
                folder=False))

    return itemlist


# ==================================================================


# =================================================================
# Funzioni di servizio
# -----------------------------------------------------------------
def scrapedAll(url="", patron=""):
    data = httptools.downloadpage(url).data
    MyPatron = patron
    matches = re.compile(MyPatron, re.DOTALL).findall(data)
    scrapertools.printMatches(matches)

    return matches


# =================================================================


# -----------------------------------------------------------------
def scrapedSingle(url="", single="", patron=""):
    data = httptools.downloadpage(url).data
    paginazione = scrapertools.find_single_match(data, single)
    matches = re.compile(patron, re.DOTALL).findall(paginazione)
    scrapertools.printMatches(matches)

    return matches


# =================================================================


# -----------------------------------------------------------------
def Crea_Url(pagina="1", azione="ricerca", categoria="", nome=""):
    # esempio
    # chiamate.php?azione=ricerca&cat=&nome=&pag=
    Stringa = host + "chiamate.php?azione=" + azione + "&cat=" + categoria + "&nome=" + nome + "&pag=" + pagina
    log("crea_Url", Stringa)
    return Stringa


# =================================================================


# -----------------------------------------------------------------
def log(funzione="", stringa="", canale=__channel__):
    logger.debug("[" + canale + "].[" + funzione + "] " + stringa)


# =================================================================


# -----------------------------------------------------------------
def HomePage(item):
    xbmc.executebuiltin(
        "ReplaceWindow(10024,plugin://plugin.video.streamondemand)")


# =================================================================

# =================================================================
# riferimenti di servizio
# -----------------------------------------------------------------
AnimeThumbnail = "http://img15.deviantart.net/f81c/i/2011/173/7/6/cursed_candies_anime_poster_by_careko-d3jnzg9.jpg"
AnimeFanart = "https://i.ytimg.com/vi/IAlbvyBdYdY/maxresdefault.jpg"
CategoriaThumbnail = "http://static.europosters.cz/image/750/poster/street-fighter-anime-i4817.jpg"
CategoriaFanart = "https://i.ytimg.com/vi/IAlbvyBdYdY/maxresdefault.jpg"
CercaThumbnail = "http://dc467.4shared.com/img/fEbJqOum/s7/13feaf0c8c0/Search"
CercaFanart = "https://i.ytimg.com/vi/IAlbvyBdYdY/maxresdefault.jpg"
HomeTxt = "[COLOR yellow]Torna Home[/COLOR]"
AvantiTxt = "[COLOR orange]Successivo>>[/COLOR]"
AvantiImg = "http://2.bp.blogspot.com/-fE9tzwmjaeQ/UcM2apxDtjI/AAAAAAAAeeg/WKSGM2TADLM/s1600/pager+old.png"
