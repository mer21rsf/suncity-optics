-- Optional: initialize the private app schema in Supabase SQL Editor. No credentials or account data.
BEGIN;
CREATE SCHEMA IF NOT EXISTS suncity;
REVOKE ALL ON SCHEMA suncity FROM PUBLIC;
CREATE TABLE IF NOT EXISTS suncity.settings (id BIGINT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS suncity.admins (username TEXT PRIMARY KEY,salt TEXT,hash TEXT,role TEXT DEFAULT 'admin',display_name TEXT DEFAULT '',enabled INTEGER DEFAULT 1,must_change INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS suncity.sessions (token TEXT PRIMARY KEY,csrf TEXT,expires DOUBLE PRECISION,username TEXT);
CREATE TABLE IF NOT EXISTS suncity.limits (key TEXT PRIMARY KEY,count INTEGER,until DOUBLE PRECISION);
CREATE TABLE IF NOT EXISTS suncity.employees (id BIGSERIAL PRIMARY KEY,name TEXT,role TEXT,email TEXT,phone TEXT,bio TEXT,public INTEGER);
CREATE TABLE IF NOT EXISTS suncity.bookings (id BIGSERIAL PRIMARY KEY,name TEXT,email TEXT,phone TEXT,service TEXT,day TEXT,time TEXT,status TEXT DEFAULT 'Requested',employee BIGINT,created TEXT);
CREATE TABLE IF NOT EXISTS suncity.messages (id BIGSERIAL PRIMARY KEY,name TEXT,email TEXT,message TEXT,status TEXT DEFAULT 'Unread',created TEXT);
CREATE TABLE IF NOT EXISTS suncity.outbox (id BIGSERIAL PRIMARY KEY,recipient TEXT,kind TEXT,record_id BIGINT,sent DOUBLE PRECISION,attempts INTEGER DEFAULT 0,error TEXT DEFAULT '',lease DOUBLE PRECISION DEFAULT 0);
CREATE TABLE IF NOT EXISTS suncity.audit (id BIGSERIAL PRIMARY KEY,created TEXT,actor TEXT,action TEXT,details TEXT);
REVOKE ALL ON ALL TABLES IN SCHEMA suncity FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA suncity FROM PUBLIC;
COMMIT;
