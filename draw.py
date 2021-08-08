from PIL import Image, ImageDraw, ImageFont
import math

#NORMAL_FONT = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 16)
#BOLD_FONT = ImageFont.truetype("Pillow/Tests/fonts/FreeMonoBold.ttf", 16)
NORMAL_FONT_SIZE = 16
NORMAL_FONT = ImageFont.truetype("./fonts/FreeSans.ttf", NORMAL_FONT_SIZE)
BOLD_FONT = ImageFont.truetype("./fonts/FreeSansBold.ttf", NORMAL_FONT_SIZE)
LARGE_FONT_SIZE = 40
LARGE_FONT = ImageFont.truetype("./fonts/FreeSans.ttf", LARGE_FONT_SIZE)
LARGE_BOLD_FONT = ImageFont.truetype("./fonts/FreeSansBold.ttf", LARGE_FONT_SIZE)

def break_text(text: str, draw: ImageDraw, font: ImageFont, max_width: float):
    """
    Break text so that it is at most X pixels wide.
    Will not respect newlines in the input (converts them to spaces).
    """
    max_width = math.floor(max_width)
    split_points = text.replace('\n', ' ').split(' ')
    lines = []
    current_line = None
    while len(split_points):
        if current_line is None:
            tmp_line = split_points[0]
        else:
            tmp_line = current_line + ' ' + split_points[0]
        # Ignore height.
        pixel_width, _ = draw.textsize(tmp_line, font=font)
        if pixel_width > max_width:
            if current_line is None:
                for i in range(1, len(tmp_line)):
                    pixel_width, _ = draw.textsize(tmp_line[:i], font=font)
                    if pixel_width > max_width:
                        break
                passing = i-1
                lines.append(tmp_line[:passing])
                split_points[0] = tmp_line[passing:]
            else:
                lines.append(current_line)
                current_line = None
        else:
            current_line = tmp_line
            split_points.pop(0)
    if current_line is not None:
        lines.append(current_line)
    return '\n'.join(lines)

