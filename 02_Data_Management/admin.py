import sqlite3, datetime, tempfile, pathlib, base64, json, urllib.request, urllib.error, urllib.parse, re
from contextlib import closing

STATUS={'DRAFT':'Entwurf','PENDING':'Zur Prüfung','REVISION':'Überarbeitung erforderlich','APPROVED':'Freigegeben','REJECTED':'Abgelehnt','TEST':'Testfreigabe'}
TABLES=['country','company_size','supply_chain_role','main_category','subcategory','company','location','source','company_role','company_category','company_subcategory']
CHECKS=['Unternehmensname und Website','Automobilbezug','Standorte und Adressen','Koordinaten','Unternehmensgröße','Lieferkettenrollen','Hauptkategorien','Unterkategorien','Quellen und Nachvollziehbarkeit']
def migrate(c):
    cols={r[1] for r in c.execute('PRAGMA table_info(company)')}
    with c:
        if 'review_status' not in cols:
            c.execute("ALTER TABLE company ADD COLUMN review_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(review_status IN ('DRAFT','PENDING','REVISION','APPROVED','REJECTED','TEST'))")
            c.execute("UPDATE company SET review_status='TEST'")
        if 'data_origin' not in cols:
            c.execute("ALTER TABLE company ADD COLUMN data_origin TEXT NOT NULL DEFAULT 'Unknown' CHECK(data_origin IN ('AI','Manual','Hybrid','Unknown'))")
        c.execute('''CREATE TABLE IF NOT EXISTS company_review(review_id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES company(company_id), status TEXT NOT NULL, reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL, notes TEXT, checklist TEXT, duration_seconds INTEGER)''')
        c.execute('''CREATE TRIGGER IF NOT EXISTS review_company_edit AFTER UPDATE OF name,website,description,size_id,data_origin ON company BEGIN UPDATE company SET review_status='PENDING' WHERE company_id=NEW.company_id AND review_status IN ('APPROVED','TEST'); END''')
        for t in ['location','source','company_role','company_category','company_subcategory']:
            for op,ref in [('INSERT','NEW'),('UPDATE','NEW'),('DELETE','OLD')]:
                extra=" OR company_id=OLD.company_id" if op=='UPDATE' else ''
                c.execute(f"CREATE TRIGGER IF NOT EXISTS review_{t}_{op} AFTER {op} ON {t} BEGIN UPDATE company SET review_status='PENDING' WHERE (company_id={ref}.company_id{extra}) AND review_status IN ('APPROVED','TEST'); END")
        for t,query in [('country','SELECT company_id FROM location WHERE country_code=OLD.country_code'),('company_size','SELECT company_id FROM company WHERE size_id=OLD.size_id'),('supply_chain_role','SELECT company_id FROM company_role WHERE role_id=OLD.role_id'),('main_category','SELECT company_id FROM company_category WHERE maincategory_id=OLD.maincategory_id'),('subcategory','SELECT company_id FROM company_subcategory WHERE subcategory_id=OLD.subcategory_id')]:
            c.execute(f"CREATE TRIGGER IF NOT EXISTS review_lookup_{t} AFTER UPDATE ON {t} BEGIN UPDATE company SET review_status='PENDING' WHERE company_id IN ({query}) AND review_status IN ('APPROVED','TEST'); END")

def review(c,cid,status,reviewer,notes,checks,duration):
    if status not in STATUS or not reviewer.strip(): raise ValueError('Status und Prüfer erforderlich.')
    if status=='APPROVED':
        if len(checks)!=len(CHECKS) or any(x not in ('Geprüft','Nicht zutreffend / begründet') for x in checks): raise ValueError('Alle Prüfpunkte bearbeiten.')
        if 'Nicht zutreffend / begründet' in checks and not notes.strip(): raise ValueError('Ausnahmen begründen.')
        if not c.execute('SELECT 1 FROM location WHERE company_id=? AND latitude IS NOT NULL AND longitude IS NOT NULL',(cid,)).fetchone(): raise ValueError('Mindestens ein kartierbarer Standort erforderlich.')
        if not c.execute('SELECT 1 FROM source WHERE company_id=?',(cid,)).fetchone(): raise ValueError('Mindestens eine Quelle erforderlich.')
        if not c.execute('SELECT 1 FROM company_category WHERE company_id=?',(cid,)).fetchone(): raise ValueError('Mindestens eine Hauptkategorie erforderlich.')
    if status in ('REVISION','REJECTED') and not notes.strip(): raise ValueError('Begründung erforderlich.')
    with c:
        c.execute('UPDATE company SET review_status=? WHERE company_id=?',(status,cid))
        c.execute('INSERT INTO company_review(company_id,status,reviewer,reviewed_at,notes,checklist,duration_seconds) VALUES (?,?,?,?,?,?,?)',(cid,status,reviewer.strip(),datetime.datetime.now(datetime.timezone.utc).isoformat(),notes,json.dumps(dict(zip(CHECKS,checks)),ensure_ascii=False),duration))

def snapshot(c, include_test=False):
    # Rebuild a fresh database; no deleted pages or private review history copied.
    with tempfile.TemporaryDirectory() as d:
        p=pathlib.Path(d)/'public.db'
        with closing(sqlite3.connect(p)) as out:
            out.execute('PRAGMA foreign_keys=ON')
            c.execute('BEGIN')
            try:
                with out:
                    for t in TABLES:
                        sql=c.execute('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?',(t,)).fetchone()[0]
                        out.execute(sql)
                        cols=[r[1] for r in c.execute(f'PRAGMA table_info({t})')]
                        where=''; args=()
                        if 'company_id' in cols:
                            where=" WHERE company_id IN (SELECT company_id FROM company WHERE review_status IN ("+('?,?' if include_test else '?')+'))'
                            args=('APPROVED','TEST') if include_test else ('APPROVED',)
                        data=c.execute(f'SELECT * FROM {t}'+where,args).fetchall()
                        # Internal source notes and data provenance are not published.
                        data=[tuple(None if t=='source' and col=='notes' else 'Unknown' if t=='company' and col=='data_origin' else row[i] for i,col in enumerate(cols)) for row in data]
                        out.executemany(f'INSERT INTO {t} VALUES ({",".join("?" for _ in cols)})',data)
                    if out.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Fremdschlüsselprüfung fehlgeschlagen.')
            finally: c.rollback()
        return p.read_bytes()

def api(repo,token,endpoint,method='GET',payload=None):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo): raise ValueError('Repository als owner/name eingeben.')
    req=urllib.request.Request('https://api.github.com/repos/'+repo+endpoint,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json','User-Agent':'Automotive-NRW'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            b=r.read(); return json.loads(b) if b else {}
    except urllib.error.HTTPError as e: raise ValueError(f'GitHub HTTP {e.code}: {e.reason}') from None
    except urllib.error.URLError as e: raise ValueError(f'GitHub-Verbindung fehlgeschlagen: {e.reason}') from None

def upload(repo,token,branch,data):
    endpoint='/contents/01_Database/companies_automotive_industry.db'; payload={'message':'Freigegebene Unternehmensdaten aktualisieren','content':base64.b64encode(data).decode(),'branch':branch}
    try: payload['sha']=api(repo,token,endpoint+'?ref='+urllib.parse.quote(branch,safe=''))['sha']
    except ValueError as e:
        if 'HTTP 404' not in str(e): raise
    return api(repo,token,endpoint,'PUT',payload)
