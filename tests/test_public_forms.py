import test_app
from datetime import datetime,timedelta
app=test_app.app
class PublicForms(test_app.Integration):
    test_auth_csrf_and_security_headers=None
    test_booking_employee_and_private_records=None
    test_chat_message_and_password_change=None
    test_word_draft_publish_links_images_and_restore=None
    test_limits_validation_and_mail_delivery=None
    test_mail_outbox_success_and_failure=None
    def test_booking_works_while_signed_in_without_admin_token(self):
        day=datetime.now(app.TZ)+timedelta(days=1)
        while day.weekday()!=0:day+=timedelta(days=1)
        body={'name':'Visitor','email':'visitor@example.com','phone':'123','service':app.SERVICES[0]['name'],'day':day.strftime('%Y-%m-%d'),'time':'10:00'}
        r=self.call('/suncityoptics/api/book',body,cookie=self.cookie)
        self.assertEqual(r['status'],200,r.get('json'))
        self.assertEqual(len(self.admin('dashboard')['json']['bookings']),1)
    def test_messages_work_with_signed_in_or_expired_session(self):
        body={'name':'Visitor','email':'visitor@example.com','message':'Hello from the public chatbox'}
        r=self.call('/suncityoptics/api/message',body,cookie=self.cookie)
        self.assertEqual(r['status'],200,r.get('json'))
        with app.db() as c:c.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.call('/suncityoptics/api/message',body,cookie=self.cookie)['status'],200)
    def test_admin_token_and_public_origin_checks_remain_enforced(self):
        body={'name':'Visitor','email':'visitor@example.com','message':'Hello'}
        self.assertEqual(self.call('/suncityoptics/api/message',body,cookie=self.cookie,origin='https://other.example')['status'],403)
        self.assertEqual(self.call('/suncityoptics/api/admin/settings',{'headline':'No token'},cookie=self.cookie)['status'],403)
        self.assertEqual(self.call('/suncityoptics/api/admin/settings',{'headline':'Bad token'},cookie=self.cookie,csrf='incorrect')['status'],403)
        self.assertEqual(self.call('/suncityoptics/api/admin/settings',{'headline':'Correct token'},cookie=self.cookie,csrf=self.csrf)['status'],200)
