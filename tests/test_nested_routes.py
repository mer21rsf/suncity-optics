import test_app
app=test_app.app
class NestedRoutes(test_app.Integration):
    test_auth_csrf_and_security_headers=None
    test_booking_employee_and_private_records=None
    test_chat_message_and_password_change=None
    test_word_draft_publish_links_images_and_restore=None
    test_limits_validation_and_mail_delivery=None
    test_mail_outbox_success_and_failure=None
    def test_requested_homepage_and_private_paths(self):
        r=self.call('/suncityoptics/index.html')
        self.assertEqual(r['status'],200)
        self.assertIn(b'/suncityoptics/site.js',r['body'])
        for suffix in ('app.py','docx_import.py','site.env','data/site.sqlite3','deploy/site.env.example','.htaccess','tests/test_app.py'):
            self.assertEqual(self.call('/suncityoptics/'+suffix)['status'],404,suffix)
        self.assertEqual(self.call('/suncityoptics/api/admin/dashboard')['status'],401)
    def test_nested_assets_and_api(self):
        for suffix in ('style.css','site.js','admin.js','eyewear.svg','admin'):
            self.assertEqual(self.call('/suncityoptics/'+suffix)['status'],200,suffix)
        self.assertIn('services',self.call('/suncityoptics/api/site')['json'])
        r=self.call('/suncityoptics/api/login',{'username':'owner','password':'a-long-test-password'})
        self.assertEqual(r['status'],200)
        cookie=r['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.call('/suncityoptics/api/admin/dashboard',cookie=cookie)['status'],200)
