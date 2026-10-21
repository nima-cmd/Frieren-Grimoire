#!/usr/bin/env python3
"""Generate a Swift key layout from a Polychromatic device-map SVG.

Polychromatic (https://github.com/polychromatic/polychromatic, GPLv3) draws each
LED as an element with id "x<col>-y<row>" (the Chroma matrix position). This
script takes each key's bounding box and label and writes a Swift table.

It also reads Polychromatic's scancode map (Linux evdev keycode -> [column, row])
and converts keycodes to HID keyboard usages (page 0x07) with the table from the
Linux kernel's drivers/hid/hid-input.c, so each key knows what it sends.

Usage: python3 tools/extract_layout.py blackwidow_elite_en_US.svg blackwidow_elite.json \\
           > RazerKit/Sources/RazerKit/BlackWidowEliteLayout.swift
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")
ARGS = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}


def path_points(d):
    """All end and control points of a path (good enough for a bounding box)."""
    tokens = TOKEN.findall(d)
    points, x, y, start, cmd, i = [], 0.0, 0.0, (0.0, 0.0), None, 0
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                x, y = start
                continue
        n = ARGS[cmd.lower()]
        vals = [float(v) for v in tokens[i:i + n]]
        i += n
        rel = cmd.islower()
        c = cmd.lower()
        if c == "h":
            x = x + vals[0] if rel else vals[0]
        elif c == "v":
            y = y + vals[0] if rel else vals[0]
        elif c == "a":
            x, y = (x + vals[5], y + vals[6]) if rel else (vals[5], vals[6])
        else:
            pairs = list(zip(vals[0::2], vals[1::2]))
            for px, py in pairs[:-1]:
                points.append((x + px, y + py) if rel else (px, py))
            ex, ey = pairs[-1]
            x, y = (x + ex, y + ey) if rel else (ex, ey)
        points.append((x, y))
        if c == "m":
            start = (x, y)
            cmd = "l" if rel else "L"  # implicit lineto after moveto
    return points


def parse_transform(text):
    """SVG transform attribute -> affine (a, b, c, d, e, f)."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.split(r"[ ,]+", args.strip()) if x]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "matrix":
            t = tuple(v)
        else:
            raise ValueError(f"unsupported transform {name}")
        m = compose(m, t)
    return m


def compose(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f)


def transform_to_root(element, parents):
    chain = []
    while element is not None:
        chain.append(element)
        element = parents.get(element)
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for node in reversed(chain):
        m = compose(m, parse_transform(node.get("transform")))
    return m


# HID keyboard usage -> Linux keycode, from hid-input.c's hid_keyboard[] (0x04-0x65, 0xE0-0xE7).
HID_TO_EVDEV = dict(zip(range(0x04, 0x66), [
    30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44,
    2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
    28, 1, 14, 15, 57, 12, 13, 26, 27, 43, 0, 39, 40, 41, 51, 52, 53, 58,
    59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 87, 88,
    99, 70, 119, 110, 102, 104, 111, 107, 109, 106, 105, 108, 103,
    69, 98, 55, 74, 78, 96, 79, 80, 81, 75, 76, 77, 71, 72, 73, 82, 83, 86, 127,
]))
HID_TO_EVDEV.update(zip(range(0xE0, 0xE8), [29, 42, 56, 125, 97, 54, 100, 126]))
EVDEV_TO_HID = {code: usage for usage, code in HID_TO_EVDEV.items() if code}


def usages_by_position(scancode_path):
    with open(scancode_path) as f:
        scancodes = json.load(f)
    usages = {(row, col): EVDEV_TO_HID[int(code)]
              for code, (col, row) in scancodes.items() if code.isdigit() and int(code) in EVDEV_TO_HID}
    # Polychromatic lists Delete as keycode 114 (volume down); it's 111 -> HID 0x4C.
    usages[(2, 15)] = 0x4C
    return usages


# Keys whose printed legend is an icon rather than text (macOS names where it helps).
LABELS = {
    (0, 18): "prev", (0, 19): "play", (0, 20): "next", (0, 21): "dial",
    (1, 14): "backspace", (4, 16): "↑", (5, 2): "⌘", (5, 6): "space",
    (5, 11): "logo", (5, 13): "menu", (5, 15): "←", (5, 16): "↓", (5, 17): "→",
}


def main(path, scancode_path):
    usages = usages_by_position(scancode_path)
    root = ET.parse(path).getroot()
    parents = {child: parent for parent in root.iter() for child in parent}
    keys = {}
    for element in root.iter():
        m = re.fullmatch(r"x(\d+)-y(\d+)", element.get("id", ""))
        if not m:
            continue
        col, row = int(m.group(1)), int(m.group(2))
        if (row, col) in keys:
            continue  # the spacebar's outline path repeats its group's id
        # The first path is the keycap outline; later ones are legend icons.
        outline = element if element.tag == NS + "path" else element.find(NS + "path")
        a, b, c, d, e, f = transform_to_root(outline, parents)
        points = [(a * x + c * y + e, b * x + d * y + f) for x, y in path_points(outline.get("d", ""))]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        label = " ".join(" ".join(t.itertext()) for t in element.iter(NS + "text"))
        label = LABELS.get((row, col), " ".join(label.split()))
        keys[(row, col)] = (row, col, label, min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    # The media buttons are circles whose outlines my path parser over-measures
    # (bezier control points, a mirrored arc). Put them over the numpad's
    # num lock, / and * columns, sized like those keys.
    for media, numpad in ((18, 18), (19, 19), (20, 20)):
        _, _, label, _, y, _, _ = keys[(0, media)]
        _, _, _, x, _, w, h = keys[(1, numpad)]
        keys[(0, media)] = (0, media, label, x, y, w, h)
    keys = list(keys.values())

    min_x, min_y = min(k[3] for k in keys), min(k[4] for k in keys)
    print("// Generated by tools/extract_layout.py from Polychromatic's blackwidow_elite_en_US.svg.")
    print("// Positions are in SVG points; row/column are Chroma matrix coordinates;")
    print("// usage is the HID keyboard usage (page 0x07) the key sends, nil for fn, media keys, dial and logo.\n")
    print("extension KeyboardLayout {")
    print("    public static let blackWidowElite = KeyboardLayout(rows: 6, columns: 22, keys: [")
    for row, col, label, x, y, w, h in sorted(keys, key=lambda k: (k[0], k[1])):
        label = label.replace("\\", "\\\\").replace('"', '\\"')
        usage = usages.get((row, col))
        usage = f"0x{usage:02X}" if usage is not None else "nil"
        print(f'        Key(row: {row}, column: {col}, label: "{label}", usage: {usage}, '
              f"x: {x - min_x:.1f}, y: {y - min_y:.1f}, width: {w:.1f}, height: {h:.1f}),")
    print("    ])")
    print("}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
