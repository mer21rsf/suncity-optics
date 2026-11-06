import os,io,json,sqlite3,tempfile,zipfile,hashlib
from pathlib import Path
from unittest.mock import patch,MagicMock
import test_app
import persistence,cloud_media,data_tools,mailer
from datetime import datetime
app=test_app.app
class CloudFeatures(test_app.Integration):
    test_auth_csrf_and_security_headers=None
    test_booking_employee_and_private_records=None
    test_chat_message_and_password_change=None
    test_word_draft_publish_links_images_and_restore=None
    test_limits_validation_and_mail_delivery=None
    test_mail_outbox_success_and_failure=None
    def test_cloud_mode_never_falls_back_without_configuration(self):
        with patch.dict(os.environ,{'STORAGE_MODE':'supabase','DATABASE_URL':''}):
            with self.assertRaises(persistence.StorageUnavailable):persistence.connect(app.DATA)
        with patch.dict(os.environ,{'STORAGE_MODE':'local','DATABASE_URL':'postgres://secret'}):
            with self.assertRaises(persistence.StorageUnavailable):persistence.cloud_enabled()
    def test_database_adapter_parameters_ids_and_rollback(self):
        class DbError(Exception):pass
        raw=MagicMock();raw.execute.return_value.fetchone.return_value={'id':37}
        c=persistence.PgConnection(raw,DbError)
        self.assertEqual(c.execute('INSERT INTO bookings(name) VALUES(?)',('visitor',)).lastrowid,37)
        self.assertEqual(raw.execute.call_args[0],('INSERT INTO bookings(name) VALUES(%s) RETURNING id',('visitor',)))
        c.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',('value',));self.assertIn('ON CONFLICT DO NOTHING',raw.execute.call_args[0][0])
        c.execute('BEGIN IMMEDIATE');self.assertIn('pg_advisory_xact_lock',raw.execute.call_args[0][0])
        with self.assertRaises(ValueError):
            with c:raise ValueError('test')
        raw.rollback.assert_called_once();raw.close.assert_called_once()
        raw.execute.side_effect=DbError('SECRET_URL_MUST_NOT_ESCAPE')
        with self.assertRaises(persistence.StorageUnavailable) as error:c.execute('SELECT 1')
        self.assertNotIn('SECRET_URL',str(error.exception))
    def test_private_storage_requests_and_no_local_fallback(self):
        image=b'\x89PNG\r\n\x1a\nexample';name=hashlib.sha256(image).hexdigest()+'.png';store=cloud_media.MediaStore(app.MEDIA_DIR)
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{}'
        with patch.dict(os.environ,{'STORAGE_MODE':'supabase','DATABASE_URL':'postgres://unused','SUPABASE_URL':'https://example.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_TEST','SUPABASE_BUCKET':'suncity-media'}),patch('cloud_media.urlopen',return_value=response) as request:
            (store/name).write_bytes(image);r=request.call_args[0][0]
            self.assertEqual(r.get_method(),'POST');self.assertIn('/storage/v1/object/suncity-media/',r.full_url)
            self.assertEqual(r.get_header('Apikey'),'sb_secret_TEST');self.assertIsNone(r.get_header('Authorization'))
            response.read.return_value=image;self.assertEqual((store/name).read_bytes(),image)
            self.assertIn('/object/authenticated/',request.call_args[0][0].full_url)
            with patch('cloud_media.urlopen',side_effect=OSError('offline')):
                with self.assertRaises(persistence.StorageUnavailable):(store/name).write_bytes(image)
            self.assertFalse((app.MEDIA_DIR/name).exists())
            response.read.return_value=b'{"public":true}'
            with self.assertRaises(persistence.StorageUnavailable):store.check()
    def test_backup_is_private_complete_and_has_no_sessions_or_env(self):
        self.call('/api/message',{'name':'Visitor','email':'v@example.com','message':'Backup me'})
        r=self.admin('backup');self.assertEqual(r['status'],200,r.get('json'))
        with zipfile.ZipFile(io.BytesIO(r['body'])) as z:
            tables=json.loads(z.read('records.json'))['tables']
            self.assertEqual(tables['admins'][0]['username'],'owner');self.assertEqual(tables['messages'][0]['message'],'Backup me')
            self.assertNotIn('sessions',tables);self.assertNotIn('limits',tables);self.assertNotIn('site.env',z.namelist())
        with app.db() as c:c.execute("UPDATE admins SET role='staff' WHERE username='owner'")
        self.assertEqual(self.admin('backup')['status'],403)
    def test_migration_preserves_hashes_and_refuses_existing_target(self):
        source_hash=data_tools.sqlite_records(app.DATA)['admins'][0]['hash']
        target=Path(tempfile.mkdtemp(prefix='suncity-target-'));persistence.initialize(target,{})
        class Target:
            def __init__(self):
                self.c=sqlite3.connect(target/'site.sqlite3');self.c.row_factory=sqlite3.Row
            def execute(self,sql,params=()):
                if sql.startswith('SELECT column_name'):
                    table=params[1];return self.c.execute('SELECT name FROM pragma_table_info(?)',(table,))
                if sql.startswith('SELECT setval'):return self.c.execute('SELECT 1')
                return self.c.execute(sql,params)
            def __enter__(self):return self
            def __exit__(self,kind,value,tb):
                if kind:self.c.rollback()
                else:self.c.commit()
                self.c.close()
        with patch('data_tools.cloud_enabled',return_value=True),patch('data_tools.initialize'),patch('data_tools.connect',side_effect=lambda _:Target()),patch('data_tools.MediaStore') as media:
            result=data_tools.migrate(app.DATA);self.assertEqual(result['records']['admins'],1)
            with self.assertRaises(ValueError):data_tools.migrate(app.DATA)
        c=sqlite3.connect(target/'site.sqlite3');saved=c.execute('SELECT salt,hash FROM admins WHERE username=?',('owner',)).fetchone();c.close()
        self.assertEqual(saved[1],source_hash);self.assertEqual(app.pw('a-long-test-password',saved[0]),saved[1])
        self.assertEqual(data_tools.sqlite_records(app.DATA)['admins'][0]['hash'],source_hash)
    def test_https_email_delivery_and_storage_status(self):
        self.admin('settings',{'recipients':['one@example.com','','']});self.call('/api/message',{'name':'Visitor','email':'v@example.com','message':'Private body'})
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{"id":"email-1"}'
        with patch.dict(os.environ,{'RESEND_API_KEY':'private-test-key','MAIL_FROM':'shop@example.com'}),patch('mailer.urlopen',return_value=response) as request:
            app.process_mail();r=request.call_args[0][0];payload=json.loads(r.data)
            self.assertEqual(r.full_url,'https://api.resend.com/emails');self.assertNotIn('Private body',payload['text'])
            self.assertEqual(self.admin('dashboard')['json']['mail']['queued'],0)
        self.assertEqual(self.admin('storage')['json']['mode'],'local')
    def test_cloud_connection_uses_verified_tls_and_driver_api(self):
        import types,sys
        fake=types.ModuleType('psycopg');rows=types.ModuleType('psycopg.rows');rows.dict_row=object()
        class DbError(Exception):pass
        fake.Error=DbError;raw=MagicMock();fake.connect=MagicMock(return_value=raw)
        with patch.dict(sys.modules,{'psycopg':fake,'psycopg.rows':rows}),patch.dict(os.environ,{'STORAGE_MODE':'supabase','DATABASE_URL':'postgresql://testuser:testpassword@example.invalid:5432/postgres'}):
            with persistence.connect(app.DATA) as c:c.execute('SELECT 1')
            self.assertEqual(fake.connect.call_args.kwargs['sslmode'],'verify-full')
            self.assertIsNone(fake.connect.call_args.kwargs['prepare_threshold'])
            raw.commit.assert_called_once();raw.close.assert_called_once()
    def test_cloud_request_failure_returns_error_not_saved(self):
        with patch('app.connect',side_effect=persistence.StorageUnavailable('Cloud database unavailable')):
            r=self.call('/api/message',{'name':'V','email':'v@example.com','message':'must not claim saved'})
            self.assertEqual(r['status'],503);self.assertNotIn('reference',r['json'])
        with app.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM messages').fetchone()[0],0)
    def test_failed_image_migration_does_not_commit_records(self):
        image=b'\x89PNG\r\n\x1a\nlocal';name=hashlib.sha256(image).hexdigest()+'.png';(app.MEDIA_DIR/name).write_bytes(image)
        s=app.settings();s['doc_live']='<img src="/suncityoptics/media/'+name+'">'
        with app.db() as c:c.execute('UPDATE settings SET value=? WHERE id=1',(json.dumps(s),))
        target=Path(tempfile.mkdtemp(prefix='suncity-failed-migration-'));persistence.initialize(target,{})
        class Target:
            def __enter__(self):
                self.c=sqlite3.connect(target/'site.sqlite3');self.c.row_factory=sqlite3.Row;return self
            def execute(self,sql,params=()):return self.c.execute(sql,params)
            def __exit__(self,kind,value,tb):
                if kind:self.c.rollback()
                else:self.c.commit()
                self.c.close()
        with patch('data_tools.cloud_enabled',return_value=True),patch('data_tools.initialize'),patch('data_tools.connect',side_effect=lambda _:Target()),patch('data_tools.MediaStore') as store:
            store.return_value.__truediv__.return_value.write_bytes.side_effect=persistence.StorageUnavailable('offline')
            with self.assertRaises(persistence.StorageUnavailable):data_tools.migrate(app.DATA)
        c=sqlite3.connect(target/'site.sqlite3');self.assertEqual(c.execute('SELECT count(*) FROM admins').fetchone()[0],0);self.assertEqual(c.execute('SELECT value FROM settings').fetchone()[0],'{}');c.close()
        self.assertEqual(data_tools.sqlite_records(app.DATA)['admins'][0]['username'],'owner')
    def test_backup_includes_word_images(self):
        self.assertEqual(self.admin('word',self.word(),raw=True)['status'],200)
        r=self.admin('backup');self.assertEqual(r['status'],200,r.get('json'))
        with zipfile.ZipFile(io.BytesIO(r['body'])) as z:self.assertTrue(any(n.startswith('media/') for n in z.namelist()))
