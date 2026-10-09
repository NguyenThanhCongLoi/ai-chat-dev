"""Extract the supplied loading sheet in reading order, without redrawing it.

Run: python scripts/build_loading_cat.py
Coordinates use the 1024 x 846 layout; the source can be higher resolution.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "image/loading-cat-sheet.png.png"
OUTPUT = ROOT / "frontend/public/assets"
SIZE = (240, 180)

FRAMES = {
    "walk": [(x, y, right, bottom) for y, bottom in [(44, 136), (139, 229)]
             for x, right in [(20, 166), (178, 320), (326, 493), (500, 650), (655, 818), (834, 993)]],
    "run": [(x, y, right, bottom) for y, bottom in [(281, 355), (367, 456)]
            for x, right in [(20, 205), (223, 403), (417, 593), (610, 793), (810, 993)]],
    "butterfly": [
        (19, 505, 161, 598), (189, 511, 342, 599), (355, 509, 485, 599),
        (17, 620, 207, 717), (194, 603, 322, 715), (323, 601, 494, 696),
        (494, 596, 635, 714), (635, 596, 778, 717), (770, 605, 873, 718),
        (873, 597, 1001, 711), (22, 750, 138, 835), (151, 724, 273, 835),
        (276, 733, 364, 835), (389, 721, 533, 835),
    ],
}


def extract(source, rect, action, index):
    scale = source.width / 1024
    crop = source.crop(tuple(round(value * scale) for value in rect)).convert("RGBA")
    pixels = np.array(crop)
    rgb = pixels[:, :, :3].astype(float)
    # The sheet background is neutral gray. Dark outlines and the dark cat
    # remain opaque; colored wings, tail, dust and butterfly glow are retained.
    neutral = rgb.max(axis=2) - rgb.min(axis=2)
    brightness = rgb.mean(axis=2)
    background = (neutral < 12) & (brightness > 70) & (brightness < 130)
    pixels[:, :, 3] = np.where(background, 0, 255)
    # Unmatte the turquoise glow against the gray sheet, including its fringe.
    glow = (brightness > 72) & (rgb[:, :, 1] > rgb[:, :, 0] + 9) & (rgb[:, :, 2] > rgb[:, :, 0] + 9)
    alpha = np.clip(neutral / 100, 0.02, 1)
    pixels[glow, :3] = np.clip((rgb[glow] - 89 * (1 - alpha[glow, None])) / alpha[glow, None], 0, 255)
    pixels[glow, 3] = (alpha[glow] * 255).astype(np.uint8)
    crop = Image.fromarray(pixels)
    # Irregular spacing in the butterfly row needs masks to keep adjacent
    # tails and butterfly halos out of these cells.
    if action == "butterfly":
        exclusions = {
            3: [(194, 620, 207, 660)],
            4: [(194, 666, 217, 715), (194, 603, 218, 635), (218, 603, 250, 609)],
            7: [(635, 596, 650, 652), (768, 650, 778, 717)],
            8: [(770, 605, 783, 644)],
        }
        mask_draw = ImageDraw.Draw(crop)
        for left, top, right, bottom in exclusions.get(index, []):
            mask_draw.rectangle(tuple(round(v * scale) for v in
                (left - rect[0], top - rect[1], right - rect[0], bottom - rect[1])), fill=(0, 0, 0, 0))
    crop = crop.crop(crop.getbbox())
    crop.thumbnail((round(crop.width / scale * 1.12), round(crop.height / scale * 1.12)), Image.Resampling.LANCZOS)
    return crop


def main():
    source = Image.open(SOURCE)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    preview = Image.new("RGB", (6 * SIZE[0], 6 * (SIZE[1] + 22)), "#f4f4f5")
    draw = ImageDraw.Draw(preview)
    preview_index = 0
    for action, rects in FRAMES.items():
        atlas = Image.new("RGBA", (SIZE[0] * len(rects), SIZE[1]))
        for index, rect in enumerate(rects):
            sprite = extract(source, rect, action, index)
            frame = Image.new("RGBA", SIZE)
            # A shared scale and baseline prevent bouncing caused by fitting
            # each crop independently. Leaping poses deliberately sit higher.
            lift = {3: 18, 4: 6, 5: 30, 6: 4, 7: 4, 9: 18}.get(index, 0) if action == "butterfly" else 0
            pixels = np.array(sprite)
            cat = (pixels[:, :, :3].mean(axis=2) < 70) & (pixels[:, :, 3] > 180)
            _, cat_x = np.where(cat)
            center = (int(cat_x.min()) + int(cat_x.max())) // 2
            frame.alpha_composite(sprite, (SIZE[0] // 2 - center, 158 - sprite.height - lift))
            atlas.alpha_composite(frame, (index * SIZE[0], 0))
            x = preview_index % 6 * SIZE[0]
            y = preview_index // 6 * (SIZE[1] + 22)
            preview.paste(frame, (x, y), frame)
            draw.text((x + 8, y + SIZE[1]), f"{action} {index + 1}", fill="#27272a")
            preview_index += 1
        atlas.save(OUTPUT / f"loading-cat-{action}-sprite.webp", lossless=True)
        print(f"{action}: {len(rects)} frames, {atlas.size}")
    report = ROOT / "reports/loading-cat-frames.jpg"
    preview.save(report, quality=92)
    print(report)


if __name__ == "__main__":
    main()
