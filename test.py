from PIL import Image, ImageDraw
import requests
import draw

size = (480,480)

#download example pfp and crop to 64x64 thumbnail
pfp = Image.open(requests.get("https://cdn.discordapp.com/attachments/297190249774448640/850845006629175356/358a354cb094544a0ed7afb7f9b4b6cd.png", stream = True).raw)
pfp.thumbnail((64, 64), Image.ANTIALIAS)
pfp = pfp.resize((64, 64))

#c = (255, 255, 255, 0)
c = (54, 57, 63, 255)

#new image with transparent background
bckgrd = Image.new('RGBA', size, color = c)

(TLx, TLy) = (32, 32)

for i in range(6):
    bckgrd.paste(pfp, box = (TLx + (i * (TLx + pfp.size[0])), TLy))

font_used = draw.NORMAL_FONT

#break up text
text = "Your mother. \n Bottom Text. \n Deez nuts. \n I've finally found it: A tomato trellis that won't collapse or blow over under the weight of my tomato plants. You can make it in about an hour with common materials..."
text = draw.break_text(text, ImageDraw.Draw(bckgrd), font_used, 40)
#text = "Hey want some dn? \nWhat's dn \n\*deez nuts\* LMAOOOOOOO owned \nNOOOOOOOOOOO \nlmao \*bruh\nmoment\* ez clap"
#text = "Going bold now \*\n there is no end bold specifier so this should be bold \n and this should too\*\*"

#text = draw.break_text(text, ImageDraw.Draw(bckgrd), font_used, size[0])

(txtX, txtY) = (0, 2 * TLy + pfp.size[1])
#draw text
draw.render_text(text, bckgrd, ImageDraw.Draw(bckgrd), font_used, (txtX, txtY) )


#show image
bckgrd.show()
bckgrd.save('test.png', 'PNG')
