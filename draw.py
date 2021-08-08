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
    _split_points = (t.replace('*', '* *').split('*') for t in text.replace('\n', ' ').split(' '))
    split_points = []
    for arr in _split_points:
        split_points += arr

    lines = []
    prev_length = 0
    prev_text = ""
    current_line = None
    bold_mode = False
    active_fonts = [font.normal, font.bold]
    while len(split_points):
        if split_points[0] == ' ':
            # Bold transition.
            prev_length += draw.textsize(tmp_line, font=active_fonts[bold_mode])
            if current_line == "":
                prev_text = "*"
            else:
                prev_text += current_line+' *'
            current_line = ""
            bold_mode = not bold_mode
            continue

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
                current_line = ""
        else:
            current_line = tmp_line
            split_points.pop(0)
    if current_line is not None:
        lines.append(current_line)
    return '\n'.join(lines)

def format_tokenize(text: str):
    r"""
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
                if cur is None:
                    cur = char
                else:
                    cur += char
                continue
            if cur is None:
                pass
                #res.append("")
            elif cur != "":
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
        if char in ' \n':
            if cur is None:
                res.append("")
            elif cur != "":
                res.append(cur)
            cur = None
            continue
        if cur is None:
            res.append("")
            cur = char
        else:
            cur += char
    if escape_mode:
        raise TypeError("Unterminated \\")
    if cur is None:
        res.append("")
    elif cur != "":
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
    test(format_tokenize, ['asdf bsdf\ncsdf'], name="space and newline", expect=['asdf', '', 'bsdf', '', 'csdf'])
    test(format_tokenize, [' asdf'], name="leading space", expect=['', 'asdf'])
    test(format_tokenize, ['     '], name="all space", expect=['', '', '', '', ''])
    test(format_tokenize, ['asdf '], name="trailing space", expect=['asdf', ''])
    test(format_tokenize, [r'\*a\*'], name="bold", expect=[FontFormat.BOLD, 'a', FontFormat.BOLD])
    test(format_tokenize, [r' \*a'], name="leading space B", expect=['', FontFormat.BOLD, 'a'])
    test(format_tokenize, [r'\* a'], name="leading B space", expect=[FontFormat.BOLD, '', 'a'])
    test(format_tokenize, [r'a\* '], name="trailing space B", expect=['a', FontFormat.BOLD, ''])
