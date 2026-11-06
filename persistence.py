"""Durable PostgreSQL or local SQLite, behind the application's small DB API."""
import os,re,json,sqlite3
from collections.abc import Mapping
class StorageUnavailable(RuntimeError):pass
AUTO_TABLES={'employees','bookings','messages','outbox','audit'}
TABLES={
'settings':'id BIGINT PRIMARY KEY,value TEXT',
'admins':"username TEXT PRIMARY KEY,salt TEXT,hash TEXT,role TEXT DEFAULT 'admin',display_name TEXT DEFAULT '',enabled INTEGER DEFAULT 1,must_change INTEGER DEFAULT 0",
'sessions':'token TEXT PRIMARY KEY,csrf TEXT,expires DOUBLE PRECISION,username TEXT',
'limits':'key TEXT PRIMARY KEY,count INTEGER,until DOUBLE PRECISION',
'employees':'id BIGSERIAL PRIMARY KEY,name TEXT,role TEXT,email TEXT,phone TEXT,bio TEXT,public INTEGER',
'bookings':"id BIGSERIAL PRIMARY KEY,name TEXT,email TEXT,phone TEXT,service TEXT,day TEXT,time TEXT,status TEXT DEFAULT 'Requested',employee BIGINT,created TEXT",
'messages':"id BIGSERIAL PRIMARY KEY,name TEXT,email TEXT,message TEXT,status TEXT DEFAULT 'Unread',created TEXT",
'outbox':"id BIGSERIAL PRIMARY KEY,recipient TEXT,kind TEXT,record_id BIGINT,sent DOUBLE PRECISION,attempts INTEGER DEFAULT 0,error TEXT DEFAULT '',lease DOUBLE PRECISION DEFAULT 0",
'audit':'id BIGSERIAL PRIMARY KEY,created TEXT,actor TEXT,action TEXT,details TEXT'}
def cloud_enabled():
    mode=os.environ.get('STORAGE_MODE','').lower()
    if mode not in ('','local','supabase'):raise StorageUnavailable('STORAGE_MODE must be local or supabase.')
    if mode=='local' and os.environ.get('DATABASE_URL'):raise StorageUnavailable('Remove DATABASE_URL for local mode, or select STORAGE_MODE=supabase.')
    enabled=mode=='supabase' or bool(os.environ.get('DATABASE_URL'))
    if enabled and not os.environ.get('DATABASE_URL'):raise StorageUnavailable('Cloud storage requires DATABASE_URL. No local fallback was used.')
    return enabled
class Record(Mapping):
    def __init__(self,value):self.value=value
    def __getitem__(self,key):return list(self.value.values())[key] if isinstance(key,int) else self.value[key]
    def __iter__(self):return iter(self.value)
    def __len__(self):return len(self.value)
class Cursor:
    def __init__(self,cursor,has_id=False):self.cursor=cursor;self.has_id=has_id;self._id=None
    def fetchone(self):
        value=self.cursor.fetchone();return Record(value) if value is not None else None
    def fetchall(self):return [Record(r) for r in self.cursor.fetchall()]
    def __iter__(self):
        for r in self.cursor:yield Record(r)
    @property
    def lastrowid(self):
        if not self.has_id:return None
        if self._id is None:
            row=self.cursor.fetchone();self._id=list(row.values())[0] if row else None
        return self._id
class PgConnection:
    def __init__(self,connection,error_type):self.raw=connection;self.error_type=error_type
    def execute(self,sql,params=()):
        if sql.strip().upper()=='BEGIN IMMEDIATE':sql='SELECT pg_advisory_xact_lock(74208523)'
        ignore=bool(re.match(r'\s*INSERT OR IGNORE\b',sql,re.I))
        sql=re.sub(r'INSERT OR IGNORE', 'INSERT',sql,flags=re.I).replace('?','%s')
        if ignore:sql=sql.rstrip(';')+' ON CONFLICT DO NOTHING'
        match=re.match(r'\s*INSERT INTO\s+(\w+)\b',sql,re.I)
        has_id=bool(match and match[1].lower() in AUTO_TABLES and 'RETURNING' not in sql.upper())
        if has_id:sql=sql.rstrip(';')+' RETURNING id'
        try:return Cursor(self.raw.execute(sql,params or None),has_id)
        except self.error_type:raise StorageUnavailable('Cloud database request failed. Check project status and database settings; no local fallback was used.') from None
    def __enter__(self):return self
    def __exit__(self,kind,value,tb):
        try:
            if kind:self.raw.rollback()
            else:self.raw.commit()
        except self.error_type:raise StorageUnavailable('Cloud database transaction could not complete.') from None
        finally:self.raw.close()
    def close(self):self.raw.close()
class LocalConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()
def connect(data):
    if not cloud_enabled():
        c=sqlite3.connect(data/'site.sqlite3',timeout=20,factory=LocalConnection);c.row_factory=sqlite3.Row;return c
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:raise StorageUnavailable('Install the supplied PostgreSQL dependency before enabling cloud storage.') from None
    c=None
    try:
        c=psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=12,sslmode='verify-full',sslrootcert=os.environ.get('PGSSLROOTCERT','/etc/ssl/certs/ca-certificates.crt'),prepare_threshold=None)
        c.execute('SET search_path TO suncity');c.execute("SET statement_timeout TO '20000ms'");c.execute("SET lock_timeout TO '12000ms'")
        return PgConnection(c,psycopg.Error)
    except psycopg.Error:
        if c is not None:c.close()
        raise StorageUnavailable('Could not connect to the cloud database. Check DATABASE_URL, project status and network access.') from None

def initialize(data,default):
    if cloud_enabled():
        with connect(data) as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('CREATE SCHEMA IF NOT EXISTS suncity')
            c.execute('REVOKE ALL ON SCHEMA suncity FROM PUBLIC')
            for table,fields in TABLES.items():c.execute('CREATE TABLE IF NOT EXISTS '+table+' ('+fields+')')
            c.execute('REVOKE ALL ON ALL TABLES IN SCHEMA suncity FROM PUBLIC')
            c.execute('REVOKE ALL ON ALL SEQUENCES IN SCHEMA suncity FROM PUBLIC')
            c.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',(json.dumps(default),))
        return
    with connect(data) as c:
        for table,fields in TABLES.items():
            fields=fields.replace('BIGSERIAL PRIMARY KEY','INTEGER PRIMARY KEY').replace('BIGINT','INTEGER').replace('DOUBLE PRECISION','REAL')
            c.execute('CREATE TABLE IF NOT EXISTS '+table+' ('+fields+')')
        # Support the original local package without replacing its password hashes.
        for name,definition in [('role',"TEXT DEFAULT 'admin'"),('display_name',"TEXT DEFAULT ''"),('enabled','INTEGER DEFAULT 1'),('must_change','INTEGER DEFAULT 0')]:
            if name not in {r[1] for r in c.execute('PRAGMA table_info(admins)')}:c.execute('ALTER TABLE admins ADD COLUMN '+name+' '+definition)
        if 'username' not in {r[1] for r in c.execute('PRAGMA table_info(sessions)')}:
            c.execute('ALTER TABLE sessions ADD COLUMN username TEXT');c.execute('DELETE FROM sessions')
        if 'lease' not in {r[1] for r in c.execute('PRAGMA table_info(outbox)')}:c.execute('ALTER TABLE outbox ADD COLUMN lease REAL DEFAULT 0')
        c.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',(json.dumps(default),))
