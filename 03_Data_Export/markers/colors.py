import colorsys

CATEGORY_COLORS = dict(enumerate([
    '#2563eb', '#16a34a', '#ea580c', '#9333ea', '#64748b',
    '#a16207', '#0891b2', '#dc2626', '#db2777'], 1))
DEFAULT_COLOR = '#9ca3af'

def category_color(category_id):
    if category_id == 0:
        return DEFAULT_COLOR
    return CATEGORY_COLORS.setdefault(category_id, '#'+''.join(f'{round(x*255):02x}' for x in colorsys.hsv_to_rgb((category_id*.61803398875)%1,.68,.78)))
