
import sqlite3
import json
import math
from pathlib import Path

# Dateipfade
DB = Path('automobilbranche_nrw.db')
OUT = Path('public/unternehmen.geojson')

# Farben der Hauptkategorien
CATEGORY_COLORS = {
    1: '#2563eb',  # Fahrzeugherstellung
    2: '#16a34a',  # Antriebs- und Energiesysteme
    3: '#ea580c',  # Fahrwerk, Karosserie und Innenraum
    4: '#9333ea',  # Elektronik und Software
    5: '#64748b',  # Maschinen- und Anlagenbau
    6: '#a16207',  # Mechanische Komponenten
    7: '#0891b2',  # Entwicklung und Prüfung
    8: '#dc2626',  # Motorsport
    9: '#db2777',  # Forschung und Innovation
}

DEFAULT_COLOR = '#9ca3af'


def get_classifications(db, company_id, table, lookup, col):
    return db.execute(
        f'''
        SELECT t.{col}, t.name_de
        FROM {table} j
        JOIN {lookup} t USING({col})
        WHERE j.company_id = ?
        ORDER BY t.{col}
        ''',
        (company_id,)
    ).fetchall()


def filter_values(rows):
    # uMap trennt Mehrfachwerte anhand von Kommas.
    # Kommas innerhalb eines Kategorienamens ersetzen.
    return ','.join(
        row[1].replace(',', ' /')
        for row in rows
    ) or 'Unbekannt'


def export():

    if not DB.is_file():
        raise FileNotFoundError(
            f'Datenbank nicht gefunden: {DB}'
        )

    with sqlite3.connect(
        DB.resolve().as_uri() + '?mode=ro',
        uri=True
    ) as db:

        db.row_factory = sqlite3.Row

        rows = db.execute('''
            SELECT l.*, c.name, c.website,
                   c.description, s.name_de AS size
            FROM location l
            JOIN company c USING(company_id)
            LEFT JOIN company_size s USING(size_id)
            ORDER BY l.location_id
        ''').fetchall()

        features = []

        for r in rows:

            lat, lon = r['latitude'], r['longitude']

            # Koordinaten überprüfen
            if (
                lat is None or lon is None
                or not isinstance(lat, (int, float))
                or not isinstance(lon, (int, float))
                or not math.isfinite(lat)
                or not math.isfinite(lon)
                or not -90 <= lat <= 90
                or not -180 <= lon <= 180
            ):
                print(
                    f"Standort {r['location_id']} "
                    "übersprungen: ungültige Koordinaten"
                )
                continue

            # Bestehende Unternehmensattribute
            props = {
                k: r[k] for k in (
                    'company_id',
                    'location_id',
                    'name',
                    'website',
                    'description',
                    'size',
                    'city',
                    'postal_code',
                    'address_line_1',
                    'address_line_2',
                    'state_province_region',
                    'country_code'
                )
            }

            props['size'] = props['size'] or 'Unbekannt'

            # Lieferkettenrollen
            roles = get_classifications(
                db, r['company_id'],
                'company_role',
                'supply_chain_role',
                'role_id'
            )

            # Hauptkategorien
            categories = get_classifications(
                db, r['company_id'],
                'company_category',
                'main_category',
                'maincategory_id'
            )

            # Unterkategorien
            subcategories = get_classifications(
                db, r['company_id'],
                'company_subcategory',
                'subcategory',
                'subcategory_id'
            )

            # Lesbare Texte für Pop-ups
            props['roles'] = '; '.join(
                x[1] for x in roles
            ) or 'Unbekannt'

            props['categories'] = '; '.join(
                x[1] for x in categories
            ) or 'Nicht klassifiziert'

            props['subcategories'] = '; '.join(
                x[1] for x in subcategories
            ) or 'Keine Zuordnung'

            # Separate Felder für uMap-Filter
            props['roles_filter'] = filter_values(roles)

            props['categories_filter'] = filter_values(
                categories
            )

            props['subcategories_filter'] = filter_values(
                subcategories
            )

            # IDs der Klassifikationen
            props['role_ids'] = ','.join(
                str(x[0]) for x in roles
            )

            props['category_ids'] = ','.join(
                str(x[0]) for x in categories
            )

            props['subcategory_ids'] = ','.join(
                str(x[0]) for x in subcategories
            )

            # Erste Hauptkategorie für Markerfarbe
            primary_id = (
                categories[0][0] if categories else 0
            )

            primary_name = (
                categories[0][1]
                if categories
                else 'Nicht klassifiziert'
            )

            props['primary_category_id'] = primary_id
            props['primary_category'] = primary_name

            color = CATEGORY_COLORS.get(
                primary_id, DEFAULT_COLOR
            )

            props['color'] = color

            # Native uMap-Darstellungsoptionen
            props['_umap_options'] = {
                'color': color
            }

            # Vollständige Standortadresse
            street = ' '.join(
                str(v) for v in (
                    r['address_line_1'],
                    r['address_line_2']
                ) if v
            )

            city = ' '.join(
                str(v) for v in (
                    r['postal_code'],
                    r['city']
                ) if v
            )

            props['address'] = ', '.join(
                str(v) for v in (
                    street,
                    city,
                    r['state_province_region'],
                    r['country_code']
                ) if v
            )

            # GeoJSON-Standort erzeugen
            features.append({
                'type': 'Feature',
                'id': r['location_id'],
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                },
                'properties': props
            })

    # GeoJSON-Datei speichern
    OUT.parent.mkdir(parents=True, exist_ok=True)

    OUT.write_text(
        json.dumps(
            {
                'type': 'FeatureCollection',
                'features': features
            },
            ensure_ascii=False,
            indent=2,
            allow_nan=False
        ) + '\n',
        encoding='utf-8'
    )

    print(
        f'{len(features)} von {len(rows)} '
        'Standorten exportiert'
    )


if __name__ == '__main__':
    export()
