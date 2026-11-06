"""Optional HTTPS email delivery for hosts that block SMTP ports."""
import os,json
from urllib.request import Request,urlopen

def send_https(message,idempotency_key):
    key=os.environ.get('RESEND_API_KEY','')
    if not key:raise ValueError('HTTPS mail key is not configured.')
    payload={'from':str(message['From']),'to':[str(message['To'])],'subject':str(message['Subject']),'text':message.get_content()}
    request=Request('https://api.resend.com/emails',data=json.dumps(payload).encode(),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','Idempotency-Key':idempotency_key,'User-Agent':'SunCityOptics/3'})
    with urlopen(request,timeout=20) as response:
        result=json.loads(response.read(65536))
        if not result.get('id'):raise ValueError('Email provider did not accept the alert.')
