import unittest, tempfile, os, sys, json, io, zipfile, base64
from datetime import datetime, timedelta
os.environ['SUNCITY_DATA']=tempfile.mkdtemp(prefix='suncity-test-')
os.environ['PUBLIC_ORIGIN']='https://optics.example'
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
import app
class Integration(unittest.TestCase):
    def call(self,path,body=None,cookie='',csrf='',origin='https://optics.example',raw=False):
        data=body if raw else json.dumps(body).encode() if body is not None else b''
        env={'PATH_INFO':path,'REQUEST_METHOD':'POST' if body is not None else 'GET','CONTENT_LENGTH':str(len(data)),'wsgi.input':io.BytesIO(data),'HTTP_ORIGIN':origin,'HTTP_COOKIE':cookie,'HTTP_X_CSRF_TOKEN':csrf,'REMOTE_ADDR':'test'}
        captured={}
        def start(status,headers):captured.update(status=int(status.split()[0]),headers=dict(headers))
        out=b''.join(app.application(env,start));captured['body']=out
        try:captured['json']=json.loads(out)
        except Exception:pass
        return captured
    def setUp(self):
        with app.db() as c:
            for t in ('admins','sessions','bookings','messages','employees','outbox','limits'):c.execute('DELETE FROM '+t)
            c.execute('UPDATE settings SET value=? WHERE id=1',(json.dumps(app.DEFAULT),))
            salt='11'*16;c.execute('INSERT INTO admins VALUES(?,?,?)',('owner',salt,app.pw('a-long-test-password',salt)))
        login=self.call('/api/login',{'username':'owner','password':'a-long-test-password'})
        self.cookie=login['headers']['Set-Cookie'].split(';')[0];self.csrf=login['json']['csrf']
    def admin(self,path,body=None,raw=False):return self.call('/api/admin/'+path,body,self.cookie,self.csrf,raw=raw)
    def test_auth_csrf_and_security_headers(self):
        self.assertEqual(self.call('/api/admin/dashboard')['status'],401)
        self.assertEqual(self.call('/api/admin/settings',{'name':'x'},self.cookie)['status'],403)
        self.assertEqual(self.call('/api/login',{},origin='https://evil.example')['status'],403)
        self.assertIn('Secure',self.call('/api/login',{'username':'owner','password':'a-long-test-password'})['headers']['Set-Cookie'])
        self.assertEqual(self.call('/data/site.sqlite3')['status'],404)
        self.assertEqual(self.call('/media/../../app.py')['status'],404)
        self.assertIn('Content-Security-Policy',self.call('/')['headers'])
    def test_booking_employee_and_private_records(self):
        self.assertEqual(self.admin('settings',{'recipients':['a@example.com','b@example.com','c@example.com']})['status'],200)
        self.admin('employee',{'name':'Alex','role':'Optical assistant','email':'private@example.com','phone':'123','bio':'Friendly help','public':True})
        public=self.call('/api/site')['json'];self.assertNotIn('recipients',public);self.assertNotIn('email',public['employees'][0])
        day=datetime.now(app.TZ)+timedelta(days=1)
        while day.weekday()!=0:day+=timedelta(days=1)
        booking={'name':'Visitor','email':'v@example.com','phone':'123','service':app.SERVICES[0]['name'],'day':day.strftime('%Y-%m-%d'),'time':'10:00'}
        self.assertEqual(self.call('/api/book',booking)['status'],200)
        booking['time']='23:00';self.assertEqual(self.call('/api/book',booking)['status'],400)
        dashboard=self.admin('dashboard')['json'];self.assertEqual(len(dashboard['bookings']),1);self.assertEqual(dashboard['mail']['queued'],3)
        employee=dashboard['employees'][0]['id'];bid=dashboard['bookings'][0]['id']
        self.assertEqual(self.admin('booking',{'id':bid,'status':'Confirmed','employee':employee})['status'],200)
        self.assertIn(b'Confirmed',self.admin('export')['body'])
        self.admin('employee',{'id':employee,'delete':True});self.assertIsNone(self.admin('dashboard')['json']['bookings'][0]['employee'])
    def test_chat_message_and_password_change(self):
        self.assertEqual(self.call('/api/message',{'name':'<script>','email':'a@example.com','message':'Hello'})['status'],200)
        self.assertEqual(self.admin('dashboard')['json']['messages'][0]['status'],'Unread')
        mid=self.admin('dashboard')['json']['messages'][0]['id'];self.admin('message',{'id':mid,'read':True})
        self.assertEqual(self.admin('dashboard')['json']['messages'][0]['status'],'Read')
        self.assertEqual(self.admin('password',{'current':'a-long-test-password','password':'a-new-long-password'})['status'],200)
        self.assertEqual(self.admin('dashboard')['status'],401)
    def word(self):
        document='''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Hello &amp; welcome</w:t></w:r></w:p><w:p><w:hyperlink r:id="good"><w:r><w:t>Book now</w:t></w:r></w:hyperlink><w:hyperlink r:id="bad"><w:r><w:t>Unsafe link</w:t></w:r></w:hyperlink><w:r><w:drawing><a:blip r:embed="image"/></w:drawing></w:r></w:p></w:body></w:document>'''
        rel='''<Relationships><Relationship Id="good" Target="https://example.com" TargetMode="External"/><Relationship Id="bad" Target="javascript:alert(1)" TargetMode="External"/><Relationship Id="image" Target="media/test.png"/></Relationships>'''
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('word/document.xml',document);z.writestr('word/_rels/document.xml.rels',rel);z.writestr('word/media/test.png',base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a/p8AAAAASUVORK5CYII='))
        return b.getvalue()
    def test_word_draft_publish_links_images_and_restore(self):
        self.assertEqual(self.admin('word',self.word(),raw=True)['status'],200)
        self.assertEqual(self.call('/api/site')['json']['word_html'],'')
        preview=self.admin('word-preview')['body'].decode();self.assertIn('<h1>Hello &amp; welcome</h1>',preview);self.assertIn('href="https://example.com"',preview);self.assertNotIn('javascript:',preview);self.assertIn('/media/',preview)
        image=__import__('re').search(r'src="(/media/[^\"]+)"',preview).group(1);self.assertEqual(self.call(image)['status'],200)
        self.admin('publish',{'mode':'word'});self.assertIn('Hello',self.call('/api/site')['json']['word_html'])
        self.admin('publish',{'mode':'designed'});self.assertEqual(self.call('/api/site')['json']['word_html'],'')
        self.assertEqual(self.admin('word',b'not a zip',raw=True)['status'],400)
    def test_limits_validation_and_mail_delivery(self):
        self.assertEqual(self.admin('settings',{'recipients':['injected\n@example.com','','']})['status'],400)
        self.assertEqual(self.admin('settings',{'hours':['bad']*7})['status'],400)
        for i in range(8):self.assertEqual(self.call('/api/message',{'name':'V','email':'v@example.com','message':'hi'})['status'],200)
        self.assertEqual(self.call('/api/message',{'name':'V','email':'v@example.com','message':'hi'})['status'],429)
    def test_mail_outbox_success_and_failure(self):
        from unittest.mock import patch,MagicMock
        self.admin('settings',{'recipients':['one@example.com','two@example.com','three@example.com']})
        self.call('/api/message',{'name':'V','email':'visitor@example.com','message':'Private customer detail'})
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.example.com','SMTP_FROM':'shop@example.com'}):
            server=MagicMock();server.__enter__.return_value=server
            with patch('app.smtplib.SMTP',return_value=server):app.process_mail()
            self.assertEqual(server.send_message.call_count,3)
            self.assertNotIn('Private customer detail',server.send_message.call_args[0][0].get_content())
            self.assertEqual(self.admin('dashboard')['json']['mail']['queued'],0)
            self.call('/api/message',{'name':'V','email':'visitor@example.com','message':'Again'})
            with patch('app.smtplib.SMTP',side_effect=OSError('offline')):app.process_mail()
            self.assertEqual(self.admin('dashboard')['json']['mail']['failed'],3)
if __name__=='__main__':unittest.main()
