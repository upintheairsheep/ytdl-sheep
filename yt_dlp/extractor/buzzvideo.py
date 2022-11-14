# coding: utf-8
from __future__ import unicode_literals

import hashlib
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    merge_dicts,
    mimetype2ext,
    strip_or_none,
    unescapeHTML,
    url_or_none,
)

# yt-dlp shim
if not hasattr(InfoExtractor, '_match_valid_url'):

    BaseIE = InfoExtractor

    class InfoExtractor(BaseIE):
        def _match_valid_url(self, url):
            return re.match(self._VALID_URL, url)


class BuzzVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?buzzvideo\.com/(?:article/(?P<id>\w\d+)|@(?P<user>[\w-]+)/(?P<display_id>[^/?#]+))'
    _TESTS = [{
        'url': 'https://www.buzzvideo.com/article/i7157121376749797894?referer=foryou&pid=website_feed',
        'md5': 'f312a656752c3a0cd8ae539899d31542',
        'info_dict': {
            'id': 'i7157121376749797894',
            'ext': 'mp4',
            'title': 'i7157121376749797894',
            'timestamp': 1666397402,
            'upload_date': '20221022',
            'description': 'md5:b254d2ab0822e886d5591946ec22828b',
            'uploader': 'Toshi',
        },
    }, {
        'url': 'https://www.buzzvideo.com/@toshi/%E3%80%90%E7%99%92%E3%81%97%E3%80%91%E3%81%B2%E3%82%87%E3%81%A3%E3%81%93%E3%82%8A%E3%81%AB%E3%82%83%E3%82%93%E3%81%93%E3%80%82%E3%81%8B%E3%82%8F%E3%81%84%E3%81%84%E3%83%8B%E3%83%A3%E3%83%BC-BsKG2_gzU2M?referer=foryou&pid=website_feed',
        'only_matching': True,
    }]

    def _parse_json(self, json_string, video_id, transform_source=unescapeHTML, fatal=True):
        return super(BuzzVideoIE, self)._parse_json(json_string, video_id, transform_source=transform_source, fatal=fatal)

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, video_id)

        if not video_id:
            alternate = self._search_regex(
                r'''(<link\b[^>]+\brel\s*=\s*["']alternate\b[^>]+>)''',
                webpage, 'article URL', default='')
            alternate = extract_attributes(alternate)
            video_id = self._match_valid_url(alternate.get('href') or url).group('id')
        if not video_id:
            video_id = hashlib.md5(display_id).hexdigest()

        info = self._search_json_ld(webpage, video_id,)

        result = merge_dicts({
            'id': video_id,
            }, info, {
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'height': int_or_none(self._og_search_property('video:height', webpage)),
        })
        if not url_or_none(result.get('url')):
            result['url'] = self._og_search_video_url(webpage)
        result['ext'] = mimetype2ext(
            self._search_regex(r'mime_type=(\w+)', result['url'], 'video type', default=None).replace('_', '/'))
        title = strip_or_none(result.get('title'))
        title = title or re.split(r'|\s*BuzzVideo', 1)[0], self._og_search_title(webpage)
        result['title'] = strip_or_none(title) or display_id or self._generic_title(url)

        return result
