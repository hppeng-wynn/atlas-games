#from game.game_state import GameState
from PIL import Image, ImageDraw, ImageFont

TEAM_IMAGES = [Image.open(f"./resources/team{i}.png") for i in range(10)]
MAP_IMAGE = Image.open("./resources/map.png")

def render_map():
    pass


N=100
# create an image
out = Image.new("RGB", (int(9.6*(N+1)), 50), (0, 0, 0))

# get a font
# fnt = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", 16)
fnt = ImageFont.truetype("Pillow/Tests/fonts/FreeMonoBold.ttf", 16)
# get a drawing context
d = ImageDraw.Draw(out)

# draw multiline text
d.multiline_text((0,10), "w"*N+"\n"+"W"*N, font=fnt, fill=(255, 255, 255))

out.show()
