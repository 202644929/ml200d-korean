#!/usr/bin/env python3
"""
Generate .KOX extension glyph files for Magic Lantern's RBF fonts.

RBF fonts only hold codepoints 0-255, so Hangul (and symbols such as U+2192)
used in strings_ko.csv have no glyphs. For each RBF font this renders every
such character from a TrueType/OpenType font at the RBF's cell height and
baseline as 1-bit bitmaps, and writes <name>.kox next to the .rbf.

The camera loads ML/FONTS/<name>.KOX at startup (file layout: see struct
rbf_ext in src/rbf_font.c), so fonts can be swapped on the card without
rebuilding the firmware.

Noto Sans CJK, Nanum and Galmuri are SIL OFL fonts; bitmaps rendered from them
may be redistributed.
"""
import argparse, csv, os, struct
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_TTF = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
NAMES = ['argnor23', 'argnor28', 'argnor32', 'arghlf22', 'term12', 'term20']
SIZE_PROBE = '한글값'   # typical syllables, matched against Latin cap height


class RBF:
    def __init__(self, path):
        d = open(path, 'rb').read()
        (self.char_size, _points, self.h, _max_w, self.first, self.last,
         _u, wmap, cmap, _desc, _il) = struct.unpack_from('<11i', d, 72)
        self.cell_w = 8 * self.char_size // self.h
        n = self.last - self.first + 1
        self.widths = d[wmap:wmap + n]
        self.data = d[cmap:cmap + n * self.char_size]
        H = ord('H')
        rows = [yy for yy in range(self.h) if any(self.px(H, xx, yy) for xx in range(self.width(H)))]
        self.cap_top, self.base = rows[0], rows[-1] + 1

    def has(self, cp):
        return self.first <= cp <= self.last

    def width(self, cp):
        return self.widths[cp - self.first] if self.has(cp) else 0

    def px(self, cp, xx, yy):
        off = (cp - self.first) * self.char_size
        return (self.data[off + yy * self.cell_w // 8 + xx // 8] >> (xx % 8)) & 1


def parse_ttf(spec):
    path, idx = spec, None
    head, _, tail = spec.rpartition(':')
    if head and tail.isdigit():
        path, idx = head, int(tail)
    if idx is None:
        idx = 0
        if path.lower().endswith('.ttc'):
            for i in range(32):
                try:
                    fam = ImageFont.truetype(path, 12, index=i).getname()[0]
                except OSError:
                    break
                if 'KR' in fam and 'Mono' not in fam:
                    idx = i
                    break
    return path, idx


def load_ttf(spec, size):
    return ImageFont.truetype(spec[0], size, index=spec[1])


def needed_chars(csv_path, rbf):
    cps = set()
    with open(csv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            for ch in row['korean']:
                cp = ord(ch)
                if 32 <= cp <= 0xFFFF and not (cp < 256 and rbf.width(cp)):
                    cps.add(cp)
    return sorted(cps)


def ink_rows(font, text, rbf):
    """Top/bottom ink rows of 'text' drawn on the RBF baseline, in cell coordinates."""
    im = Image.new('L', (int(font.getlength(text)) + 16, rbf.h * 3), 0)
    ImageDraw.Draw(im).text((0, rbf.h), text, font=font, fill=255, anchor='ls')
    bb = im.getbbox()
    if not bb:
        return None
    return bb[1] - rbf.h + rbf.base, bb[3] - rbf.h + rbf.base


def fit(spec, rbf, chars, mode, size=None):
    """Pick (size, baseline).
    'cap':  match Hangul to the Latin cap height, on the RBF baseline.
    'cell': largest size whose glyphs fit the cell, moving the baseline if
            needed (Hangul has no descenders, so it still lines up)."""
    cap_h = rbf.base - rbf.cap_top
    all_text = ''.join(map(chr, chars))
    best = None
    for s in ([size] if size else range(6, 64)):
        font = load_ttf(spec, s)
        span = ink_rows(font, all_text, rbf)
        if span is None:
            continue
        top, bottom = span
        if mode == 'cell':
            fits = bottom - top <= rbf.h
            baseline = rbf.base + max(-top, 0) - max(bottom - rbf.h, 0)
        else:
            fits = top >= 0 and bottom <= rbf.h
            baseline = rbf.base
        if not fits:
            if size:
                raise SystemExit('%s at %dpx does not fit a %dpx cell' % (spec[0], size, rbf.h))
            break
        if mode == 'cell' or size:
            best = (s, baseline)
        else:
            probe = ink_rows(font, SIZE_PROBE, rbf)
            if probe and probe[1] - probe[0] <= cap_h * 1.35:
                best = (s, baseline)
    if best is None:
        raise SystemExit('no size of %s fits a %dpx cell' % (spec[0], rbf.h))
    return best

def render(font, cp, rbf, baseline, threshold, spacing):
    ch = chr(cp)
    adv = int(round(font.getlength(ch)))
    im = Image.new('L', (adv + 16, rbf.h), 0)
    ImageDraw.Draw(im).text((0, baseline), ch, font=font, fill=255, anchor='ls')
    bits = im.point(lambda v: 255 if v >= threshold else 0)
    bb = bits.getbbox()
    return bits, min(max(adv + spacing, bb[2] if bb else 0), 255)

def pack(bits, width, cell_bits, height):
    stride = cell_bits // 8
    out = bytearray(height * stride)
    px = bits.load()
    for yy in range(height):
        for xx in range(min(width, bits.width)):
            if px[xx, yy]:
                out[yy * stride + xx // 8] |= 1 << (xx % 8)
    return bytes(out)


def build(rbf, spec, chars, mode, threshold, spacing, size=None):
    size, baseline = fit(spec, rbf, chars, mode, size)
    font = load_ttf(spec, size)
    glyphs = [render(font, cp, rbf, baseline, threshold, spacing) for cp in chars]
    cell_bits = (max(w for _, w in glyphs) + 7) // 8 * 8
    assert cell_bits <= 248
    data = bytearray(b'KOX1' + struct.pack('<HBB', len(chars), rbf.h, cell_bits))
    data += struct.pack('<%dH' % len(chars), *chars)
    data += bytes(w for _, w in glyphs)
    for bits, w in glyphs:
        data += pack(bits, w, cell_bits, rbf.h)
    return bytes(data), size, baseline, cell_bits


class KOX:
    def __init__(self, data, rbf):
        assert data[:4] == b'KOX1'
        n, self.h, self.cell_bits = struct.unpack_from('<HBB', data, 4)
        assert self.h == rbf.h and self.cell_bits % 8 == 0
        self.glyph_size = self.h * self.cell_bits // 8
        assert len(data) >= 8 + 3 * n + n * self.glyph_size
        self.index = {c: i for i, c in enumerate(struct.unpack_from('<%dH' % n, data, 8))}
        self.widths = data[8 + 2 * n:8 + 3 * n]
        self.bitmaps = data[8 + 3 * n:]


def draw_like_camera(rbf, kox, text):
    """Python mirror of rbf_char_width() + rbf_draw_char() + font_draw_char()."""
    def char_width(cp):
        if 0 <= cp < 256 and rbf.width(cp):
            return rbf.width(cp)
        i = kox.index.get(cp, -1)
        return kox.widths[i] if i >= 0 else 0
    cps = [ord(c) for c in text]
    im = Image.new('L', (max(sum(map(char_width, cps)), 1), rbf.h), 0)
    px = im.load()
    x = 0
    for cp in cps:
        w = char_width(cp)
        if rbf.has(cp):
            src, off, cell = rbf.data, (cp - rbf.first) * rbf.char_size, rbf.cell_w
        elif cp in kox.index:
            src, off, cell = kox.bitmaps, kox.index[cp] * kox.glyph_size, kox.cell_bits
        else:
            src = None
        if src is not None:
            for yy in range(rbf.h):
                for xx in range(w):
                    if src[off + yy * cell // 8 + xx // 8] & (1 << (xx % 8)):
                        px[x + xx, yy] = 255
        x += w
    return im


def sample_lines(csv_path):
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8')))
    hang = lambda s: any(0xAC00 <= ord(c) <= 0xD7A3 for c in s)
    names = [r['korean'] for r in rows if r['field'] == 'name' and hang(r['korean'])]
    helps = [r['korean'] for r in rows if r['field'].startswith('help') and hang(r['korean'])]
    others = [r['korean'] for r in rows if any(ord(c) > 0xFF and not 0xAC00 <= ord(c) <= 0xD7A3 for c in r['korean'])]
    return names[:4] + sorted(helps, key=len)[-1:] + others[:2]


def verify(rbf, kox_bytes, name, lines, out_dir, scale):
    kox = KOX(kox_bytes, rbf)
    imgs = [draw_like_camera(rbf, kox, t) for t in lines]
    W = 720
    cv = Image.new('RGB', (W, 4 + len(imgs) * (rbf.h + 2)), (0, 0, 0))
    y = 4
    for im in imgs:
        cv.paste((255, 255, 255), (4, y), im.crop((0, 0, min(im.width, W - 8), im.height)))
        y += rbf.h + 2
    path = os.path.join(out_dir, 'kox_verify_%s.png' % name)
    cv.resize((W * scale, cv.height * scale), Image.NEAREST).save(path)
    return path, max(im.width for im in imgs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--csv', default=os.path.join(REPO, 'tools/i18n/strings_ko.csv'))
    ap.add_argument('--fonts-dir', default=os.path.join(REPO, 'data/fonts'))
    ap.add_argument('--ttf', default=DEFAULT_TTF, help='PATH[:INDEX] for the argnor/arghlf fonts')
    ap.add_argument('--small-ttf', help='PATH[:INDEX] for the --small-names fonts (default: --ttf)')
    ap.add_argument('--small-names', default='term12', help='fonts rendered with --small-ttf')
    ap.add_argument('--names', default=','.join(NAMES))
    ap.add_argument('--threshold', type=int, default=110, help='antialias cutoff (0-255) for 1-bit glyphs')
    ap.add_argument('--spacing', type=int, default=1, help='extra pixels after each glyph')
    ap.add_argument('--size', action='append', default=[], metavar='NAME=PX', help='force the pixel size for one font')
    ap.add_argument('--verify-dir', help='write camera-accurate previews decoded back from the .kox files')
    args = ap.parse_args()

    main_spec = parse_ttf(args.ttf)
    small_spec = parse_ttf(args.small_ttf) if args.small_ttf else main_spec
    forced = {k: int(v) for k, v in (s.split('=') for s in args.size)}
    small_names = set(args.small_names.split(','))
    lines = sample_lines(args.csv)
    if args.verify_dir:
        os.makedirs(args.verify_dir, exist_ok=True)

    print('main font : %s [%d]' % main_spec)
    print('small font: %s [%d]' % small_spec)
    for name in args.names.split(','):
        rbf = RBF(os.path.join(args.fonts_dir, name + '.rbf'))
        spec = small_spec if name in small_names else main_spec
        mode = 'cell' if name.startswith('term') else 'cap'
        chars = needed_chars(args.csv, rbf)
        data, size, base, cell = build(rbf, spec, chars, mode, args.threshold, args.spacing, forced.get(name))
        out = os.path.join(args.fonts_dir, name + '.kox')
        with open(out, 'wb') as f:
            f.write(data)
        msg = '%-9s h=%2d size=%2dpx base=%2d cell=%2d glyphs=%d  %s %d bytes' % (
            name, rbf.h, size, base, cell, len(chars), os.path.basename(out), len(data))
        if args.verify_dir:
            path, widest = verify(rbf, data, name, lines, args.verify_dir, 3 if rbf.h < 16 else 2)
            msg += '  verify=%s widest_line=%dpx' % (os.path.basename(path), widest)
        print(msg)


if __name__ == '__main__':
    main()
