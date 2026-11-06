import os, json, sqlite3, secrets, hashlib, hmac, time, re, sys, mimetypes, traceback, smtplib, ssl, csv, io
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.cookies import SimpleCookie
from email.message import EmailMessage
from docx_import import convert, safe_url
BASE=Path(__file__).resolve().parent
DATA=Path(os.environ.get('SUNCITY_DATA',str(BASE/'data'))); DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
MEDIA=DATA/'media'; MEDIA.mkdir(exist_ok=True)
ORIGIN=os.environ.get('PUBLIC_ORIGIN','http://localhost:8090').rstrip('/')
TZ=ZoneInfo('America/Vancouver')
SERVICES=[{'name':n,'minutes':m,'description':d} for n,m,d in [('Eyeglasses Adjustment',30,'A better fit, a little more comfort.'),('Contact Lens Fitting',30,'Find a fit that feels right for you.'),('Safety Glasses Fitting',60,'Practical protection for your working day.'),('Sight Test',60,'Make time for your vision needs.'),('Eyewear Shopping',60,'Explore frames and find your next favourite.'),('Lens Change or Upgrade',60,'Give your everyday eyewear a fresh perspective.')]]
DEFAULT={'name':'Sun City Optics','eyebrow':'YOUR NEIGHBOURHOOD OPTICAL · SURREY, BC','headline':'See beautifully.\nLive brightly.','intro':'Find frames that feel like you. Discover thoughtfully chosen eyewear and friendly, personal service in the heart of Newton.','about':'Your view of the world deserves a little care. We bring together a wide choice of frames and lenses, accessible prices, and a friendly team to help you find your fit.','phone':'+1 604 355 1337','email':'suncityoptics@gmail.com','address':'Unit 125, 7135 138 Street, Surrey, BC V3W 7T9','facebook':'https://www.facebook.com/suncityoptics.surrey/','setmore':'https://suncityoptics.setmore.com/','hours':['11:00–15:00','09:00–17:00','09:00–17:00','09:00–17:00','09:00–17:00','09:00–17:00','08:00–16:00'],'services':SERVICES,'recipients':['','',''],'accent':'#d27140','hero_image':'','page_mode':'designed','doc_draft':'','doc_live':''}
def db():
    c=sqlite3.connect(DATA/'site.sqlite3',timeout=20);c.row_factory=sqlite3.Row;return c
def init():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS admins(username TEXT PRIMARY KEY,salt TEXT,hash TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,csrf TEXT,expires REAL);
CREATE TABLE IF NOT EXISTS limits(key TEXT PRIMARY KEY,count INTEGER,until REAL);
CREATE TABLE IF NOT EXISTS employees(id INTEGER PRIMARY KEY,name TEXT,role TEXT,email TEXT,phone TEXT,bio TEXT,public INTEGER);
CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,name TEXT,email TEXT,phone TEXT,service TEXT,day TEXT,time TEXT,status TEXT DEFAULT 'Requested',employee INTEGER,created TEXT);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,name TEXT,email TEXT,message TEXT,status TEXT DEFAULT 'Unread',created TEXT);
CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,recipient TEXT,kind TEXT,record_id INTEGER,sent REAL,attempts INTEGER DEFAULT 0,error TEXT DEFAULT '',lease REAL DEFAULT 0);''')
        c.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',(json.dumps(DEFAULT),))
init()
def settings():
    with db() as c:return {**DEFAULT,**json.loads(c.execute('SELECT value FROM settings WHERE id=1').fetchone()[0])}
def pw(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000).hex()
def clean(v,n=500):return str(v or '').strip()[:n]
def email(v):return bool(re.fullmatch(r'[^\s@\r\n]+@[^\s@\r\n]+\.[^\s@\r\n]+',v)) and len(v)<=254
def limit(c,key,max_count,seconds):
    now=time.time();c.execute('DELETE FROM limits WHERE until<?',(now,));c.execute('INSERT OR IGNORE INTO limits VALUES(?,0,?)',(key,now+seconds));c.execute('UPDATE limits SET count=count+1 WHERE key=?',(key,));return c.execute('SELECT count FROM limits WHERE key=?',(key,)).fetchone()[0]<=max_count
def queue(c,kind,rid):
    for recipient in settings()['recipients']:
        if recipient:c.execute('INSERT INTO outbox(recipient,kind,record_id) VALUES(?,?,?)',(recipient,kind,rid))
def process_mail():
    host=os.environ.get('SMTP_HOST'); sender=os.environ.get('SMTP_FROM'); user=os.environ.get('SMTP_USER'); password=os.environ.get('SMTP_PASSWORD')
    if not host or not sender:return
    # Claim each item briefly; never hold a database write lock during SMTP I/O.
    for _ in range(30):
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM outbox WHERE sent IS NULL AND attempts<10 AND lease<? ORDER BY id LIMIT 1',(time.time(),)).fetchone()
            if row is None:break
            c.execute('UPDATE outbox SET lease=?,attempts=attempts+1 WHERE id=?',(time.time()+600,row['id']))
        try:
            msg=EmailMessage();msg['From']=sender;msg['To']=row['recipient'];msg['Subject']='Sun City Optics — new '+row['kind']
            msg.set_content('A new '+row['kind']+' is waiting in your secure admin dashboard.\n\n'+ORIGIN+'/admin\n\nReference: '+str(row['record_id'])+'\nCustomer details are available after signing in.')
            port=int(os.environ.get('SMTP_PORT','587'))
            if port==465: server=smtplib.SMTP_SSL(host,port,timeout=15,context=ssl.create_default_context())
            else:
                server=smtplib.SMTP(host,port,timeout=15);server.ehlo();server.starttls(context=ssl.create_default_context());server.ehlo()
            with server:
                if user:server.login(user,password or '')
                server.send_message(msg)
            with db() as c:c.execute("UPDATE outbox SET sent=?,lease=0,error='' WHERE id=?",(time.time(),row['id']))
        except Exception:
            with db() as c:c.execute('UPDATE outbox SET lease=?,error=? WHERE id=?',(time.time()+60,'Delivery failed; check SMTP credentials and server connectivity.',row['id']))

def application(env,start):
    headers=[('X-Content-Type-Options','nosniff'),('Referrer-Policy','strict-origin-when-cross-origin'),('X-Frame-Options','SAMEORIGIN'),('Content-Security-Policy',"default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'self'; object-src 'none'"),('Cache-Control','no-store')]
    def respond(data,status=200,mime='application/json; charset=utf-8'):
        b=data if isinstance(data,bytes) else json.dumps(data).encode();start(str(status)+' '+{200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',409:'Conflict',413:'Payload Too Large',429:'Too Many Requests',500:'Server Error'}.get(status,'Error'),headers+[('Content-Type',mime),('Content-Length',str(len(b)))]);return [b]
    path=env.get('PATH_INFO','/');method=env.get('REQUEST_METHOD','GET');session=None
    try:
        cookie=SimpleCookie();cookie.load(env.get('HTTP_COOKIE',''));token=cookie['sc_session'].value if 'sc_session' in cookie else ''
        with db() as c:
            c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),));session=c.execute('SELECT * FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if path.startswith('/api/admin') and not session:return respond({'error':'Please sign in.'},401)
        if method not in ('GET','POST'):return respond({'error':'Unsupported request.'},400)
        if method=='POST':
            if env.get('HTTP_ORIGIN','')!=ORIGIN:return respond({'error':'Origin rejected. Configure PUBLIC_ORIGIN to match this address.'},403)
            if session and not hmac.compare_digest(env.get('HTTP_X_CSRF_TOKEN',''),session['csrf']):return respond({'error':'Session check failed. Refresh and sign in again.'},403)
            length=int(env.get('CONTENT_LENGTH') or 0)
            if length<0 or length>10*1024*1024:return respond({'error':'Upload must be under 10 MB.'},413)
            raw=env['wsgi.input'].read(length)
            body={} if path=='/api/admin/word' else json.loads(raw or b'{}')
        if path=='/api/site':
            s=settings();return respond({k:v for k,v in s.items() if k not in ('recipients','doc_draft','doc_live')} | {'word_html':s['doc_live'] if s['page_mode']=='word' else '', 'employees':employees(True)})
        if path=='/api/login' and method=='POST':
            with db() as c:
                if not limit(c,'login:'+env.get('REMOTE_ADDR',''),10,900):return respond({'error':'Too many attempts. Try again in 15 minutes.'},429)
                row=c.execute('SELECT * FROM admins WHERE username=?',(clean(body.get('username'),80),)).fetchone()
                valid=hmac.compare_digest(pw(str(body.get('password','')),row['salt'] if row else '00'*16),row['hash'] if row else '0'*64)
                if not row or not valid:return respond({'error':'Username or password is incorrect.'},401)
                value=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
                c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(value.encode()).hexdigest(),csrf,time.time()+8*3600))
                c.execute('DELETE FROM limits WHERE key=?',('login:'+env.get('REMOTE_ADDR',''),))
                headers.append(('Set-Cookie','sc_session='+value+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if ORIGIN.startswith('https://') else '')))
            return respond({'ok':True,'csrf':csrf})
        if path=='/api/admin/session':return respond({'csrf':session['csrf']})
        if path=='/api/admin/logout' and method=='POST':
            with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(session['token'],))
            headers.append(('Set-Cookie','sc_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'));return respond({'ok':True})
        if path=='/api/admin/password' and method=='POST':
            password=str(body.get('password',''))
            if len(password)<12 or len(password)>128:raise ValueError('Use a password of 12–128 characters.')
            with db() as c:
                row=c.execute('SELECT * FROM admins LIMIT 1').fetchone()
                if not hmac.compare_digest(pw(str(body.get('current','')),row['salt']),row['hash']):return respond({'error':'Current password is incorrect.'},403)
                salt=secrets.token_hex(16);c.execute('UPDATE admins SET salt=?,hash=?',(salt,pw(password,salt)));c.execute('DELETE FROM sessions')
            return respond({'ok':True})
        if path in ('/api/book','/api/message') and method=='POST':
            if body.get('website'):return respond({'error':'Unable to submit.'},400)
            name=clean(body.get('name'),100);address=clean(body.get('email'),254)
            if not name or not email(address):raise ValueError('Enter your name and a valid email address.')
            with db() as c:
                if not limit(c,'submit:'+env.get('REMOTE_ADDR',''),8,3600):return respond({'error':'Too many requests. Please call the shop.'},429)
                if path=='/api/book':
                    service=clean(body.get('service'),100);day=clean(body.get('day'),10);clock=clean(body.get('time'),5);phone=clean(body.get('phone'),40)
                    if service not in [x['name'] for x in settings()['services']]:raise ValueError('Select an available service.')
                    try:dt=datetime.strptime(day+' '+clock,'%Y-%m-%d %H:%M').replace(tzinfo=TZ)
                    except ValueError:raise ValueError('Select a valid date and time.')
                    if dt<=datetime.now(TZ) or dt>datetime.now(TZ)+timedelta(days=180):raise ValueError('Choose a future time within 180 days.')
                    if not phone:raise ValueError('Enter a contact number.')
                    schedule=settings()['hours'][(dt.weekday()+1)%7]
                    matches=re.fullmatch(r'(\d{2}:\d{2})[–-](\d{2}:\d{2})',schedule)
                    if not matches or not matches[1]<=clock<matches[2]:raise ValueError('Choose a time during the displayed shop hours.')
                    rid=c.execute('INSERT INTO bookings(name,email,phone,service,day,time,created) VALUES(?,?,?,?,?,?,?)',(name,address,phone,service,day,clock,datetime.now(TZ).isoformat())).lastrowid;queue(c,'booking request',rid)
                else:
                    message=clean(body.get('message'),3000)
                    if not message:raise ValueError('Please enter a message.')
                    rid=c.execute('INSERT INTO messages(name,email,message,created) VALUES(?,?,?,?)',(name,address,message,datetime.now(TZ).isoformat())).lastrowid;queue(c,'chat message',rid)
            return respond({'ok':True,'reference':rid})
        if path=='/api/admin/dashboard':
            with db() as c:
                return respond({'settings':settings(),'employees':employees(),'bookings':[dict(r) for r in c.execute('SELECT * FROM bookings ORDER BY day DESC,time DESC')],'messages':[dict(r) for r in c.execute('SELECT * FROM messages ORDER BY id DESC')],'mail':{'configured':bool(os.environ.get('SMTP_HOST') and os.environ.get('SMTP_FROM')),'queued':c.execute('SELECT count(*) FROM outbox WHERE sent IS NULL').fetchone()[0],'failed':c.execute('SELECT count(*) FROM outbox WHERE sent IS NULL AND attempts>0').fetchone()[0]}})
        if path=='/api/admin/settings' and method=='POST':
            s=settings()
            for k in ('name','eyebrow','headline','intro','about','phone','email','address'):s[k]=clean(body.get(k,s[k]),3000 if k=='about' else 600)
            for k in ('facebook','setmore','hero_image'):
                v=clean(body.get(k,s[k]),2000)
                if v and not re.match(r'^https://[^\s]+$',v):raise ValueError(k+' must be an HTTPS URL.')
                s[k]=v
            col=body.get('accent',s['accent'])
            if not re.fullmatch('#[0-9a-fA-F]{6}',col):raise ValueError('Invalid accent colour.')
            s['accent']=col
            if 'recipients' in body:
                recipients=body['recipients']
                if not isinstance(recipients,list) or len(recipients)!=3:raise ValueError('Provide three email fields; blanks are allowed.')
                recipients=[clean(x,254) for x in recipients]
                if any(x and not email(x) for x in recipients):raise ValueError('Check the alert email addresses.')
                s['recipients']=list(dict.fromkeys(recipients));s['recipients']+=['']*(3-len(s['recipients']))
            if 'hours' in body:
                if not isinstance(body['hours'],list) or len(body['hours'])!=7:raise ValueError('Provide seven opening hours.')
                for h in body['hours']:
                    if h.lower()=='closed':continue
                    match=re.fullmatch(r'([01]\d|2[0-3]):([0-5]\d)[–-]([01]\d|2[0-3]):([0-5]\d)',h)
                    if not match or h[:5]>=h[6:]:raise ValueError('Hours must be HH:MM–HH:MM or Closed.')
                s['hours']=body['hours']
            if 'services' in body:
                items=body['services']
                if not isinstance(items,list) or not 1<=len(items)<=20:raise ValueError('Add between 1 and 20 services.')
                s['services']=[]
                for item in items:
                    n=clean(item.get('name'),100);mins=int(item.get('minutes',30))
                    if not n or not 5<=mins<=240:raise ValueError('Service names and durations (5–240 minutes) are required.')
                    s['services'].append({'name':n,'minutes':mins,'description':clean(item.get('description'),300)})
            save_settings(s);return respond({'ok':True})
        if path=='/api/admin/word' and method=='POST':
            s=settings()
            try:s['doc_draft']=convert(raw,MEDIA)
            except Exception:raise ValueError('This document could not be imported. Use a valid .docx file with embedded PNG/JPEG/GIF/WebP images.')
            save_settings(s);return respond({'ok':True})
        if path=='/api/admin/word-preview':
            return respond(('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/style.css"><article class="word-page">'+settings()['doc_draft']+'</article>').encode(),mime='text/html; charset=utf-8')
        if path=='/api/admin/publish' and method=='POST':
            s=settings();mode=body.get('mode')
            if mode not in ('word','designed'):raise ValueError('Invalid page mode.')
            if mode=='word':
                if not s['doc_draft']:raise ValueError('Import a Word document first.')
                s['doc_live']=s['doc_draft']
            s['page_mode']=mode;save_settings(s);return respond({'ok':True})
        if path=='/api/admin/employee' and method=='POST':
            with db() as c:
                rid=int(body.get('id') or 0)
                if body.get('delete'):
                    c.execute('UPDATE bookings SET employee=NULL WHERE employee=?',(rid,));c.execute('DELETE FROM employees WHERE id=?',(rid,))
                else:
                    vals=[clean(body.get(k),n) for k,n in [('name',100),('role',100),('email',254),('phone',40),('bio',1000)]]+[int(bool(body.get('public')))]
                    if not vals[0]:raise ValueError('Employee name is required.')
                    if vals[2] and not email(vals[2]):raise ValueError('Employee email is invalid.')
                    if rid:c.execute('UPDATE employees SET name=?,role=?,email=?,phone=?,bio=?,public=? WHERE id=?',vals+[rid])
                    else:c.execute('INSERT INTO employees(name,role,email,phone,bio,public) VALUES(?,?,?,?,?,?)',vals)
            return respond({'ok':True})
        if path=='/api/admin/booking' and method=='POST':
            status=body.get('status');employee=int(body.get('employee') or 0) or None
            if status not in ('Requested','Confirmed','Completed','Cancelled'):raise ValueError('Invalid status.')
            with db() as c:
                if employee and not c.execute('SELECT id FROM employees WHERE id=?',(employee,)).fetchone():raise ValueError('Employee no longer exists.')
                c.execute('UPDATE bookings SET status=?,employee=? WHERE id=?',(status,employee,int(body['id'])))
            return respond({'ok':True})
        if path=='/api/admin/message' and method=='POST':
            with db() as c:c.execute('UPDATE messages SET status=? WHERE id=?',('Read' if body.get('read') else 'Unread',int(body['id'])))
            return respond({'ok':True})
        if path=='/api/admin/retry-mail' and method=='POST':
            with db() as c:c.execute('UPDATE outbox SET attempts=0,lease=0,error=\'\' WHERE sent IS NULL')
            return respond({'ok':True})
        if path=='/api/admin/export':
            out=io.StringIO();w=csv.writer(out);w.writerow(['Reference','Name','Email','Phone','Service','Date','Time (Surrey)','Status','Employee ID'])
            with db() as c:
                for r in c.execute('SELECT id,name,email,phone,service,day,time,status,employee FROM bookings ORDER BY day'):
                    w.writerow([("'"+str(x)) if str(x or '').startswith(('=','+','-','@','\t','\r')) else x for x in r])
            headers.append(('Content-Disposition','attachment; filename="suncity-bookings.csv"'));return respond(out.getvalue().encode('utf-8-sig'),mime='text/csv; charset=utf-8')
        if path.startswith('/api/'):return respond({'error':'Not found.'},404)
        if path.startswith('/media/'):
            name=path[7:]
            if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|gif|webp)',name):return respond({'error':'Not found.'},404)
            file=MEDIA/name
        else:
            names={'/':'index.html','/admin':'admin.html','/admin/':'admin.html','/style.css':'style.css','/site.js':'site.js','/admin.js':'admin.js','/eyewear.svg':'eyewear.svg'}
            if path not in names:return respond({'error':'Not found.'},404)
            file=BASE/'public'/names[path]
        if not file.is_file():return respond({'error':'Not found.'},404)
        return respond(file.read_bytes(),mime=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
    except (ValueError,KeyError,TypeError,OverflowError) as e:return respond({'error':str(e) if isinstance(e,ValueError) else 'Invalid request data.'},400)
    except Exception:
        traceback.print_exc();return respond({'error':'Request failed. Please try again or contact the shop.'},500)
def employees(public=False):
    with db() as c:
        rows=[dict(r) for r in c.execute('SELECT * FROM employees'+(' WHERE public=1' if public else '')+' ORDER BY name')]
        return [{k:r[k] for k in ('id','name','role','bio')} for r in rows] if public else rows
def save_settings(s):
    with db() as c:c.execute('UPDATE settings SET value=? WHERE id=1',(json.dumps(s),))
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='setup':
        import getpass
        username=input('Admin username: ').strip();password=getpass.getpass('Password (minimum 12 characters): ')
        if not username or len(username)>80 or not 12<=len(password)<=128:sys.exit('Invalid username or password length.')
        if password!=getpass.getpass('Confirm password: '):sys.exit('Passwords do not match.')
        salt=secrets.token_hex(16)
        with db() as c:c.execute('DELETE FROM admins');c.execute('INSERT INTO admins VALUES(?,?,?)',(username,salt,pw(password,salt)));c.execute('DELETE FROM sessions')
        print('Admin account ready. Any previous admin account was replaced.')
    elif len(sys.argv)>1 and sys.argv[1]=='mail':process_mail()
    else:
        from wsgiref.simple_server import make_server
        print('Development server: '+ORIGIN+' — use Gunicorn behind HTTPS for deployment.')
        make_server('127.0.0.1',8090,application).serve_forever()
