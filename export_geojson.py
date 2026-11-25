import sqlite3
import json
import math
from pathlib import Path
from copy import deepcopy
from PIL import Image, ImageDraw
import os
import colorsys

DB = Path('automobilbranche_nrw.db')
OUT = Path('public/unternehmen.geojson')
CATEGORY_FILES = {
    1: '01_vehicle_manufacturing', 2: '02_powertrain_energy',
    3: '03_chassis_body_interior', 4: '04_electronics_software',
    5: '05_machinery_automation', 6: '06_components_materials',
    7: '07_engineering_testing', 8: '08_motorsport',
    9: '09_research_innovation',
}
CATEGORY_COLORS = dict(enumerate([
    '#2563eb', '#16a34a', '#ea580c', '#9333ea', '#64748b',
    '#a16207', '#0891b2', '#dc2626', '#db2777'], 1))
DEFAULT_COLOR = '#9ca3af'
BASE_URL = os.environ.get('PAGES_BASE_URL', 'https://ndopiera.github.io/interaktive_karte_automotive_unternehmen_test').rstrip('/')


def pictogram(key):
    # Original, dependency-free line drawings on a 64 x 64 transparent canvas.
    im = Image.new('RGBA', (64, 64))
    d = ImageDraw.Draw(im)
    def line(points, width=5):
        d.line(points, fill='white', width=width, joint='curve')
    def box(b):
        d.rounded_rectangle(b, radius=3, outline='white', width=4)
    def circle(x,y,r):
        d.ellipse((x-r,y-r,x+r,y+r), outline='white', width=4)
    if key == 1:  # Car
        line([(7,39),(7,27),(16,24),(23,12),(43,12),(51,24),(57,27),(57,39),(7,39)])
        line([(17,24),(50,24)],3); circle(17,42,5); circle(47,42,5)
    elif key == 2:  # Lightning
        d.polygon([(35,3),(12,36),(29,36),(25,61),(53,24),(36,24)],fill='white')
    elif key == 3:  # Suspension spring
        line([(20,6),(44,6)]); line([(32,6),(32,13)],3)
        line([(32,13),(18,20),(46,28),(18,36),(46,44),(32,51)])
        line([(32,51),(32,58)],3); line([(20,58),(44,58)])
    elif key == 4:  # Chip
        box((17,17,47,47)); box((25,25,39,39))
        for t in (22,32,42):
            line([(t,7),(t,17)],3); line([(t,47),(t,57)],3)
            line([(7,t),(17,t)],3); line([(47,t),(57,t)],3)
    elif key == 5:  # Robot arm
        line([(9,56),(55,56)]); box((22,44,42,54))
        line([(32,44),(17,28),(38,10),(52,23)],7)
        circle(17,28,5); circle(38,10,5); line([(47,24),(53,30),(59,24)],3)
    elif key == 6:  # Hexagonal nut
        pts=[(32,5),(55,18),(55,46),(32,59),(9,46),(9,18),(32,5)]
        line(pts,5); circle(32,32,12)
    elif key == 7:  # Inspection magnifier
        circle(25,25,17); line([(38,38),(56,56)],7)
        line([(16,25),(23,32),(34,19)],4)
    elif key == 8:  # Checkered flag
        line([(12,58),(12,6)],4); box((13,7,55,39))
        for y in range(3):
            for x in range(4):
                if (x+y)%2==0: d.rectangle((15+x*10,9+y*10,24+x*10,18+y*10),fill='white')
    elif key == 9:  # Laboratory flask
        line([(23,6),(41,6)]); line([(26,6),(26,25),(10,51),(12,57),(52,57),(54,51),(38,25),(38,6)])
        line([(18,40),(46,40)],3); circle(32,47,3)
    else:
        line([(23,19),(27,12),(39,12),(44,21),(32,33),(32,40)]); circle(32,51,2)
    return im


def marker_url(category_ids):
    keys = sorted(set(category_ids)) or [0]
    filename = 'v2_' + '_'.join(map(str, keys)) + '.png'
    path = OUT.parent / 'icons' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return f'{BASE_URL}/icons/{filename}'
    # Supersampling for smooth edges, transparent background.
    img = Image.new('RGBA', (192, 192), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bounds = (8, 8, 183, 183)
    if len(keys) == 1:
        draw.ellipse(bounds, fill=CATEGORY_COLORS.get(keys[0], DEFAULT_COLOR))
    else:
        for i, key in enumerate(keys):
            draw.pieslice(bounds, -90 + i * 360 / len(keys),
                          -90 + (i + 1) * 360 / len(keys),
                          fill=CATEGORY_COLORS.get(key, DEFAULT_COLOR))
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
    return f'{BASE_URL}/icons/{filename}'



def write_geojson(path, features):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'type': 'FeatureCollection', 'features': features},
                               ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(f'{path}: {len(features)} Standorte')


def classifications(db, cid, table, lookup, key):
    return db.execute(f'SELECT t.* FROM {table} j JOIN {lookup} t USING({key}) '
                      f'WHERE j.company_id=? ORDER BY t.{key}', (cid,)).fetchall()


def names(rows, fallback):
    return '; '.join(r['name_de'] for r in rows) or fallback


def filter_values(rows):
    return ','.join(r['name_de'].replace(',', ' /') for r in rows)


def ids(rows, key):
    return ','.join(str(r[key]) for r in rows)


def style(props, category_id):
    color = CATEGORY_COLORS.get(category_id, DEFAULT_COLOR)
    props['color'] = color
    props['_umap_options'] = {'color': color}


def export():
    if not DB.is_file():
        raise FileNotFoundError(f'Datenbank nicht gefunden: {DB}')
    features = []
    layers = {i: [] for i in CATEGORY_FILES}
    unclassified = []
    with sqlite3.connect(DB.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        if 'review_status' not in {r[1] for r in db.execute('PRAGMA table_info(company)')}:
            raise ValueError('Veröffentlichungsdatenbank aus V3 erforderlich.')
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='company_review'").fetchone():
            raise ValueError('Interne Arbeitsdatenbank darf nicht veröffentlicht werden.')
        for cat in db.execute('SELECT maincategory_id FROM main_category'):
            i=cat[0]
            CATEGORY_FILES.setdefault(i,f'{i:02d}_category')
            if i not in CATEGORY_COLORS:
                CATEGORY_COLORS[i]='#'+''.join(f'{round(x*255):02x}' for x in colorsys.hsv_to_rgb((i*.61803398875)%1,.68,.78))
        layers = {i: [] for i in CATEGORY_FILES}
        rows = db.execute('''SELECT l.*, c.name, c.website, c.description, c.review_status, s.name_de AS size
            FROM location l JOIN company c USING(company_id)
            LEFT JOIN company_size s USING(size_id) WHERE c.review_status IN ('APPROVED','TEST') ORDER BY l.location_id''').fetchall()
        for r in rows:
            lat, lon = r['latitude'], r['longitude']
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                print(f"Standort {r['location_id']} übersprungen: ungültige Koordinaten")
                continue
            cid = r['company_id']
            roles = classifications(db, cid, 'company_role', 'supply_chain_role', 'role_id')
            cats = classifications(db, cid, 'company_category', 'main_category', 'maincategory_id')
            subs = classifications(db, cid, 'company_subcategory', 'subcategory', 'subcategory_id')
            props = {k: r[k] for k in ('company_id','location_id','name','website','description','review_status','size','city','postal_code','address_line_1','address_line_2','state_province_region','country_code')}
            props['size'] = props['size'] or 'Unbekannt'
            for label, values, key, fallback in [('roles', roles, 'role_id', 'Unbekannt'), ('categories', cats, 'maincategory_id', 'Nicht klassifiziert'), ('subcategories', subs, 'subcategory_id', 'Keine Zuordnung')]:
                props[label] = names(values, fallback)
                props[label + '_filter'] = filter_values(values) or (fallback if label != 'subcategories' else '')
                props[{'roles':'role_ids','categories':'category_ids','subcategories':'subcategory_ids'}[label]] = ids(values, key)
            # Separate Filter pro Hauptkategorie (Variante B).
            # Leere Felder bedeuten: keine Unterkategorie dieser Gruppe.
            for main_id in CATEGORY_FILES:
                selected = [s for s in subs if s['maincategory_id'] == main_id]
                props[f'subcategories_{main_id}'] = filter_values(selected)
            street = ' '.join(str(r[k]) for k in ('address_line_1','address_line_2') if r[k])
            city = ' '.join(str(r[k]) for k in ('postal_code','city') if r[k])
            props['address'] = ', '.join(str(v) for v in (street, city, r['state_province_region'], r['country_code']) if v)
            primary = cats[0]['maincategory_id'] if cats else 0
            props['primary_category_id'] = primary
            props['primary_category'] = cats[0]['name_de'] if cats else 'Nicht klassifiziert'
            style(props, primary)
            props['icon_url'] = marker_url([c['maincategory_id'] for c in cats])
            # Set per-feature options as well as the reusable URL property.
            props['_umap_options'] = {'color': '#ffffff', 'iconUrl': props['icon_url'], 'iconClass': 'Default'}
            feature = {'type':'Feature','id':r['location_id'],'geometry':{'type':'Point','coordinates':[lon,lat]},'properties':props}
            features.append(feature)
            if not cats:
                unclassified.append(feature)
            for cat in cats:
                i = cat['maincategory_id']
                if i not in layers:
                    print(f'Keine konfigurierte Ebene für Hauptkategorie {i}; Standort bleibt in Gesamtdatei')
                    continue
                item = deepcopy(feature)
                p = item['properties']
                selected = [s for s in subs if s['maincategory_id'] == i]
                p['layer_category_id'] = i
                p['layer_category'] = cat['name_de']
                p['subcategories_all'] = props['subcategories']
                p['subcategories'] = names(selected, 'Keine Zuordnung')
                p['subcategories_filter'] = filter_values(selected)
                p['subcategory_ids'] = ids(selected, 'subcategory_id')
                style(p, i)
                p['icon_url'] = marker_url([i])
                p['_umap_options'] = {'color': '#ffffff', 'iconUrl': p['icon_url'], 'iconClass': 'Default'}
                layers[i].append(item)
    write_geojson(OUT, features)
    for i, filename in CATEGORY_FILES.items():
        write_geojson(OUT.parent / 'categories' / (filename + '.geojson'), layers[i])
    write_geojson(OUT.parent / 'categories' / '00_unclassified.geojson', unclassified)
    print(f'{len(features)} von {len(rows)} Standorten exportiert')


if __name__ == '__main__':
    export()
