import sqlite3, json, sys, math
from pathlib import Path

DB = Path('automobilbranche_nrw.db')
OUT = Path('public/unternehmen.geojson')

def export():
    with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('''SELECT l.*, c.name, c.website, c.description, s.name_de AS size
        FROM location l JOIN company c USING(company_id)
        LEFT JOIN company_size s USING(size_id) ORDER BY l.location_id''').fetchall()
        features = []
        for r in rows:
            lat, lon = r['latitude'], r['longitude']
            if lat is None or lon is None or not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                print(f"Standort {r['location_id']} übersprungen: fehlende/ungültige Koordinaten")
                continue
            props = {k:r[k] for k in ('company_id','location_id','name','website','description','size','city','postal_code','address_line_1','address_line_2','state_province_region','country_code')}
            for key, table, lookup, col in [('roles','company_role','supply_chain_role','role_id'),('categories','company_category','main_category','maincategory_id'),('subcategories','company_subcategory','subcategory','subcategory_id')]:
                props[key] = ', '.join(x[0] for x in db.execute(f'SELECT t.name_de FROM {table} j JOIN {lookup} t USING({col}) WHERE j.company_id=? ORDER BY t.{col}',(r['company_id'],)))
            features.append({'type':'Feature','id':r['location_id'],'geometry':{'type':'Point','coordinates':[lon,lat]},'properties':props})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'{len(features)} von {len(rows)} Standorten exportiert')

if __name__=='__main__': export()
