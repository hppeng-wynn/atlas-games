# Type annotations without import
from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(path)

from typing import List
from PIL import Image, ImageDraw
from draw import LARGE_FONT, LARGE_BOLD_FONT, LARGE_FONT_SIZE, break_text

N_MARKER_MAX = 10;
MARKER_WIDTH = 77;
MARKER_HEIGHT = 77;
TEAM_IMAGES = [Image.open(f"./resources/team{i}.png").resize((MARKER_WIDTH, MARKER_HEIGHT)).convert('RGBA') for i in range(N_MARKER_MAX)]
MAP_IMAGE = Image.open("./resources/map.png").convert('RGBA')
# scale things down.. too slow
SCALE_FACTOR=2
MAP_IMAGE = MAP_IMAGE.resize((int(MAP_IMAGE.size[0]/SCALE_FACTOR), int(MAP_IMAGE.size[1]/SCALE_FACTOR)))

def render_map(pois: List[Point], labels: List[str]):
    pois = pois[:min(N_MARKER_MAX, len(pois))]
    labels = labels[:min(N_MARKER_MAX, len(labels))]
    base_width, base_height = MAP_IMAGE.size

    label_start_y = base_height
    result_height = label_start_y + MARKER_HEIGHT;
    single_width = base_width / N_MARKER_MAX;
    used_width = single_width * len(labels)
    label_start_x_center = (base_width - used_width + single_width)/2
    max_label_width = single_width - 20;

    draw = ImageDraw.Draw(MAP_IMAGE)

    label_text_y = result_height
    label_text_max_height = 0
    for i, label in enumerate(labels):
        txt = break_text(label, draw, LARGE_FONT, max_label_width)
        _, pixel_height = draw.textsize(txt, font=LARGE_BOLD_FONT)
        label_text_max_height = max(label_text_max_height, pixel_height)
        labels[i] = txt

    # Arbitrary bottom padding?
    result_height += label_text_max_height + 15
    result = Image.new(mode='RGBA', size=(base_width, result_height), color=(54, 57, 63))
    result.paste(im=MAP_IMAGE, box=(0, 0), mask=MAP_IMAGE)

    for i, (poi, label) in enumerate(zip(pois, labels)):
        layer = Image.new(mode='RGBA', size=(base_width, result_height), color=(0, 0, 0, 0))
        layer.paste(im=TEAM_IMAGES[i], box=(int(label_start_x_center - MARKER_WIDTH/2 + i*single_width), label_start_y))
        layer.paste(im=TEAM_IMAGES[i], box=(int(poi[0]/SCALE_FACTOR - MARKER_WIDTH/2), int(poi[1]/SCALE_FACTOR - MARKER_WIDTH/2)))
        draw = ImageDraw.Draw(layer)
        draw.text((int(label_start_x_center + i*single_width), label_text_y+LARGE_FONT_SIZE), label, font=LARGE_FONT, anchor="ms", fill=(255, 255, 255))
        result = Image.alpha_composite(result, layer)
    return result

if __name__ == "__main__":
    out = render_map([[500, 500], [1000, 1000], [1000, 500], [500, 1000], [1500, 500], [1500, 1000], [1500, 1500]], ["nuts", "bothades", "stress", "test", "longer team name go brr", "hello", "world"])
    with open("out.png", 'wb') as outfile:
        out.save(outfile)
