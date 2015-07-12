# Global URLs
KS_RETRIEVAL_URL = "http://open.http.mmp.streamuk.com/html5/html5lib/v2.0.RC3/mwEmbedFrame.php?&uiconf_id=11170445&wid=_2000012&p=2000012"
SPURSTV_ROOT = "http://www.tottenhamhotspur.com/spurs-tv/"
API_URL = "http://mmp.streamuk.com/api_v3/index.php?service=%s&action=%s"

# Plex Variables
PREFIX = "/video/spurstv"
NAME = 'Spurs TV'
ICON = 'icon-default.png'
ART  = 'art-default.jpg'

####################################################################################################
def Start():
    import re
    ObjectContainer.title1 = NAME
    ObjectContainer.art = R(ART)
    DirectoryObject.thumb = R(ICON)
    # TODO Fanart and icon

    # Make this plugin show up in the 'Video' section in Plex.
    Plugin.AddPrefixHandler(PREFIX, MainMenu, NAME, ICON, ART)
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux i686; rv:32.0) Gecko/20100101 Firefox/32.0'

    # Retrieve session key once now (8 hours max for cached values)
    ksfind = re.compile(r'.*"ks"\s*:\s*"([^"]*)".*', re.DOTALL)
    ks_scripts = HTML.ElementFromURL(KS_RETRIEVAL_URL, cacheTime=86400).xpath('//script[@type="text/javascript"]//text()')
    ks_list = [ ksfind.sub(r'\1', s) for s in ks_scripts if 'kalturaIframePackageData = ' in s ]
    if(ks_list):
        ks = ks_list[0]
        Dict["spursTvKs"] = ks
        Log.Info('KS: ' + ks)
    else:
        Log.Critical('Cannot continue without a session key.')

####################################################################################################
def MainMenu():
    # Hard coded sections from Spurs TV page
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(ListVideos, tag='highlights'), title="Highlights", thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(ListVideos, tag='interviews'), title="Interviews", thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(ListVideos, tag='extra-time'), title="Extra Time", thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(ListVideos, tag='features'), title="Features", thumb=R(ICON)))
    return(oc)
# TODO Generate this from the categories endpoint on the API
# TODO Subsections for each of these?

####################################################################################################
@route(PREFIX + '/listvideos')
def ListVideos(tag):
    oc = ObjectContainer()

    # Nothing to do without a tag
    if(not tag):
        return(oc)

    # Parse out the video IDs for videos on the page doing so separately for the main video an the rest
    raw = HTML.ElementFromURL(SPURSTV_ROOT + tag)
    video_ids = raw.xpath('//div[@class="video"]/@data-videoid')
    video_ids.extend([ x.split('/')[7] for x in raw.xpath('//div[@class="card"]/a/@style') ])

    # Retrieve the session key
    if('spursTvKs' in Dict):
        ks = Dict['spursTvKs']
    else:
        Log.Error('Cannot ListVideos without a session key')
        return(oc)

    # Batch request info on videos
    infoXml = XML.ObjectFromURL(url=API_URL % ('baseEntry', 'getbyids'),
                                values={'ks' : ks, 'entryIds' : ",".join(video_ids)})
    items = infoXml.xpath('//item')
    ordered_items = sorted(items, key=lambda x: int(x.createdAt.text), reverse=True)

    # Loop through XML and create objects
    for item in ordered_items:
        # Create video object
        vco = VideoClipObject(
            url = item.downloadUrl.text,
            title = item.name.text,
            thumb = Resource.ContentsOfURLWithFallback(item.thumbnailUrl.text),
            duration = int(item.msDuration.text),
            summary = item.description.text
        )
        oc.add(vco)

    return(oc)

