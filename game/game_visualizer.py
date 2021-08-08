# Type annotations without import
from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(path)

from typing import List
from PIL import Image, ImageDraw
from draw import LARGE_FONT, LARGE_BOLD_FONT, break_text

N_MARKER_MAX = 10;
MARKER_WIDTH = 77;
MARKER_HEIGHT = 77;
TEAM_IMAGES = [Image.open(f"./resources/team{i}.png").convert('RGBA') for i in range(N_MARKER_MAX)]
MAP_IMAGE = Image.open("./resources/map.png").convert('RGBA')

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

    result_height += label_text_max_height
    result = Image.new(mode='RGBA', size=(base_width, result_height), color=(54, 57, 63))
    layer2 = Image.new(mode='RGBA', size=(base_width, result_height), color=(0, 0, 0, 0))
    result.paste(im=MAP_IMAGE, box=(0, 0), mask=MAP_IMAGE)
    draw = ImageDraw.Draw(layer2)

    for i, (poi, label) in enumerate(zip(pois, labels)):
        layer2.paste(im=TEAM_IMAGES[i], box=(int(label_start_x_center - MARKER_WIDTH/2 + i*single_width), label_start_y))
        layer2.paste(im=TEAM_IMAGES[i], box=(int(poi[0] - MARKER_WIDTH/2), int(poi[1] - MARKER_WIDTH/2)))
        draw.text((int(label_start_x_center + i*single_width), label_text_y+42), label, font=LARGE_FONT, anchor="ms", fill=(255, 255, 255))
    return Image.alpha_composite(result, layer2)

out = render_map([[500, 500], [1000, 1000]], ["a", "b"*200])
with open("out.png", 'wb') as outfile:
    out.save(outfile)
