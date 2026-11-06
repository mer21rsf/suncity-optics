"""One shared shop calendar. All intervals are [start, end), in Surrey local time."""
import re,calendar
from datetime import datetime,date,time,timedelta
from zoneinfo import ZoneInfo
TZ=ZoneInfo('America/Vancouver')
ACTIVE=('Requested','Confirmed','Completed')
STEP=15
HORIZON=180
class SlotConflict(ValueError):pass

def clock_minutes(clock,allow_end=False):
    if allow_end and clock=='24:00':return 1440
    if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',str(clock)):raise ValueError('Choose a valid time.')
    hour,minute=map(int,clock.split(':'));return hour*60+minute

def clock_text(value):return f'{value//60:02d}:{value%60:02d}'

def parse_day(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(value)):raise ValueError('Choose a valid date.')
    try:return date.fromisoformat(value)
    except ValueError:raise ValueError('Choose a valid date.') from None

def service_minutes(settings,name):
    services=[s for s in settings['services'] if s['name']==name]
    if not services:raise ValueError('Select an available service.')
    return int(services[0]['minutes'])

def hours_for(settings,day):
    value=settings['hours'][(day.weekday()+1)%7].strip()
    if value.lower()=='closed':return None
    parts=re.split('[–-]',value)
    if len(parts)!=2:return None
    start,end=map(clock_minutes,parts)
    return (start,end) if start<end else None

def intervals(c,day,exclude=None):
    result=[]
    for row in c.execute('SELECT id,time,minutes,status FROM bookings WHERE day=?',(day,)):
        row=dict(row)
        if row['status'] not in ACTIVE or row['id']==exclude:continue
        start=clock_minutes(row['time']);length=int(row.get('minutes') or 60)
        result.append((start,start+length,'Booked'))
    for row in c.execute('SELECT start_time,end_time FROM booking_blocks WHERE day=?',(day,)):
        result.append((clock_minutes(row['start_time']),clock_minutes(row['end_time'],True),'Unavailable'))
    return result

def overlaps(start,end,existing):return any(start<right and end>left for left,right,*_ in existing)

def validate_slot(c,settings,service,day_text,clock,now=None,exclude=None,minutes=None,require_future=True):
    day=parse_day(day_text);now=now or datetime.now(TZ)
    duration=service_minutes(settings,service) if minutes is None else int(minutes)
    start=clock_minutes(clock);end=start+duration
    hours=hours_for(settings,day)
    if not hours:raise ValueError('The shop is closed on that date.')
    if start<hours[0] or end>hours[1]:raise ValueError('The entire appointment must fit between opening and closing time.')
    if (start-hours[0])%STEP:raise ValueError('Choose a time from the available calendar slots.')
    local=datetime.combine(day,time(start//60,start%60),TZ)
    if require_future and (local<=now or day>now.date()+timedelta(days=HORIZON)):raise ValueError('Choose an available future date within 180 days.')
    if overlaps(start,end,intervals(c,day_text,exclude)):raise SlotConflict('That time is no longer available. Choose another calendar slot.')
    return duration

def month_availability(c,settings,service,month=None,now=None):
    now=now or datetime.now(TZ);month=month or now.strftime('%Y-%m')
    if not re.fullmatch(r'\d{4}-\d{2}',month):raise ValueError('Choose a valid calendar month.')
    try:first=date.fromisoformat(month+'-01')
    except ValueError:raise ValueError('Choose a valid calendar month.') from None
    last=first.replace(day=calendar.monthrange(first.year,first.month)[1]);maximum=now.date()+timedelta(days=HORIZON)
    if last<now.date() or first>maximum:raise ValueError('Choose a month within the next 180 days.')
    duration=service_minutes(settings,service)
    occupied={}
    for row in c.execute('SELECT id,day,time,minutes,status FROM bookings WHERE day>=? AND day<=?',(first.isoformat(),last.isoformat())):
        r=dict(row)
        if r['status'] in ACTIVE:
            start=clock_minutes(r['time']);occupied.setdefault(r['day'],[]).append((start,start+int(r.get('minutes') or 60),'Booked'))
    for row in c.execute('SELECT day,start_time,end_time FROM booking_blocks WHERE day>=? AND day<=?',(first.isoformat(),last.isoformat())):
        r=dict(row);occupied.setdefault(r['day'],[]).append((clock_minutes(r['start_time']),clock_minutes(r['end_time'],True),'Unavailable'))
    days=[]
    for n in range(1,last.day+1):
        day=first.replace(day=n);key=day.isoformat();hours=hours_for(settings,day);slots=[];state='closed'
        if day<now.date() or day>maximum:state='past'
        elif hours:
            for start in range(hours[0],hours[1]-duration+1,STEP):
                end=start+duration;local=datetime.combine(day,time(start//60,start%60),TZ)
                reason='Passed' if local<=now else next((reason for left,right,reason in occupied.get(key,[]) if start<right and end>left),'')
                slots.append({'time':clock_text(start),'end':clock_text(end),'available':not reason,'reason':reason})
            state='available' if any(s['available'] for s in slots) else 'full'
        days.append({'day':key,'state':state,'opening':clock_text(hours[0]) if hours else None,'closing':clock_text(hours[1]) if hours else None,'slots':slots})
    return {'month':month,'today':now.date().isoformat(),'max_date':maximum.isoformat(),'timezone':'America/Vancouver','service':service,'minutes':duration,'step':STEP,'days':days}

def booking_issues(bookings,settings):
    issues=[];active=[dict(b) for b in bookings if b['status'] in ACTIVE]
    for i,row in enumerate(active):
        try:
            day=parse_day(row['day']);hours=hours_for(settings,day);start=clock_minutes(row['time']);end=start+int(row.get('minutes') or 60)
            if not hours or start<hours[0] or end>hours[1]:issues.append({'type':'outside_hours','day':row['day'],'ids':[row['id']]})
            for other in active[i+1:]:
                if other['day']!=row['day']:continue
                left=clock_minutes(other['time']);right=left+int(other.get('minutes') or 60)
                if start<right and end>left:issues.append({'type':'overlap','day':row['day'],'ids':[row['id'],other['id']]})
        except ValueError:issues.append({'type':'invalid_legacy_date','day':row['day'],'ids':[row['id']]})
    return issues
