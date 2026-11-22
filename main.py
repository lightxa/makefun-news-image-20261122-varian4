"""Sunday around the world: 22 November 2026 in one image.

A horizontal UTC timeline (00:00-24:00) with six story cards placed at
their times, under a big masthead naming the day. Pure stdlib: the image
is drawn procedurally into an RGB buffer and encoded as PNG by hand
(zlib + struct). No network, no randomness, no time dependence, so every
run writes byte-identical output.
"""

import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (247, 242, 232)
INK = (24, 24, 40)
WHITE = (255, 255, 255)
GREY = (120, 116, 108)
LIGHT = (232, 226, 212)

# 5x7 bitmap font. Each glyph is 7 rows of 5 pixels.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
}


def text_width(text, scale):
    """Pixel width of text at the given scale."""
    return len(text) * 6 * scale - scale


def draw_text(px, x, y, text, scale, color):
    """Draw uppercase bitmap text; returns the width drawn."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            set_pixel(px, cx + col * scale + dx,
                                      y + row * scale + dy, color)
        cx += 6 * scale
    return cx - x - scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines."""
    lines = []
    current = ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def set_pixel(px, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i], px[i + 1], px[i + 2] = color


def fill_rect(px, x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            set_pixel(px, xx, yy, color)


def draw_line(px, x0, y0, x1, y1, color, thick=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ty in range(thick):
            for tx in range(thick):
                set_pixel(px, x0 + tx, y0 + ty, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def fill_circle(px, cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        for xx in range(cx - dx, cx + dx + 1):
            set_pixel(px, xx, cy + dy, color)


def ring_circle(px, cx, cy, r, color, thick=2):
    for dy in range(-r - thick, r + thick + 1):
        for dx in range(-r - thick, r + thick + 1):
            d = (dx * dx + dy * dy) ** 0.5
            if r - thick < d <= r:
                set_pixel(px, cx + dx, cy + dy, color)


def fill_triangle(px, x0, y0, x1, y1, x2, y2, color):
    ys = sorted([y0, y1, y2])
    for yy in range(ys[0], ys[2] + 1):
        xs = []
        for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2),
                                 (x2, y2, x0, y0)):
            if ay == by:
                continue
            if min(ay, by) <= yy <= max(ay, by):
                t = (yy - ay) / (by - ay)
                xs.append(ax + t * (bx - ax))
        if len(xs) >= 2:
            for xx in range(int(min(xs)), int(max(xs)) + 1):
                set_pixel(px, xx, yy, color)


def draw_icon(px, kind, cx, cy, color):
    """Small procedural pictogram centred at (cx, cy), ~56 px wide."""
    if kind == "cricket":
        fill_circle(px, cx + 12, cy - 8, 10, color)
        draw_line(px, cx - 18, cy + 16, cx + 2, cy - 6, color, thick=6)
    elif kind == "ballot":
        fill_rect(px, cx - 18, cy - 4, 36, 5, color)
        fill_rect(px, cx - 18, cy + 22, 36, 5, color)
        fill_rect(px, cx - 18, cy - 4, 5, 31, color)
        fill_rect(px, cx + 13, cy - 4, 5, 31, color)
        draw_line(px, cx - 8, cy + 6, cx + 8, cy + 6, color, thick=3)
        draw_line(px, cx - 8, cy - 14, cx - 2, cy - 6, color, thick=3)
        draw_line(px, cx - 2, cy - 6, cx + 14, cy - 20, color, thick=3)
    elif kind == "sun":
        fill_circle(px, cx, cy, 11, color)
        offs = [(20, 0), (14, 14), (0, 20), (-14, 14),
                (-20, 0), (-14, -14), (0, -20), (14, -14)]
        for k in range(8):
            ox, oy = offs[k]
            draw_line(px, cx + int(ox * 0.75), cy + int(oy * 0.75),
                      cx + ox, cy + oy, color, thick=2)
    elif kind == "cedar":
        fill_triangle(px, cx, cy - 22, cx - 16, cy + 2, cx + 16, cy + 2, color)
        fill_triangle(px, cx, cy - 12, cx - 20, cy + 14, cx + 20, cy + 14, color)
        fill_rect(px, cx - 3, cy + 14, 6, 10, color)
    elif kind == "globe":
        ring_circle(px, cx, cy, 18, color, thick=3)
        draw_line(px, cx, cy - 18, cx, cy + 18, color, thick=2)
        draw_line(px, cx - 18, cy, cx + 18, cy, color, thick=2)
        draw_line(px, cx - 15, cy - 9, cx + 15, cy - 9, color, thick=2)
        draw_line(px, cx - 15, cy + 9, cx + 15, cy + 9, color, thick=2)
    elif kind == "percent":
        draw_text(px, cx - 22, cy - 14, "3%", 4, color)
    elif kind == "triangle":
        # Three bright points joined as a triangle: Mars, Jupiter, Regulus.
        ax, ay = cx, cy - 20
        bx, by = cx - 19, cy + 13
        dx, dy = cx + 19, cy + 13
        draw_line(px, ax, ay, bx, by, color, thick=3)
        draw_line(px, bx, by, dx, dy, color, thick=3)
        draw_line(px, dx, dy, ax, ay, color, thick=3)
        for vx, vy in ((ax, ay), (bx, by), (dx, dy)):
            fill_circle(px, vx, vy, 5, color)
    elif kind == "lifebuoy":
        ring_circle(px, cx, cy, 16, color, thick=4)
        draw_line(px, cx - 16, cy, cx + 16, cy, color, thick=3)
        draw_line(px, cx, cy - 16, cx, cy + 16, color, thick=3)


# The six stories, in UTC order. Times are UTC on 22 November 2026.
STORIES = [
    {
        "time": "00:00", "hour": 0.0,
        "tag": "SPORT . WELLINGTON", "place": "WELLINGTON",
        "headline": "PANT 128",
        "summary": "PANT HITS 128 AS INDIA LEAD BY 261 IN WELLINGTON",
        "accent": (46, 125, 50), "icon": "cricket",
    },
    {
        "time": "01:00", "hour": 1.0,
        "tag": "POLITICS . HONG KONG", "place": "HONG KONG",
        "headline": "HONG KONG VOTES",
        "summary": "856 CANDIDATES CHASE 723 SEATS IN POLLS OPEN 9AM",
        "accent": (178, 52, 42), "icon": "ballot",
    },
    {
        "time": "05:00", "hour": 5.0,
        "tag": "SKY . WORLD", "place": "WORLD",
        "headline": "SKY TRIANGLE",
        "summary": "MARS JUPITER AND REGULUS FORM A TRIANGLE BEFORE DAWN",
        "accent": (63, 58, 150), "icon": "triangle",
    },
    {
        "time": "06:00", "hour": 6.0,
        "tag": "CLIMATE . ANTALYA", "place": "ANTALYA",
        "headline": "COP31 DEAL VOTE",
        "summary": "ANTALYA: FINAL TEXT GOES TO A VOTE ON SUNDAY",
        "accent": (201, 138, 27), "icon": "sun",
    },
    {
        "time": "07:00", "hour": 7.0,
        "tag": "MIDDLE EAST . BEIRUT", "place": "BEIRUT",
        "headline": "LEBANON 83",
        "summary": "BEIRUT MARKS 83 YEARS OF INDEPENDENCE",
        "accent": (31, 58, 95), "icon": "cedar",
    },
    {
        "time": "12:00", "hour": 12.0,
        "tag": "AFRICA . NIGERIA", "place": "BAYELSA",
        "headline": "BAYELSA SEARCH",
        "summary": "SEARCH FOR MISSING BOAT PASSENGERS GOES ON INTO SUNDAY",
        "accent": (14, 124, 107), "icon": "lifebuoy",
    },
]


def draw_card(px, story, x, y, w, h):
    accent = story["accent"]
    fill_rect(px, x, y, w, h, WHITE)
    fill_rect(px, x, y, w, 8, accent)
    # Time badge.
    fill_rect(px, x + 16, y + 20, 118, 26, accent)
    draw_text(px, x + 26, y + 26, story["time"] + " UTC", 2, WHITE)
    # Pictogram, bottom right (keeps the tag line clear).
    draw_icon(px, story["icon"], x + w - 54, y + h - 66, accent)
    # Tag line.
    draw_text(px, x + 16, y + 62, story["tag"], 2, accent)
    # Headline, up to two lines.
    lines = wrap_text(story["headline"], w - 32, 3)
    hy = y + 92
    for line in lines[:2]:
        draw_text(px, x + 16, hy, line, 3, INK)
        hy += 28
    # Rule.
    fill_rect(px, x + 16, y + 158, w - 32, 3, LIGHT)
    # Summary.
    sy = y + 176
    for line in wrap_text(story["summary"], w - 32, 2)[:4]:
        draw_text(px, x + 16, sy, line, 2, INK)
        sy += 20
    # Bottom accent underline.
    fill_rect(px, x + 16, y + h - 18, w - 32, 3, accent)


def draw_timeline(px):
    x0, x1, y = 60, 964, 178
    draw_text(px, x0, 146, "ALL TIMES UTC", 2, GREY)
    draw_line(px, x0, y, x1, y, INK, thick=3)
    for hour in range(0, 25, 4):
        tx = x0 + int(hour * (x1 - x0) / 24)
        draw_line(px, tx, y - 8, tx, y + 8, INK, thick=3)
        label = "%02d" % hour
        draw_text(px, tx - 12, y + 14, label, 2, GREY)
    # Story markers, labels staggered on two rows to avoid collisions.
    for i, story in enumerate(STORIES):
        mx = x0 + int(story["hour"] * (x1 - x0) / 24)
        fill_circle(px, mx, y, 8, story["accent"])
        ring_circle(px, mx, y, 8, INK, thick=1)
        label = story["time"]
        ly = y + 30 if i % 2 == 0 else y + 56
        draw_text(px, mx - 30, ly, label, 2, story["accent"])


def build_image():
    px = bytearray(PAPER * W * H)
    # Masthead.
    title = "SUNDAY 22 NOVEMBER 2026"
    tw = text_width(title, 6)
    draw_text(px, (W - tw) // 2, 36, title, 6, INK)
    sub = "THE WORLD IN ONE DAY"
    draw_text(px, (W - text_width(sub, 3)) // 2, 94, sub, 3, (178, 52, 42))
    fill_rect(px, 48, 130, W - 96, 3, INK)
    # Timeline.
    draw_timeline(px)
    # Cards: 3 columns x 2 rows.
    cw, ch, gap = 296, 336, 20
    for i, story in enumerate(STORIES):
        cx = 48 + (i % 3) * (cw + gap)
        cy = 252 + (i // 3) * (ch + gap)
        draw_card(px, story, cx, cy, cw, ch)
    # Footer.
    foot1 = "ALL EVENTS HAPPENED OR WERE FIRST REPORTED ON SUNDAY 22 NOVEMBER 2026"
    draw_text(px, (W - text_width(foot1, 2)) // 2, 956, foot1, 2, INK)
    foot2 = "SOURCES: REUTERS, CHINA DAILY, IANS, INSIGHT INTERNATIONAL, BBC SKY AT NIGHT, NNU"
    draw_text(px, (W - text_width(foot2, 2)) // 2, 980, foot2, 2, GREY)
    return px


def write_png(px, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    px = build_image()
    write_png(px, os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
