import test_app
from pathlib import Path
import shutil,tempfile
from unittest.mock import patch
class PortableLayout(test_app.Integration):
    test_auth_csrf_and_security_headers=None
    test_booking_employee_and_private_records=None
    test_chat_message_and_password_change=None
    test_word_draft_publish_links_images_and_restore=None
    test_limits_validation_and_mail_delivery=None
    test_mail_outbox_success_and_failure=None
    def test_original_render_public_folder(self):
        root=Path(tempfile.mkdtemp(prefix='suncity-render-layout-'));(root/'public').mkdir()
        for name in ('index.html','admin.html','style.css','site.js','admin.js','eyewear.svg'):shutil.copy2(test_app.app.BASE/name,root/'public'/name)
        with patch.object(test_app.app,'BASE',root):
            for path in ('/','/admin','/style.css','/site.js','/suncityoptics/index.html','/suncityoptics/admin','/suncityoptics/admin.js'):
                self.assertEqual(self.call(path)['status'],200,path)
            self.assertEqual(self.call('/public/app.py')['status'],404)
            self.assertEqual(self.call('/suncityoptics/api/admin/dashboard')['status'],401)
