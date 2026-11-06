"""Private portable backups and one-way migration; never needs plaintext site passwords."""
import os,io,json,sqlite3,tempfile,zipfile,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from persistence import connect,initialize,cloud_enabled,AUTO_TABLES,StorageUnavailable
from cloud_media import MediaStore,IMAGE
RECORD_TABLES=('settings','admins','employees','bookings','messages','outbox','audit','booking_blocks','stories','products','customer_photos')
MAX_BACKUP=32*1024*1024

def load_env_file(path):
    for line in Path(path).read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        if '=' not in line:raise ValueError('Each environment entry must be KEY=value.')
        key,value=line.split('=',1);key=key.strip();value=value.strip()
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*',key):raise ValueError('Invalid environment key.')
        if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):value=value[1:-1]
        os.environ[key]=value

def sqlite_records(source):
    path=Path(source)/'site.sqlite3'
    if not path.is_file():raise ValueError('Source folder must contain site.sqlite3.')
    # Online backup API gives a consistent read without altering the original database.
    with tempfile.TemporaryDirectory(prefix='suncity-read-') as temp:
        raw=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
        snapshot=sqlite3.connect(str(Path(temp)/'snapshot.sqlite3'));raw.backup(snapshot);raw.close();snapshot.row_factory=sqlite3.Row
        available={r[0] for r in snapshot.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result={table:[dict(r) for r in snapshot.execute('SELECT * FROM '+table)] if table in available else [] for table in RECORD_TABLES}
        snapshot.close()
    if not result['admins'] or not result['settings']:raise ValueError('Source must contain accounts and settings; nothing was migrated.')
    return result

def referenced_images(records):
    content=json.dumps({'settings':records.get('settings',[]),'products':records.get('products',[]),'customer_photos':records.get('customer_photos',[])})
    return sorted(set(re.findall(r'/(?:suncityoptics/)?media/([a-f0-9]{64}\.(?:png|jpg|gif|webp))',content)))

def backup_bytes(data,media):
    with connect(data) as c:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ' if cloud_enabled() else 'BEGIN')
        records={table:[dict(r) for r in c.execute('SELECT * FROM '+table)] for table in RECORD_TABLES}
    raw=json.dumps({'format':'suncity-backup','version':1,'created':datetime.now(ZoneInfo('America/Vancouver')).isoformat(),'tables':records},ensure_ascii=False).encode()
    if len(raw)>MAX_BACKUP:raise ValueError('Backup is larger than the 32 MB download limit. Use database-provider export tools.')
    out=io.BytesIO();size=len(raw)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('records.json',raw)
        for name in referenced_images(records):
            image=(media/name).read_bytes();size+=len(image)
            if size>MAX_BACKUP:raise ValueError('Backup is larger than the 32 MB download limit. Use database/provider export tools.')
            z.writestr('media/'+name,image)
        z.writestr('README.txt','PRIVATE BACKUP: contains account password hashes and customer records. Store privately. No SMTP/API credentials, active sessions or rate limits are included. This is a backup, not a public website asset. Restore only through a controlled migration procedure.')
    return out.getvalue()

def migrate(source):
    if not cloud_enabled():raise ValueError('Enable STORAGE_MODE=supabase and DATABASE_URL before migration.')
    source=Path(source);records=sqlite_records(source)
    initialize(source,{})
    media=MediaStore(source/'media');media.check()
    uploads=[]
    for name in referenced_images(records):
        p=source/'media'/name
        if not p.is_file():raise ValueError('An image referenced by the source Word page is missing. Restore the source media folder before migration.')
        uploads.append((name,p.read_bytes()))
    with connect(source) as c:
        c.execute('BEGIN IMMEDIATE')
        for table in RECORD_TABLES:
            if table!='settings' and c.execute('SELECT count(*) FROM '+table).fetchone()[0]:raise ValueError('Destination already has application data. Migration refused to overwrite it. Use a fresh Supabase project/schema.')
        # Upload images before committing references; failed uploads leave the source intact.
        for name,data in uploads:(media/name).write_bytes(data)
        c.execute('DELETE FROM settings')
        allowed={t:{r[0] for r in c.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=? AND table_name=?',('suncity',t))} for t in RECORD_TABLES}
        for table,rows in records.items():
            for row in rows:
                clean={k:v for k,v in row.items() if k in allowed[table]}
                if table=='outbox':clean['lease']=0
                columns=list(clean)
                if not columns:continue
                c.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(clean[k] for k in columns))
        for table in AUTO_TABLES:
            c.execute("SELECT setval(pg_get_serial_sequence('suncity."+table+"','id'),COALESCE((SELECT max(id) FROM "+table+"),1),(SELECT count(*)>0 FROM "+table+'))')
        c.execute('INSERT INTO audit(created,actor,action,details) VALUES(?,?,?,?)',(datetime.now(ZoneInfo('America/Vancouver')).isoformat(),'migration','Imported existing Pi records',json.dumps({'accounts':len(records['admins']),'images':len(uploads)})))
    return {'records':{t:len(rows) for t,rows in records.items()},'images':len(uploads),'source_unchanged':True}
