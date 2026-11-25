import sqlite3
import json
import math
from pathlib import Path
from copy import deepcopy

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
        rows = db.execute('''SELECT l.*, c.name, c.website, c.description, s.name_de AS size
            FROM location l JOIN company c USING(company_id)
            LEFT JOIN company_size s USING(size_id) ORDER BY l.location_id''').fetchall()
        for r in rows:
            lat, lon = r['latitude'], r['longitude']
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                print(f"Standort {r['location_id']} übersprungen: ungültige Koordinaten")
                continue
            cid = r['company_id']
            roles = classifications(db, cid, 'company_role', 'supply_chain_role', 'role_id')
            cats = classifications(db, cid, 'company_category', 'main_category', 'maincategory_id')
            subs = classifications(db, cid, 'company_subcategory', 'subcategory', 'subcategory_id')
            props = {k: r[k] for k in ('company_id','location_id','name','website','description','size','city','postal_code','address_line_1','address_line_2','state_province_region','country_code')}
            props['size'] = props['size'] or 'Unbekannt'
            for label, values, key, fallback in [('roles', roles, 'role_id', 'Unbekannt'), ('categories', cats, 'maincategory_id', 'Nicht klassifiziert'), ('subcategories', subs, 'subcategory_id', 'Keine Zuordnung')]:
                props[label] = names(values, fallback)
                props[label + '_filter'] = filter_values(values) or (fallback if label != 'subcategories' else '')
                props[{'roles':'role_ids','categories':'category_ids','subcategories':'subcategory_ids'}[label]] = ids(values, key)
            # Separate Filter pro Hauptkategorie (Variante B).
            # Leere Felder bedeuten: keine Unterkategorie dieser Gruppe.
            for main_id in range(2, 8):
                selected = [s for s in subs if s['maincategory_id'] == main_id]
                props[f'subcategories_{main_id}'] = filter_values(selected)
            street = ' '.join(str(r[k]) for k in ('address_line_1','address_line_2') if r[k])
            city = ' '.join(str(r[k]) for k in ('postal_code','city') if r[k])
            props['address'] = ', '.join(str(v) for v in (street, city, r['state_province_region'], r['country_code']) if v)
            primary = cats[0]['maincategory_id'] if cats else 0
            props['primary_category_id'] = primary
            props['primary_category'] = cats[0]['name_de'] if cats else 'Nicht klassifiziert'
            style(props, primary)
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
                layers[i].append(item)
    write_geojson(OUT, features)
    for i, filename in CATEGORY_FILES.items():
        write_geojson(OUT.parent / 'categories' / (filename + '.geojson'), layers[i])
    write_geojson(OUT.parent / 'categories' / '00_unclassified.geojson', unclassified)
    print(f'{len(features)} von {len(rows)} Standorten exportiert')


if __name__ == '__main__':
    export()
