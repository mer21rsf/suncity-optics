import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_app
import persistence
class ConnectionDiagnostics(unittest.TestCase):
    def test_error_categories_never_include_raw_credentials(self):
        class Error(Exception):sqlstate=None
        secret='postgresql://USER:SUPER_SECRET@hostname.example/postgres'
        cases=[('password authentication failed','DATABASE_AUTH_FAILED'),('certificate verify failed','DATABASE_TLS_VERIFY'),('tenant or user not found','DATABASE_POOLER_USER'),('could not translate host','DATABASE_DNS_FAILED'),('connection timed out','DATABASE_TIMEOUT'),('too many clients','DATABASE_CONNECTION_LIMIT'),('connection refused','DATABASE_NETWORK_FAILED'),('other failure','DATABASE_CONNECT_FAILED')]
        for raw,code in cases:
            result=persistence.connection_error_hint(Error(raw+' '+secret))
            self.assertTrue(result.startswith(code),result);self.assertNotIn('SUPER_SECRET',result);self.assertNotIn(secret,result)
    def test_missing_and_invalid_ca_files_are_explicit(self):
        uri='postgresql://user:password@host.example:5432/postgres'
        with tempfile.TemporaryDirectory() as temp:
            cert=Path(temp)/'ca.crt'
            with patch.dict(os.environ,{'DATABASE_URL':uri,'PGSSLROOTCERT':str(cert)}):
                with self.assertRaisesRegex(persistence.StorageUnavailable,'DATABASE_CA_MISSING'):persistence.checked_connection_config()
                cert.write_text('not a PEM certificate')
                with self.assertRaisesRegex(persistence.StorageUnavailable,'DATABASE_CA_INVALID'):persistence.checked_connection_config()
    def test_invalid_or_placeholder_uris_are_not_echoed(self):
        for uri in ('DATABASE_URL=postgresql://u:pass@host/db','postgresql://u:[YOUR-PASSWORD]@host/db','postgresql://u:secret#password@host/db','postgresql://u:bad%pass@host/db'):
            with patch.dict(os.environ,{'DATABASE_URL':uri}):
                with self.assertRaises(persistence.StorageUnavailable) as error:persistence.checked_connection_config()
                self.assertTrue(str(error.exception).startswith('DATABASE_URL_INVALID'));self.assertNotIn(uri,str(error.exception))
