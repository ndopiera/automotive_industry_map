from pathlib import Path
import sqlite3
from datetime import date
import streamlit as st
import admin
from contextlib import closing
import os

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Automotive NRW', layout='wide')
st.title('Automotive NRW – Unternehmensdatenbank')

def connect(path):
    con = sqlite3.connect(path, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

path = Path(st.sidebar.text_input('Pfad zur SQLite-Datenbank', str(ROOT.parent / '01_Database' / 'automobilbranche_nrw_work.db'))).expanduser()
if not path.is_file():
    st.warning('Datenbank nicht gefunden. Wähle den Pfad deiner bestehenden Datenbank oder erstelle eine neue leere Datenbank.')
    if st.button('Neue Datenbank an diesem Pfad erstellen'):
        try:
            with connect(path) as c: c.executescript((ROOT.parent/'01_Database'/'schema.sql').read_text(encoding='utf-8'))
            st.rerun()
        except (sqlite3.Error, OSError) as e: st.error(str(e))
    st.stop()

def rows(sql, args=()):
    c=connect(path)
    try: return [dict(r) for r in c.execute(sql,args)]
    finally: c.close()

def write(sql, args=()):
    c=connect(path)
    try:
        with c: cur=c.execute(sql,args)
        return cur.lastrowid
    finally: c.close()

def run(fn, message):
    try:
        fn()
        st.session_state['notice']=message
        st.rerun()
    except (sqlite3.Error, ValueError) as e: st.error(str(e))

def clean(s): return s.strip() or None

def required(s, name):
    if not s.strip(): raise ValueError(f'{name} ist erforderlich.')
    return s.strip()

def coordinates(a,b):
    if not a.strip() and not b.strip(): return None,None
    try: x,y=float(a.replace(',','.')),float(b.replace(',','.'))
    except ValueError: raise ValueError('Beide Koordinaten als Dezimalzahl eingeben.')
    if not (-90<=x<=90 and -180<=y<=180): raise ValueError('Koordinaten außerhalb des gültigen Bereichs.')
    return x,y

try:
    with closing(connect(path)) as c:
        if 'review_status' not in {r[1] for r in c.execute('PRAGMA table_info(company)')}:
            target=path.with_name(path.stem+'_vor_v3.db')
            if not target.exists():
                with closing(sqlite3.connect(target)) as backup: c.backup(backup)
        admin.migrate(c)
    sizes={r['size_id']:r['name_de'] for r in rows('SELECT * FROM company_size ORDER BY size_id')}
    countries={r['country_code']:r['name_de'] for r in rows('SELECT * FROM country ORDER BY name_de')}
    companies=rows('SELECT * FROM company ORDER BY name')
except sqlite3.Error as e:
    st.error(f'Datenbankstruktur nicht lesbar: {e}'); st.stop()
if 'notice' in st.session_state: st.success(st.session_state.pop('notice'))
if st.sidebar.button('Sicherungskopie erstellen'):
    try:
        from datetime import datetime
        target=path.with_name(path.stem+'_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
        a,b=connect(path),sqlite3.connect(target)
        try: a.backup(b)
        finally: a.close(); b.close()
        st.sidebar.success(str(target))
    except sqlite3.Error as e: st.sidebar.error(str(e))

mode=st.sidebar.radio('Bereich',['Übersicht','Unternehmen bearbeiten','Unternehmen anlegen','Kategorien & Stammlisten','Qualitätsprüfung','Veröffentlichung'])
if mode=='Kategorien & Stammlisten':
    st.header('Kategorien und Stammlisten verwalten')
    config={'Hauptkategorien':('main_category','maincategory_id'),'Unterkategorien':('subcategory','subcategory_id'),'Lieferkettenrollen':('supply_chain_role','role_id'),'Unternehmensgrößen':('company_size','size_id'),'Länder':('country','country_code')}
    label=st.selectbox('Liste',list(config)); table,pk=config[label]
    entries={r[pk]:r for r in rows(f'SELECT * FROM {table} ORDER BY {pk}')}
    st.dataframe(list(entries.values()),hide_index=True)
    ident=st.selectbox('Eintrag',[None]+list(entries),format_func=lambda x:'Neu anlegen' if x is None else f'{x} – {entries[x]["name_de"]}')
    old=entries.get(ident,{})
    with st.form(f'lookup_{table}_{ident}'):
        de=st.text_input('Bezeichnung DE',old.get('name_de','')); en=st.text_input('Bezeichnung EN',old.get('name_en',''))
        fields={'name_de':de,'name_en':en}
        if table=='country': fields[pk]=st.text_input('ISO-Ländercode (2 Zeichen)',old.get(pk,''),disabled=ident is not None).strip().upper()
        if table in ('company_size','supply_chain_role'):
            code='size_code' if table=='company_size' else 'role_code'; fields[code]=st.text_input('Eindeutiger Code',old.get(code,''))
        if table=='subcategory':
            parents={r['maincategory_id']:r['name_de'] for r in rows('SELECT * FROM main_category ORDER BY maincategory_id')}
            fields['maincategory_id']=st.selectbox('Hauptkategorie',list(parents),index=list(parents).index(old['maincategory_id']) if old else 0,format_func=parents.get)
        if table=='company_size':
            for f in ('employees_minimum','employees_maximum'):
                fields[f]=st.text_input(f, str(old[f]) if old.get(f) is not None else '')
        def save_lookup():
            vals=dict(fields); required(de,'Deutsch'); required(en,'Englisch')
            if table=='company_size':
                for f in ('employees_minimum','employees_maximum'): vals[f]=int(vals[f]) if vals[f].strip() else None
                lo,hi=vals['employees_minimum'],vals['employees_maximum']
                if (lo is not None and lo<0) or (hi is not None and (hi<0 or lo is None or hi<lo)): raise ValueError('Ungültige Mitarbeitergrenzen.')
            if table=='subcategory' and ident is not None and vals['maincategory_id']!=old['maincategory_id'] and rows('SELECT 1 FROM company_subcategory WHERE subcategory_id=?',(ident,)): raise ValueError('Verwendete Unterkategorie nicht verschieben; zuerst Zuordnungen ändern.')
            if table=='country' and not __import__('re').fullmatch('[A-Z]{2}',vals[pk]): raise ValueError('Zwei Buchstaben erforderlich.')
            if ident is None:
                if pk!='country_code': vals[pk]=max(entries,default=0)+1
                write(f'INSERT INTO {table} ({",".join(vals)}) VALUES ({",".join("?" for _ in vals)})',tuple(vals.values()))
            else:
                vals.pop(pk,None); write(f'UPDATE {table} SET '+','.join(f'{k}=?' for k in vals)+f' WHERE {pk}=?',tuple(vals.values())+(ident,))
        if st.form_submit_button('Eintrag speichern'): run(save_lookup,'Stammliste gespeichert.')
    if ident is not None:
        st.caption('Verwendete Einträge können aufgrund der Fremdschlüssel nicht gelöscht werden. Bestehende IDs bleiben unverändert.')
        confirm=st.checkbox('Eintrag endgültig löschen',key=f'del_{table}_{ident}')
        if st.button('Eintrag löschen',disabled=not confirm):
            if (table=='company_size' and ident==5) or (table=='country' and ident=='DE'): st.error('Standardwert darf nicht gelöscht werden.')
            else: run(lambda:write(f'DELETE FROM {table} WHERE {pk}=?',(ident,)),'Eintrag gelöscht.')
    st.stop()
if mode=='Qualitätsprüfung':
    st.header('Qualitätsprüfung und Freigabe')
    statuses=st.multiselect('Status',list(admin.STATUS),default=['DRAFT','PENDING','REVISION','TEST'],format_func=admin.STATUS.get)
    candidates={r['company_id']:r for r in companies if r['review_status'] in statuses}
    if not candidates: st.info('Keine passenden Unternehmen.'); st.stop()
    cid=st.selectbox('Unternehmen',list(candidates),format_func=lambda i:f"{candidates[i]['name']} – {admin.STATUS[candidates[i]['review_status']]}")
    st.json(candidates[cid],expanded=False)
    for label,q in [('Standorte','SELECT * FROM location WHERE company_id=?'),('Quellen','SELECT * FROM source WHERE company_id=?'),('Lieferkettenrollen','SELECT t.name_de,j.source_id FROM company_role j JOIN supply_chain_role t USING(role_id) WHERE company_id=?'),('Hauptkategorien','SELECT t.name_de,j.source_id FROM company_category j JOIN main_category t USING(maincategory_id) WHERE company_id=?'),('Unterkategorien','SELECT t.name_de,j.source_id FROM company_subcategory j JOIN subcategory t USING(subcategory_id) WHERE company_id=?')]:
        st.subheader(label); st.dataframe(rows(q,(cid,)),hide_index=True)
    with st.form(f'review_{cid}'):
        reviewer=st.text_input('Prüfende Person / Kürzel'); notes=st.text_area('Prüfanmerkungen / Begründung')
        checks=[st.selectbox(x,['Offen','Geprüft','Nicht zutreffend / begründet','Fehler'],key=f'check_{cid}_{i}') for i,x in enumerate(admin.CHECKS)]
        duration=st.number_input('Prüfdauer in Sekunden (0 = nicht erfasst)',min_value=0,step=1)
        status=st.selectbox('Entscheidung',['APPROVED','REVISION','REJECTED','PENDING','TEST'],format_func=admin.STATUS.get)
        def save_review():
            with closing(connect(path)) as c: admin.review(c,cid,status,reviewer,notes,checks,int(duration) or None)
        if st.form_submit_button('Prüfentscheidung speichern'): run(save_review,'Prüfung gespeichert.')
    st.subheader('Prüfhistorie'); st.dataframe(rows('SELECT * FROM company_review WHERE company_id=? ORDER BY review_id DESC',(cid,)),hide_index=True)
    st.stop()
if mode=='Veröffentlichung':
    st.header('Karte veröffentlichen')
    st.warning('Nur die frisch erzeugte Veröffentlichungsdatenbank hochladen. Arbeitsdatenbank und Prüfhistorie bleiben lokal. Bereits öffentlich hochgeladene Daten bleiben ggf. in der Git-Historie.')
    include=st.checkbox('Testfreigaben einschließen (öffentlicher Testbetrieb)',value=False)
    allowed=['APPROVED','TEST'] if include else ['APPROVED']; count=sum(r['review_status'] in allowed for r in companies)
    st.metric('Zur Veröffentlichung ausgewählte Unternehmen',count)
    if not count: st.warning('Der Export wäre leer. Freigaben prüfen oder Testbetrieb auswählen.')
    if st.button('Veröffentlichungsdatenbank erzeugen'):
        try:
            with closing(connect(path)) as c: st.session_state['public_bytes']=admin.snapshot(c,include)
            st.session_state['public_scope']=(str(path.resolve()),include)
        except (sqlite3.Error,ValueError) as e: st.error(str(e))
    if st.session_state.get('public_scope')==(str(path.resolve()),include):
        st.download_button('Erzeugten Stand herunterladen',st.session_state['public_bytes'],'automobilbranche_nrw_public.db')
        st.caption('Download ist der zuletzt erzeugte Stand; nach Änderungen erneut erzeugen. GitHub-Upload erzeugt immer einen neuen Stand.')
    repo=st.text_input('GitHub Repository','ndopiera/unternehmenskarte_automobilbranche'); branch=st.text_input('Branch','main'); workflow=st.text_input('Workflow-Datei','deploy.yml')
    token=st.text_input('GitHub Token (nur Sitzung)',type='password',value=os.environ.get('GITHUB_TOKEN',''))
    confirm=st.checkbox('Öffentlichen Upload bestätigen; Testdaten ggf. ausdrücklich eingeschlossen')
    if st.button('Karte aktualisieren (Datenbank hochladen)',disabled=not(token and confirm)):
        try:
            with closing(connect(path)) as c: data=admin.snapshot(c,include)
            result=admin.upload(repo,token,branch,data); st.success('Commit erstellt: '+result.get('commit',{}).get('sha','')); st.info('Push startet den konfigurierten Workflow. Status unten prüfen.')
        except (ValueError,sqlite3.Error) as e: st.error(str(e))
    if st.button('Nur GitHub Action starten',disabled=not(token and confirm)):
        try: admin.api(repo,token,'/actions/workflows/'+__import__('urllib.parse',fromlist=['quote']).quote(workflow,safe='')+'/dispatches','POST',{'ref':branch}); st.success('Workflow angefordert (bereits hochgeladene Daten).')
        except ValueError as e: st.error(str(e))
    if st.button('Workflow-Status abrufen',disabled=not token):
        try:
            result=admin.api(repo,token,'/actions/workflows/'+__import__('urllib.parse',fromlist=['quote']).quote(workflow,safe='')+'/runs?per_page=10'); st.dataframe([{k:r.get(k) for k in ('name','status','conclusion','created_at','html_url')} for r in result.get('workflow_runs',[])])
        except ValueError as e: st.error(str(e))
    st.stop()
if mode=='Übersicht':
    st.dataframe(companies, hide_index=True, use_container_width=True)
    st.download_button('Unternehmensübersicht als CSV', __import__('pandas').DataFrame(companies).to_csv(index=False).encode('utf-8-sig'), 'unternehmen.csv')
    st.stop()
def save_new_company(name, website, desc, size, locations, sources, selections):
    c=connect(path)
    try:
        with c:
            name=required(name,'Unternehmensname')
            if any(r['name'].casefold()==name.casefold() for r in c.execute('SELECT name FROM company')):
                raise ValueError('Ein Unternehmen mit diesem Namen existiert bereits.')
            cid=c.execute('INSERT INTO company(name,website,description,size_id) VALUES (?,?,?,?)',(name,clean(website),clean(desc),size)).lastrowid
            lids=[]
            for country,region,city,postal,addr,addr2,lat,lon in locations:
                lids.append(c.execute('INSERT INTO location(company_id,country_code,state_province_region,city,postal_code,address_line_1,address_line_2,latitude,longitude) VALUES (?,?,?,?,?,?,?,?,?)',(cid,country,clean(region),required(city,'Stadt'),clean(postal),clean(addr),clean(addr2),*coordinates(lat,lon))).lastrowid)
            sids=[]
            for url,title,typ,accessed,notes,loc in sources:
                if accessed.strip(): date.fromisoformat(accessed.strip())
                sids.append(c.execute('INSERT INTO source(company_id,url,title,source_type,accessed_at,notes,location_id) VALUES (?,?,?,?,?,?,?)',(cid,required(url,'Quellen-URL'),clean(title),clean(typ),clean(accessed),clean(notes),None if loc is None else lids[loc])).lastrowid)
            for j,k,m in selections:
                c.executemany(f'INSERT INTO {j}(company_id,{k},source_id) VALUES (?,?,?)',[(cid,i,None if s is None else sids[s]) for i,s in m.items()])
    finally: c.close()

if mode=='Unternehmen anlegen':
    st.header('Neues Unternehmen vollständig erfassen')
    st.caption('Alle Angaben werden gemeinsam gespeichert. Standorte, Quellen und Klassifikationen sind optional.')
    # Separate widget namespace after each successful save.
    prefix=f"new_{st.session_state.get('new_generation',0)}_"
    def key(s): return prefix+s
    st.subheader('1. Unternehmensdaten')
    name=st.text_input('Unternehmensname *',key=key('name'))
    website=st.text_input('Website',key=key('website'))
    desc=st.text_area('Beschreibung',key=key('desc'))
    size=st.selectbox('Unternehmensgröße',list(sizes),index=list(sizes).index(5) if 5 in sizes else 0,format_func=sizes.get,key=key('size'))
    st.subheader('2. Standorte')
    nloc=int(st.number_input('Anzahl der Standorte',min_value=0,value=1,step=1,key=key('nloc')))
    new_locations=[]
    for i in range(nloc):
        with st.expander(f'Standort {i+1}',expanded=True):
            p=f'loc{i}_'
            a,b=st.columns(2)
            country=a.selectbox('Land',list(countries),index=list(countries).index('DE') if 'DE' in countries else 0,format_func=countries.get,key=key(p+'country'))
            region=b.text_input('Bundesland / Region','Nordrhein-Westfalen',key=key(p+'region'))
            city=a.text_input('Stadt *',key=key(p+'city')); postal=b.text_input('Postleitzahl',key=key(p+'postal'))
            addr=a.text_input('Straße und Hausnummer',key=key(p+'addr')); addr2=b.text_input('Adresszusatz',key=key(p+'addr2'))
            lat=a.text_input('Breitengrad',key=key(p+'lat')); lon=b.text_input('Längengrad',key=key(p+'lon'))
            new_locations.append((country,region,city,postal,addr,addr2,lat,lon))
    st.subheader('3. Quellen')
    nsrc=int(st.number_input('Anzahl der Quellen',min_value=0,value=0,step=1,key=key('nsrc')))
    new_sources=[]
    for i in range(nsrc):
        with st.expander(f'Quelle {i+1}',expanded=True):
            p=f'src{i}_'
            url=st.text_input('URL *',key=key(p+'url')); title=st.text_input('Titel',key=key(p+'title'))
            a,b=st.columns(2)
            typ=a.text_input('Quellentyp','Unternehmenswebsite',key=key(p+'type'))
            accessed=b.text_input('Abrufdatum (JJJJ-MM-TT)',date.today().isoformat(),key=key(p+'date'))
            notes=st.text_area('Notizen',key=key(p+'notes'))
            loc=st.selectbox('Standortbezug',[None]+list(range(nloc)),format_func=lambda x:'Gesamtes Unternehmen' if x is None else f'Standort {x+1}: {new_locations[x][2]}',key=key(p+'loc'))
            new_sources.append((url,title,typ,accessed,notes,loc))
    st.subheader('4. Klassifikationen')
    selections=[]; parents=[]
    for label,table,junction,k in [('Lieferkettenrollen','supply_chain_role','company_role','role_id'),('Hauptkategorien','main_category','company_category','maincategory_id'),('Unterkategorien','subcategory','company_subcategory','subcategory_id')]:
        entries=rows(f'SELECT * FROM {table} ORDER BY {k}')
        names={r[k]:r['name_de'] for r in entries if table!='subcategory' or r['maincategory_id'] in parents}
        widget=key(k)
        if widget in st.session_state:
            st.session_state[widget]=[i for i in st.session_state[widget] if i in names]
        chosen=st.multiselect(label,list(names),format_func=names.get,key=widget)
        if table=='main_category': parents=chosen
        mapping={}
        for i in chosen:
            mapping[i]=st.selectbox(f'Quelle: {names[i]}',[None]+list(range(nsrc)),format_func=lambda x:'Keine Quellenzuordnung' if x is None else f'Quelle {x+1}: {new_sources[x][1] or new_sources[x][0]}',key=key(f'proof_{k}_{i}'))
        selections.append((junction,k,mapping))
    if st.button('Unternehmen vollständig speichern',type='primary'):
        try:
            save_new_company(name,website,desc,size,new_locations,new_sources,selections)
            st.session_state['new_generation']=st.session_state.get('new_generation',0)+1
            st.session_state['notice']='Unternehmen einschließlich Standorten, Quellen und Klassifikationen gespeichert.'
            st.rerun()
        except (sqlite3.Error,ValueError) as e: st.error(str(e))
    st.stop()
if not companies: st.info('Noch keine Unternehmen vorhanden. Wähle links Unternehmen anlegen.'); st.stop()
search=st.sidebar.text_input('Unternehmen suchen')
choices={r['company_id']:r for r in companies if search.casefold() in r['name'].casefold()}
if not choices: st.info('Keine Treffer.'); st.stop()
cid=st.sidebar.selectbox('Unternehmen',list(choices),format_func=lambda i:f"{choices[i]['name']} (#{i})")
r=choices[cid]
st.header(r['name'])
st.caption('Freigabestatus: '+admin.STATUS[r['review_status']])
origin=st.selectbox('Datenerfassung / Herkunft',['Unknown','AI','Manual','Hybrid'],index=['Unknown','AI','Manual','Hybrid'].index(r['data_origin']),key=f'origin_{cid}')
if st.button('Herkunft speichern'): run(lambda:write('UPDATE company SET data_origin=? WHERE company_id=?',(origin,cid)),'Herkunft gespeichert.')
t1,t2,t3,t4=st.tabs(['Stammdaten','Standorte','Quellen','Klassifikationen'])
with t1:
    with st.form(f'company{cid}'):
        name=st.text_input('Name *',r['name']); website=st.text_input('Website',r['website'] or ''); desc=st.text_area('Beschreibung',r['description'] or '')
        size=st.selectbox('Größe',list(sizes),index=list(sizes).index(r['size_id']),format_func=sizes.get)
        if st.form_submit_button('Stammdaten speichern'): run(lambda:write('UPDATE company SET name=?,website=?,description=?,size_id=? WHERE company_id=?',(required(name,'Name'),clean(website),clean(desc),size,cid)),'Stammdaten gespeichert.')
locations=rows('SELECT * FROM location WHERE company_id=? ORDER BY location_id',(cid,))
locs={r['location_id']:r for r in locations}
with t2:
    lid=st.selectbox('Standort wählen',[None]+list(locs),format_func=lambda i:'Neuer Standort' if i is None else f"{locs[i]['city']} – {locs[i]['address_line_1'] or ''} (#{i})",key=f'loc{cid}')
    l=locs.get(lid,{})
    with st.form(f'location{cid}_{lid}'):
        country=st.selectbox('Land',list(countries),index=list(countries).index(l.get('country_code','DE')) if l.get('country_code','DE') in countries else 0,format_func=countries.get)
        region=st.text_input('Bundesland / Region',l.get('state_province_region') or ('Nordrhein-Westfalen' if lid is None else ''))
        city=st.text_input('Stadt *',l.get('city') or ''); postal=st.text_input('Postleitzahl',l.get('postal_code') or '')
        addr=st.text_input('Straße und Hausnummer',l.get('address_line_1') or ''); addr2=st.text_input('Adresszusatz',l.get('address_line_2') or '')
        lat=st.text_input('Breitengrad',str(l['latitude']) if l.get('latitude') is not None else ''); lon=st.text_input('Längengrad',str(l['longitude']) if l.get('longitude') is not None else '')
        def save_location():
            vals=(country,clean(region),required(city,'Stadt'),clean(postal),clean(addr),clean(addr2),*coordinates(lat,lon))
            if lid is None: write('INSERT INTO location(country_code,state_province_region,city,postal_code,address_line_1,address_line_2,latitude,longitude,company_id) VALUES (?,?,?,?,?,?,?,?,?)',vals+(cid,))
            else: write('UPDATE location SET country_code=?,state_province_region=?,city=?,postal_code=?,address_line_1=?,address_line_2=?,latitude=?,longitude=? WHERE location_id=? AND company_id=?',vals+(lid,cid))
        if st.form_submit_button('Standort speichern'): run(save_location,'Standort gespeichert.')
    points=[{'lat':l['latitude'],'lon':l['longitude']} for l in locations if l['latitude'] is not None and l['longitude'] is not None]
    if points: st.map(__import__('pandas').DataFrame(points))
sources=rows('SELECT * FROM source WHERE company_id=? ORDER BY source_id',(cid,))
src={r['source_id']:r for r in sources}
def source_label(i): return 'Keine Quellenzuordnung' if i is None else f"#{i} – {src[i]['title'] or src[i]['url']}"
with t3:
    sid=st.selectbox('Quelle wählen',[None]+list(src),format_func=lambda i:'Neue Quelle' if i is None else source_label(i),key=f'src{cid}')
    s=src.get(sid,{})
    with st.form(f'source{cid}_{sid}'):
        url=st.text_input('URL *',s.get('url') or ''); title=st.text_input('Titel',s.get('title') or '')
        typ=st.text_input('Quellentyp',s.get('source_type') or 'Unternehmenswebsite')
        accessed=st.text_input('Abrufdatum (JJJJ-MM-TT)',s.get('accessed_at') or date.today().isoformat())
        notes=st.text_area('Notizen',s.get('notes') or '')
        opts=[None]+list(locs); loc=st.selectbox('Standortbezug',opts,index=opts.index(s.get('location_id')),format_func=lambda i:'Gesamtes Unternehmen' if i is None else f"{locs[i]['city']} (#{i})")
        def save_source():
            if accessed.strip(): date.fromisoformat(accessed.strip())
            vals=(required(url,'URL'),clean(title),clean(typ),clean(accessed),clean(notes),loc)
            if sid is None: write('INSERT INTO source(url,title,source_type,accessed_at,notes,location_id,company_id) VALUES (?,?,?,?,?,?,?)',vals+(cid,))
            else: write('UPDATE source SET url=?,title=?,source_type=?,accessed_at=?,notes=?,location_id=? WHERE source_id=? AND company_id=?',vals+(sid,cid))
        if st.form_submit_button('Quelle speichern'): run(save_source,'Quelle gespeichert.')
with t4:
    groups=[('Lieferkettenrollen','supply_chain_role','company_role','role_id'),('Hauptkategorien','main_category','company_category','maincategory_id'),('Unterkategorien','subcategory','company_subcategory','subcategory_id')]
    selections=[]
    parent_ids=[]
    for label,table,junction,key in groups:
        entries=rows(f'SELECT * FROM {table} ORDER BY {key}')
        existing={r[key]:r['source_id'] for r in rows(f'SELECT * FROM {junction} WHERE company_id=?',(cid,))}
        names={r[key]:r['name_de'] for r in entries}
        allowed=list(names)
        if table=='subcategory':
            allowed=[r[key] for r in entries if r['maincategory_id'] in parent_ids]
            wk=f'choose_{cid}_{key}'
            if wk in st.session_state: st.session_state[wk]=[i for i in st.session_state[wk] if i in allowed]
        chosen=st.multiselect(label,allowed,default=[i for i in existing if i in allowed],format_func=names.get,key=f'choose_{cid}_{key}')
        if table=='main_category': parent_ids=chosen
        mapping={}
        for i in chosen:
            options=[None]+list(src)
            old=existing.get(i)
            mapping[i]=st.selectbox(f'Quelle: {names[i]}',options,index=options.index(old) if old in options else 0,format_func=source_label,key=f'proof_{cid}_{key}_{i}')
        selections.append((junction,key,mapping))
    def save_classifications():
        c=connect(path)
        try:
            with c:
                for j,k,m in selections:
                    c.execute(f'DELETE FROM {j} WHERE company_id=?',(cid,))
                    c.executemany(f'INSERT INTO {j}(company_id,{k},source_id) VALUES (?,?,?)',[(cid,i,s) for i,s in m.items()])
        finally: c.close()
    st.caption('Unterkategorien werden nach Hauptkategorien gefiltert. Nicht mehr passende Zuordnungen werden beim Speichern entfernt.')
    if st.button('Klassifikationen speichern',type='primary'): run(save_classifications,'Klassifikationen gespeichert.')
