# Global URLs
KS_RETRIEVAL_URL = "http://open.http.mmp.streamuk.com/html5/html5lib/v2.0.RC3/mwEmbedFrame.php?&uiconf_id=11170445&wid=_2000012&p=2000012"
SPURSTV_ROOT = "http://www.tottenhamhotspur.com/spurs-tv/"
#STREAMUK_API = "http://mmp.streamuk.com/api_v3/index.php?service=baseEntry&action=getbyids"
API_URL = "http://mmp.streamuk.com/api_v3/index.php?service=%s&action=%s"

# Need the session key everywhere
ks = ""

# Plex Variables
PREFIX = "/video/spurstv"
NAME = 'Spurs TV'
ICON = 'icon-default.png'
ART  = 'art-default.jpg'

####################################################################################################
def Start():
    import re

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
        Log.Info("Session Key(ks) = '" + ks + "'")
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

    Log.Info('video_ids({0})'.format(video_ids))
    Log.Info('video_ids: ' + ','.join(video_ids))
    #filter:entryIdIn=0_wpszy3ew,0_e66uu2ht&filter:objectType=KalturaAssetFilter

    # Retrieve the session key
    if('spursTvKs' in Dict):
        ks = Dict['spursTvKs']
        Log.Info('KS: ' + ks)
    else:
        Log.Error('Cannot ListVideos without a session key')
        return(oc)

    # Batch request info on videos
    infoXml = XML.ObjectFromURL(url="http://mmp.streamuk.com/api_v3/index.php?service=baseEntry&action=getbyids",
                                values={'ks' : ks, 'entryIds' : ",".join(video_ids)})
    items = infoXml.xpath('//item')
    Log.Info('Items: ' + str(len(items)))

    ## Get the flavor id for all videos
    #flavorsXml = XML.ObjectFromURL(url="http://mmp.streamuk.com/api_v3/index.php?service=flavorAsset&action=list",
    #                            values={'ks' : ks, 'filter:entryIdIn' : ",".join(video_ids)})
    #flavorIds = flavorsXml.xpath('//item[width=1280]/id/text()')
    #Log.Info('Flavors: ' + str(len(flavorIds)))
    #if(flavorIds > 0):
    #    Log.Info('FlavorList: ' + ','.join(flavorIds))
    #    flavorId = flavorIdRaw[0]
    #    Log.Info("GoodFlavor: " + str(flavorId))
    #else:
    #    Log.Error('No video flavor found')
    #    return(None)
    #Log.Info('Flavors: ' + str(len(items)))
    # TODO Fix this section to avoid one of the API calls in the MakeVideoClipObject section

    # Loop through XML and create objects
    for item in infoXml.xpath('//item'):
        #Log.Info('ID: {0}, URL: {1}'.format(item.id.text, item.downloadUrl.text))

        ## Create video object
        #vco = VideoClipObject(
        #    url = item.downloadUrl.text,
        #    title = item.name.text,
        #    thumb = GetThumb(item.thumbnailUrl.text),
        #    summary = item.description.text
        #)
        #oc.add(vco)

        # Create the video object and add it to the list
        vco = MakeVideoClipObject(item, ks)
        if(vco):
            oc.add(vco)

    return(oc)


####################################################################################################
@route(PREFIX + '/makevideoclipobject')
def MakeVideoClipObject(item, ks):
    # Get flavor list (video types/containers)
    flavorXml = XML.ObjectFromURL(url="http://mmp.streamuk.com/api_v3/index.php?service=flavorAsset&action=getByEntryId",
                                values={'ks' : ks, 'entryId' : item.id})

    # Get flavor we want (MP4, max resolution) - Determine resolution based on end device?
    flavorIdRaw = flavorXml.xpath('//item[width=1280]/id/text()')
    if(flavorIdRaw > 0):
        flavorId = flavorIdRaw[0]
        Log.Info("GoodFlavor: " + str(flavorId))
    else:
        Log.Error('No video flavor found')
        return(None)

    # Get actual video URL
    videoUrlXml = XML.ObjectFromURL(url="http://mmp.streamuk.com/api_v3/index.php?service=flavorAsset&action=getUrl",
                               values={'ks' : ks, 'id' : flavorId, 'storageId' : 0})
    urls = videoUrlXml.xpath('/xml/result//text()')

    # Quit if we didn't get a video url
    if(len(urls) < 1):
        Log.Error('No video URL found')
        return(None)

    # Create video object
    vco = VideoClipObject(
        url = urls[0],
        title = item.name.text,
        thumb = GetThumb(item.thumbnailUrl.text),
        summary = item.description.text
    )
    #vco = VideoClipObject()
    return(vco)


####################################################################################################
# Ripped this code out of the IPTV plugin
def GetThumb(thumb):
    if thumb and thumb.startswith('http'):
        return thumb
    else:
        return R('icon-default.png')

