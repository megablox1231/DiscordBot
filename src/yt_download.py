import yt_dlp
import asyncio

yt_dlp_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    #'logtostderr': False,
    #'quiet': True,
    #'no_warnings': True,
    #'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

async def dl(search):
    if not search.startswith(('http:', 'https:', "www.")):
        search = 'ytsearch1:' + search

    loop = asyncio.get_running_loop()
    with yt_dlp.YoutubeDL(yt_dlp_options) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(search, download=False))
        return info