import io,json,zipfile,base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from urllib.parse import urlencode
import test_app
import scheduling,persistence
app=test_app.app
class CalendarControls(test_app.Integration):
    test_auth_csrf_and_security_headers=None
    test_booking_employee_and_private_records=None
    test_chat_message_and_password_change=None
    test_word_draft_publish_links_images_and_restore=None
    test_limits_validation_and_mail_delivery=None
    test_mail_outbox_success_and_failure=None
    def monday(self):
        day=datetime.now(app.TZ).date()+timedelta(days=2)
        while day.weekday()!=0:day+=timedelta(days=1)
        return day.isoformat()
    def book(self,clock='10:00',day=None,service=None):
        return self.call('/api/book',{'name':'Calendar Visitor','email':'private-calendar@example.com','phone':'123','service':service or app.SERVICES[0]['name'],'day':day or self.monday(),'time':clock})
    def availability(self,service=None,day=None):
        return self.avail_call(service or app.SERVICES[0]['name'],day or self.monday())
    def avail_call(self,service,day):
        # Test helper includes QUERY_STRING separately as a real WSGI server does.
        env={'PATH_INFO':'/suncityoptics/api/availability','QUERY_STRING':urlencode({'service':service,'month':day[:7]}),'REQUEST_METHOD':'GET','wsgi.input':io.BytesIO(),'REMOTE_ADDR':'test'};out={}
        def start(status,headers):out['status']=int(status.split()[0])
        out['json']=json.loads(b''.join(app.application(env,start)));return out
    def test_closing_time_complete_duration_and_adjacent_slots(self):
        self.assertEqual(self.book('16:45')['status'],400)
        self.assertEqual(self.book('17:00')['status'],400)
        self.assertEqual(self.book('16:30')['status'],200)
        self.assertEqual(self.book('10:00')['status'],200)
        self.assertEqual(self.book('10:30')['status'],200)
    def test_overlaps_across_services_and_snapshot_duration(self):
        self.assertEqual(self.book()['status'],200)
        self.assertEqual(self.book()['status'],409)
        self.assertEqual(self.book('09:45',service=app.SERVICES[3]['name'])['status'],409)
        s=app.settings();s['services'][0]['minutes']=5
        self.admin('settings',{'services':s['services']})
        self.assertEqual(self.book('10:15')['status'],409)
        self.assertEqual(self.admin('dashboard')['json']['bookings'][0]['minutes'],30)
    def test_custom_hours_relative_slot_grid_and_closed_day(self):
        hours=list(app.settings()['hours']);hours[1]='09:10–10:10';self.admin('settings',{'hours':hours})
        r=self.availability();self.assertEqual(r['status'],200);self.assertEqual(r['json']['timezone'],'America/Vancouver')
        day=next(d for d in r['json']['days'] if d['day']==self.monday())
        self.assertEqual([s['time'] for s in day['slots']],['09:10','09:25','09:40'])
        self.assertEqual(self.book('09:15')['status'],400);self.assertEqual(self.book('09:40')['status'],200)
        hours[1]='Closed';self.admin('settings',{'hours':hours});self.assertEqual(self.book('09:10')['status'],400)
    def test_parallel_submissions_only_one_reservation(self):
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.book(),range(2)))
        self.assertEqual(sorted(r['status'] for r in results),[200,409])
        with app.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM bookings').fetchone()[0],1)
    def test_availability_hides_contact_data_and_cancel_releases(self):
        booked=self.book();bid=booked['json']['reference'];r=self.availability()
        self.assertNotIn('private-calendar@example.com',json.dumps(r['json']))
        day=next(d for d in r['json']['days'] if d['day']==self.monday());self.assertFalse(next(s for s in day['slots'] if s['time']=='10:00')['available'])
        self.assertEqual(self.admin('booking',{'id':bid,'status':'Cancelled'})['status'],200)
        self.assertEqual(self.book()['status'],200)
        self.assertEqual(self.admin('booking',{'id':bid,'status':'Confirmed'})['status'],409)
    def test_time_blocks_and_all_day_closures(self):
        self.assertEqual(self.admin('calendar-block',{'day':self.monday(),'start':'12:00','end':'13:00','label':'Private lunch'})['status'],200)
        self.assertEqual(self.book('12:00')['status'],409)
        self.assertNotIn('Private lunch',json.dumps(self.availability()['json']))
        block=self.admin('dashboard')['json']['calendar_blocks'][0]
        self.admin('calendar-block',{'id':block['id'],'delete':True});self.assertEqual(self.book('12:00')['status'],200)
        self.assertEqual(self.admin('calendar-block',{'day':self.monday(),'all_day':True})['status'],409)
        tomorrow=(datetime.fromisoformat(self.monday())+timedelta(days=1)).date().isoformat()
        self.assertEqual(self.admin('calendar-block',{'day':tomorrow,'all_day':True})['status'],200)
        self.assertEqual(self.book('10:00',day=tomorrow)['status'],409)
    def test_delete_records_is_admin_only_and_frees_slots(self):
        bid=self.book()['json']['reference'];mid=self.call('/api/message',{'name':'V','email':'v@example.com','message':'Delete me'})['json']['reference']
        with app.db() as c:c.execute("UPDATE admins SET role='staff' WHERE username='owner'")
        self.assertEqual(self.admin('delete-record',{'type':'booking','id':bid})['status'],403)
        with app.db() as c:c.execute("UPDATE admins SET role='admin' WHERE username='owner'")
        self.assertEqual(self.admin('delete-record',{'type':'booking','id':bid})['status'],200)
        self.assertEqual(self.book()['status'],200)
        self.assertEqual(self.admin('delete-record',{'type':'message','id':mid})['status'],200)
        self.assertEqual(self.admin('dashboard')['json']['messages'],[])
    def test_log_retention_selected_cleanup_and_receipt(self):
        with app.db() as c:
            old=c.execute('INSERT INTO audit(created,actor,action,details) VALUES(?,?,?,?)',('2000-01-01T00:00:00-08:00','old','old action','{}')).lastrowid
        self.assertEqual(self.admin('clear-history',{'mode':'older','days':30})['json']['removed'],1)
        with app.db() as c:self.assertFalse(c.execute('SELECT id FROM audit WHERE id=? AND action=?',(old,'old action')).fetchone())
        logs=self.admin('audit')['json']['logs'];self.assertEqual(self.admin('clear-history',{'mode':'selected','ids':[logs[0]['id']]})['status'],200)
        self.assertEqual(self.admin('clear-history',{'mode':'all'})['status'],200)
        logs=self.admin('audit')['json']['logs'];self.assertEqual(len(logs),1);self.assertEqual(logs[0]['action'],'Cleaned change history')
        with app.db() as c:c.execute("UPDATE admins SET role='staff' WHERE username='owner'")
        self.assertEqual(self.admin('clear-history',{'mode':'all'})['status'],403)
    def test_legacy_duplicate_records_retained_and_flagged(self):
        self.book()
        with app.db() as c:c.execute('INSERT INTO bookings(name,email,phone,service,day,time,status,created) VALUES(?,?,?,?,?,?,?,?)',('Legacy','legacy@example.com','123',app.SERVICES[0]['name'],self.monday(),'10:00','Requested',datetime.now(app.TZ).isoformat()))
        persistence.initialize(app.DATA,app.DEFAULT)
        d=self.admin('dashboard')['json'];self.assertEqual(len(d['bookings']),2);self.assertTrue(any(i['type']=='overlap' for i in d['booking_issues']))
        self.assertTrue(all(b['minutes']==30 for b in d['bookings']));self.assertEqual(self.book()['status'],409)
    def test_community_notes_wait_for_admin_approval_and_can_be_hidden(self):
        note={'name':'A Visitor','email':'private@example.com','note':'Thank you for helping me choose my frames!','consent':'on'}
        posted=self.call('/api/story',note);self.assertEqual(posted['status'],200);nid=posted['json']['reference']
        self.assertEqual(self.call('/api/stories')['json']['stories'],[])
        self.assertEqual(self.admin('story',{'id':nid,'status':'Approved'})['status'],200)
        public=self.call('/api/stories')['json']['stories'];self.assertEqual(len(public),1);self.assertNotIn('email',public[0])
        self.admin('story',{'id':nid,'status':'Rejected'});self.assertEqual(self.call('/api/stories')['json']['stories'],[])
        self.admin('story',{'id':nid,'delete':True});self.assertEqual(self.admin('dashboard')['json']['stories'],[])
    def test_story_consent_and_staff_moderation_permissions(self):
        body={'name':'V','note':'A note','consent':False};self.assertEqual(self.call('/api/story',body)['status'],400)
        body['consent']=True;nid=self.call('/api/story',body)['json']['reference']
        with app.db() as c:c.execute("UPDATE admins SET role='staff' WHERE username='owner'")
        self.assertEqual(self.admin('story',{'id':nid,'status':'Approved'})['status'],403)
        self.assertEqual(self.admin('story',{'id':nid,'delete':True})['status'],403)
        self.assertEqual(self.admin('dashboard')['json']['stories'],[])
    def test_featured_photo_upload_preview_url_and_private_backup(self):
        image=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a/p8AAAAASUVORK5CYII=')
        response=self.admin('hero-image',image,raw=True);self.assertEqual(response['status'],200,response.get('json'))
        url=response['json']['image'];self.assertEqual(self.call(url)['body'],image)
        self.assertEqual(self.admin('settings',{'hero_image':url,'hero_alt':'Featured AI eyewear model'})['status'],200)
        self.assertEqual(self.call('/api/site')['json']['hero_image'],url)
        with zipfile.ZipFile(io.BytesIO(self.admin('backup')['body'])) as z:self.assertIn('media/'+url.split('/')[-1],z.namelist())
        self.assertEqual(self.admin('hero-image',b'<html>not an image</html>',raw=True)['status'],400)
        self.assertEqual(self.call('/api/admin/hero-image',image,raw=True)['status'],401)
    def test_booking_delete_removes_only_its_notification_records(self):
        self.admin('settings',{'recipients':['alerts@example.com','','']})
        bid=self.book()['json']['reference'];self.call('/api/message',{'name':'V','email':'v@example.com','message':'Keep this message alert'})
        self.admin('delete-record',{'type':'booking','id':bid})
        with app.db() as c:
            kinds=[r[0] for r in c.execute('SELECT kind FROM outbox')]
            self.assertEqual(kinds,['chat message'])
    def test_backup_includes_manual_blocks_and_pending_story_records(self):
        self.admin('calendar-block',{'day':self.monday(),'start':'12:00','end':'13:00'})
        self.call('/api/story',{'name':'V','note':'Awaiting review','consent':True})
        with zipfile.ZipFile(io.BytesIO(self.admin('backup')['body'])) as z:
            tables=json.loads(z.read('records.json'))['tables'];self.assertEqual(len(tables['booking_blocks']),1);self.assertEqual(tables['stories'][0]['status'],'Pending')
