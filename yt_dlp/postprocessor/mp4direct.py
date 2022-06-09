from .common import PostProcessor
from ..utils import prepend_extension

from ..ts_parser import (
    write_mp4_boxes,
    parse_mp4_boxes,
    pack_be32,
    pack_be64,
    unpack_ver_flags,
    unpack_be32,
    unpack_be64,
)


class MP4TimestampFixupPP(PostProcessor):
    def __init__(self, downloader=None):
        super().__init__(downloader)

    def analyze_mp4(filepath):
        """ returns (baseMediaDecodeTime offset, sample duration cutoff) """
        smallest_bmdt, known_sdur = float('inf'), set()
        with open(filepath, 'rb') as r:
            for btype, content in parse_mp4_boxes(r):
                if btype == 'tfdt':
                    version, _ = unpack_ver_flags(content[0:4])
                    # baseMediaDecodeTime always comes to the first
                    if version == 0:
                        bmdt = unpack_be32(content[4:8])
                    else:
                        bmdt = unpack_be64(content[4:12])
                    if bmdt == 0:
                        continue
                    smallest_bmdt = min(bmdt, smallest_bmdt)
                elif btype == 'tfhd':
                    version, flags = unpack_ver_flags(content[0:4])
                    if not flags & 0x08:
                        # this box does not contain "sample duration"
                        continue
                    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L203-L209
                    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/parsing/tfhd.js
                    sdur_start = 8  # header + track id
                    if flags & 0x01:
                        sdur_start += 8
                    if flags & 0x02:
                        sdur_start += 4
                    # the next 4 bytes are "sample duration"
                    sample_dur = unpack_be32(content[sdur_start:sdur_start + 4])
                    known_sdur.add(sample_dur)

        maximum_sdur = max(known_sdur)
        for multiplier in (0.7, 0.8, 0.9, 0.95):
            sdur_cutoff = maximum_sdur * multiplier
            test_set = set(x for x in known_sdur if x > sdur_cutoff)
            if len(test_set) < 4:
                break
        else:
            sdur_cutoff = float('inf')

        return smallest_bmdt, sdur_cutoff

    def modify_mp4(self, src, dst, bmdt_offset, sdur_cutoff):
        with open(src, 'rb') as r, open(dst, 'wb') as w:
            def converter():
                for box in parse_mp4_boxes(r):
                    content = box[1]
                    if box[0] == 'tfdt':
                        version, _ = unpack_ver_flags(content[0:4])
                        # baseMediaDecodeTime always comes to the first
                        if version == 0:
                            bmdt = unpack_be32(content[4:8])
                        else:
                            bmdt = unpack_be64(content[4:12])
                        if bmdt == 0:
                            yield box
                            continue
                        # calculate new baseMediaDecodeTime
                        bmdt = max(0, bmdt - bmdt_offset)
                        # pack everything again and insert as a new box
                        if version == 0:
                            bmdt_b = pack_be32(bmdt)
                        else:
                            bmdt_b = pack_be64(bmdt)
                        yield ('tfdt', content[0:4] + bmdt_b + content[8 + version * 4:])
                        continue
                    elif box[0] == 'tfhd':
                        version, flags = unpack_ver_flags(content[0:4])
                        if not flags & 0x08:
                            yield box
                            continue
                        # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L203-L209
                        # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/parsing/tfhd.js
                        sdur_start = 8  # header + track id
                        if flags & 0x01:
                            sdur_start += 8
                        if flags & 0x02:
                            sdur_start += 4
                        # the next 4 bytes are "sample duration"
                        sample_dur = unpack_be32(content[sdur_start:sdur_start + 4])
                        if sample_dur > sdur_cutoff:
                            sample_dur = 0
                        sd_b = pack_be32(sample_dur)
                        yield ('tfhd', content[:sdur_start] + sd_b + content[sdur_start + 4:])
                        continue
                    yield box

            write_mp4_boxes(w, converter())

    def run(self, information):
        filename = information['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        self.write_debug('Analyzing MP4')
        bmdt_offset, sdur_cutoff = self.analyze_mp4(filename)
        # if any of them are Infinity, there's something wrong
        self.write_debug(f'baseMediaDecodeTime offset = {bmdt_offset}, sample duration cutoff = {sdur_cutoff}')
        self.modify_mp4(filename, temp_filename, bmdt_offset, sdur_cutoff)

        self._downloader.replace(temp_filename, filename)

        return [], information
