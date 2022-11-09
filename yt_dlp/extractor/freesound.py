import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    unified_strdate,
)
from .playlistbase import PlaylistBaseIE

class FreesoundIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?freesound\.org/people/[^/]+/sounds/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://www.freesound.org/people/miklovan/sounds/194503/',
        'md5': '12280ceb42c81f19a515c745eae07650',
        'info_dict': {
            'id': '194503',
            'ext': 'mp3',
            'title': 'gulls in the city.wav',
            'description': 'the sounds of seagulls in the city',
            'duration': 130.233,
            'uploader': 'miklovan',
            'upload_date': '20130715',
            'tags': list,
        }
    }

    def _real_extract(self, url):
    # Todo: extract copyright info, geotags, and possibly comments
        audio_id = self._match_id(url)

        webpage = self._download_webpage(url, audio_id)

        audio_url = self._og_search_property('audio', webpage, 'song url')
        title = self._og_search_property('audio:title', webpage, 'song title')

        description = self._html_search_regex(
            r'(?s)id=["\']sound_description["\'][^>]*>(.+?)</div>',
            webpage, 'description', fatal=False)

        duration = float_or_none(
            get_element_by_class('duration', webpage), scale=1000)

        upload_date = unified_strdate(get_element_by_id('sound_date', webpage))
        uploader = self._og_search_property(
            'audio:artist', webpage, 'uploader', fatal=False)
        download_count = self._og_search_property(
            'download_text', '.b' webpage, 'download_count', fatal=False)
        average_rating = self._og_search_property(
            'span.numratings', webpage, 'average_rating', fatal=False)
        channels = self._html_search_regex(
            r'Channels</dt><dd>(.+?)</dd>', webpage,
            'channels info', fatal=False)

        tags_str = get_element_by_class('tags', webpage)
        tags = re.findall(r'<a[^>]+>([^<]+)', tags_str) if tags_str else None

        audio_urls = [audio_url]

        LQ_FORMAT = '-lq.mp3'
        if LQ_FORMAT in audio_url:
            audio_urls.append(audio_url.replace(LQ_FORMAT, '-hq.mp3'))

        formats = [{
            'url': format_url,
            'format_note': channels,
            'quality': quality,
        } for quality, format_url in enumerate(audio_urls)]
        self._sort_formats(formats)

        return {
            'id': audio_id,
            'title': title,
            'description': description,
            'duration': duration,
            'uploader': uploader,
            'upload_date': upload_date,
            'download_count': download_count,
            'tags': tags,
            'formats': formats,
        }


class FreesoundPlaylistIE(PlaylistBaseIE):
    # Source: https://github.com/yt-dlp/yt-dlp/issues/4161#issuecomment-1166157842
    # Todo: Add metadata: profile pic, info
    _VALID_URL = r'https?://(?:www\.)?freesound\.org/people/(?P<person>[^/]+)/(?P<type>downloaded_sounds|packs)/(?P<id>[^/]*)'

    _ITEM_RE = r'''(?s)<div\b[^>]+\bclass\s*=\s*("|')sound_filename\1[^>]*>\s*<a\b[^>]+\bclass\s*=\s*("|')title\2[^>]+\bhref\s*=\s*("|')(?P<url>(?:(?!\3).)+)'''
    _NEXT_RE = r'''<a\b[^>]+\bhref\s*=\s*("|')(?P<url>(?:(?!\1).)+)[^>]+\btitle\s*=\s*["']Next\s+Page'''
    _ITEM_IE = 'Freesound'
