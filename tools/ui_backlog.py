"""Keep the current dialogue from showing through the backlog reading area."""
from PIL import Image


def render_backlog(source, destination):
    with Image.open(source) as original:
        if original.mode != "RGBA" or original.size != (2048, 2334):
            raise ValueError("Unexpected backlog atlas")
        atlas = original.copy()
    # The first 1920x1080 sprite is the history panel. Its parchment has
    # alpha 166. The speaker plate starts around y=734 on this canvas.
    box = (128, 656, 1626, 1080)
    parchment = atlas.getchannel("A").crop(box)
    opaque = parchment.point(lambda a: min(255, round(a * 255 / 166)))
    ramp = Image.new("L", (1, parchment.height))
    ramp.putdata([min(255, round(y * 255 / 64)) for y in range(parchment.height)])
    alpha = atlas.getchannel("A")
    alpha.paste(Image.composite(opaque, parchment, ramp.resize(parchment.size)), box)
    atlas.putalpha(alpha)
    atlas.save(destination)
