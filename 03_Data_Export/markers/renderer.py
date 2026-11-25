import math
from PIL import Image, ImageDraw
from .colors import category_color
from .pictograms import pictogram

_generated = set()

def marker_url(category_ids, output_dir, base_url):
    keys = sorted(set(category_ids)) or [0]
    filename = 'v2_' + '_'.join(map(str, keys)) + '.png'
    path = output_dir / 'icons' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path in _generated and path.exists():
        return f'{base_url}/icons/{filename}'
    # Supersampling for smooth edges, transparent background.
    img = Image.new('RGBA', (192, 192), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bounds = (8, 8, 183, 183)
    if len(keys) == 1:
        draw.ellipse(bounds, fill=category_color(keys[0]))
    else:
        for i, key in enumerate(keys):
            draw.pieslice(bounds, -90 + i * 360 / len(keys),
                          -90 + (i + 1) * 360 / len(keys),
                          fill=category_color(key))
        for i in range(len(keys)):
            a = math.radians(-90 + i * 360 / len(keys))
            draw.line((95.5, 95.5, 95.5 + 87 * math.cos(a),
                       95.5 + 87 * math.sin(a)), fill='white', width=3)
    # A single pictogram is large; multiple pictograms would be unreadable
    # at uMap's normal marker size, so keep the sectors clear.
    if len(keys) == 1:
        symbol = pictogram(keys[0]).resize((112,112), Image.Resampling.LANCZOS)
        img.alpha_composite(symbol, (40,40))
    draw.ellipse(bounds, outline='white', width=5)
    img.resize((64, 64), Image.Resampling.LANCZOS).save(path)
    _generated.add(path)
    return f'{base_url}/icons/{filename}'



