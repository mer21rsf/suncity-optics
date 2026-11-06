import io,json,zipfile,base64
from urllib.parse import urlencode
import test_app
app=test_app.app
class CatalogPhotos(test_app.Integration):
    test_auth_csrf_and_security_headers=None
    test_booking_employee_and_private_records=None
    test_chat_message_and_password_change=None
    test_word_draft_publish_links_images_and_restore=None
    test_limits_validation_and_mail_delivery=None
    test_mail_outbox_success_and_failure=None
    def image(self):return base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a/p8AAAAASUVORK5CYII=')
    def upload(self,kind):
        r=self.admin(kind,self.image(),raw=True);self.assertEqual(r['status'],200,r.get('json'));return r['json']['image']
    def query(self,path,query):
        env={'PATH_INFO':path,'QUERY_STRING':urlencode(query),'REQUEST_METHOD':'GET','wsgi.input':io.BytesIO(),'REMOTE_ADDR':'test'};out={}
        def start(status,headers):out['status']=int(status.split()[0])
        out['json']=json.loads(b''.join(app.application(env,start)));return out
    def test_unique_model_codes_visibility_edit_and_delete(self):
        image=self.upload('product-image');body={'code':'sc-001','name':'New frames','description':'A frame style','image':image,'visible':True}
        created=self.admin('product',body);self.assertEqual(created['status'],200);pid=created['json']['id']
        public=self.call('/api/products')['json']['products'];self.assertEqual(public[0]['code'],'SC-001');self.assertEqual(public[0]['image'],image)
        self.assertEqual(self.admin('product',body)['status'],409)
        self.assertEqual(self.admin('product',dict(body,id=pid,visible=False))['status'],200);self.assertEqual(self.call('/api/products')['json']['products'],[])
        self.admin('product',dict(body,id=pid,visible=True,code='SC-002'));self.assertEqual(self.call('/api/products')['json']['products'][0]['code'],'SC-002')
        self.admin('product',{'id':pid,'delete':True});self.assertEqual(self.call('/api/products')['json']['products'],[])
    def test_catalog_search_and_model_code_message(self):
        image=self.upload('product-image');self.admin('product',{'code':'SC-001','name':'Amber','image':image})
        r=self.query('/api/products',{'q':'sc-001'});self.assertEqual(len(r['json']['products']),1)
        self.assertEqual(self.query('/api/products',{'q':'unknown'})['json']['products'],[])
        note='I am interested in model SC-001 (Amber). Please confirm price and availability.'
        self.assertEqual(self.call('/api/message',{'name':'Visitor','email':'v@example.com','message':note})['status'],200)
        self.assertIn('SC-001',self.admin('dashboard')['json']['messages'][0]['message'])
    def test_catalog_management_admin_only(self):
        with app.db() as c:c.execute("UPDATE admins SET role='staff' WHERE username='owner'")
        self.assertEqual(self.admin('product',{'code':'SC-001','name':'No access'})['status'],403)
        self.assertEqual(self.admin('product-image',self.image(),raw=True)['status'],403)
        self.assertEqual(self.admin('dashboard')['json']['products'],[])
    def test_customer_slides_limit_order_visibility_and_timing(self):
        image=self.upload('customer-photo-image')
        ids=[]
        for n in range(10):
            body={'title':'Customer photo '+str(n),'caption':'Shared with permission','image':image,'alt':'Customer with new eyeglasses','sort_order':9-n,'visible':True,'consent':True}
            r=self.admin('customer-photo',body);self.assertEqual(r['status'],200,r.get('json'));ids.append(r['json']['id'])
        self.assertEqual(self.admin('customer-photo',body)['status'],400)
        public=self.call('/api/customer-photos')['json'];self.assertEqual(len(public['photos']),10);self.assertEqual(public['photos'][0]['title'],'Customer photo 9');self.assertEqual(public['seconds'],5)
        self.assertEqual(self.admin('settings',{'customer_slide_seconds':7})['status'],200);self.assertEqual(self.call('/api/customer-photos')['json']['seconds'],7)
        self.admin('customer-photo',dict(body,id=ids[-1],visible=False));self.assertEqual(len(self.call('/api/customer-photos')['json']['photos']),9)
        self.admin('customer-photo',{'id':ids[0],'delete':True});self.assertEqual(self.admin('customer-photo',body)['status'],200)
    def test_customer_photo_permission_and_staff_denials(self):
        image=self.upload('customer-photo-image');body={'image':image,'alt':'A customer moment','consent':False}
        self.assertEqual(self.admin('customer-photo',body)['status'],400)
        with app.db() as c:c.execute("UPDATE admins SET role='staff' WHERE username='owner'")
        self.assertEqual(self.admin('customer-photo',dict(body,consent=True))['status'],403)
        self.assertEqual(self.admin('customer-photo-image',self.image(),raw=True)['status'],403)
        self.assertEqual(self.admin('dashboard')['json']['customer_photos'],[])
    def test_model_and_customer_photos_in_private_backup(self):
        image=self.upload('product-image');self.admin('product',{'code':'SC-001','name':'A model','image':image})
        self.admin('customer-photo',{'image':image,'alt':'Customer photo','consent':True})
        with zipfile.ZipFile(io.BytesIO(self.admin('backup')['body'])) as z:
            tables=json.loads(z.read('records.json'))['tables'];self.assertEqual(len(tables['products']),1);self.assertEqual(len(tables['customer_photos']),1);self.assertIn('media/'+image.split('/')[-1],z.namelist())
