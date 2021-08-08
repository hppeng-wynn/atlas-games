from PIL import Image, ImageDraw, ImageFont
import math
from collections import namedtuple
from enum import Enum

#NORMAL_FONT = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 16)
#BOLD_FONT = ImageFont.truetype("Pillow/Tests/fonts/FreeMonoBold.ttf", 16)
Font = namedtuple("Font", ["size", "normal", "bold"])
NORMAL_FONT_SIZE = 16
NORMAL_FONT = Font(NORMAL_FONT_SIZE,
                ImageFont.truetype("./fonts/FreeSans.ttf", NORMAL_FONT_SIZE),
                ImageFont.truetype("./fonts/FreeSansBold.ttf", NORMAL_FONT_SIZE))
LARGE_FONT_SIZE = 40
LARGE_FONT = Font(LARGE_FONT_SIZE,
                ImageFont.truetype("./fonts/FreeSans.ttf", LARGE_FONT_SIZE),
                ImageFont.truetype("./fonts/FreeSansBold.ttf", LARGE_FONT_SIZE))

class FontFormat(Enum):
    BOLD=0
    UNDERLINE=1
    ITALIC=2


def break_text(text: str, draw: ImageDraw, font: Font, max_width: float):
    """
    Break text so that it is at most X pixels wide.
    Will not respect newlines in the input (converts them to spaces).
    """
    max_width = math.floor(max_width)
    mode_changes = format_tokenize(text)
    prev_length = 0
    bold_mode = False
    lines = []
    prev_text = ""
    current_line = ""
    active_fonts = [font.normal, font.bold]
    for content in mode_changes:
        if content == FontFormat.BOLD:
            pixel_width, _ = draw.textsize(current_line, font=active_fonts[bold_mode])
            prev_length += pixel_width
            prev_text += r'\*'
            bold_mode = not bold_mode
            continue
        elif content == FontFormat.UNDERLINE:
            continue
        elif content == FontFormat.ITALIC:
            continue
        split_points = content.replace('\n', ' ').split(' ')

        while len(split_points):
            if current_line == "":
                tmp_line = split_points[0]
            else:
                tmp_line = current_line + ' ' + split_points[0]
            # Ignore height.
            pixel_width, _ = draw.textsize(tmp_line, font=active_fonts[bold_mode])
            if pixel_width + prev_length > max_width:
                if current_line == "" and prev_text == "":
                    for i in range(1, len(tmp_line)):
                        pixel_width, _ = draw.textsize(tmp_line[:i], font=active_fonts[bold_mode])
                        if pixel_width + prev_length > max_width:
                            break
                    passing = i-1
                    lines.append(tmp_line[:passing])
                    split_points[0] = tmp_line[passing:]
                else:
                    lines.append(prev_text + current_line)
                    prev_length = 0
                    prev_text = ""
                    current_line = ""
            else:
                current_line = tmp_line
                split_points.pop(0)
        prev_text += current_line
    if prev_text is not None:
        lines.append(prev_text)
    return '\n'.join(lines)

def format_tokenize(text: str):
    """
    Split text by space/newline, but also split out `FontFormat`s
    \\: \
    \*: bold
    \_: underline
    \|: italic
    """
    res = []
    cur = ""
    escape_mode = False
    for char in text:
        if escape_mode:
            escape_mode = False
            if char == '\\':
                cur += char
                continue
            if cur != "":
                res.append(cur)
            if char == '*':
                res.append(FontFormat.BOLD)
            elif char == '_':
                res.append(FontFormat.UNDERLINE)
            elif char == '|':
                res.append(FontFormat.ITALIC)
            else:
                raise TypeError(f"Invalid format [{char}]")
            cur = ""
            continue
        if char == '\\':
            escape_mode = True
            continue
        escape_mode = False
        cur += char
    if escape_mode:
        raise TypeError("Unterminated \\")
    if cur != "":
        res.append(cur)
    return res

if __name__ == "__main__":
    # Self test scripts.
    def test(f, args=[], kwargs={}, name=None, expect=None, compare=lambda a, b: a == b, err=False):
        if name is not None:
            print("test "+name)
        if err:
            try:
                f(*args, **kwargs)
                print("Excepted error but got none")
                return False
            except Exception as e:
                print("OK")
                return True
        res = f(*args, **kwargs)
        if compare(res, expect):
            print("OK")
            return True
        print(f"Assertion fail: {res}, {expect}")
        return False
    print("draw.py self test")
    test(format_tokenize, ['asdf'], name="basic", expect=['asdf'])
    test(format_tokenize, [r'\*a\*'], name="bold", expect=[FontFormat.BOLD, 'a', FontFormat.BOLD])
    test(format_tokenize, [r' \*a'], name="leading space B", expect=[' ', FontFormat.BOLD, 'a'])
    test(format_tokenize, [r'\* a'], name="leading B space", expect=[FontFormat.BOLD, ' a'])
    test(format_tokenize, [r'a\* '], name="trailing space B", expect=['a', FontFormat.BOLD, ' '])
