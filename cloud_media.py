"""Content-addressed images: private Supabase bucket, served through the website."""
import os,re,mimetypes,json
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import quote,urlsplit
from persistence import cloud_enabled,StorageUnavailable
IMAGE=re.compile(r'[0-9a-f]{64}\.(png|jpg|gif|webp)')
class MediaStore:
    def __init__(self,path):self.path=path
    def __truediv__(self,name):
        if not IMAGE.fullmatch(name):raise ValueError('Invalid image name.')
        return MediaObject(self,name)
    def config(self):
        base=os.environ.get('SUPABASE_URL','').rstrip('/');key=os.environ.get('SUPABASE_SECRET_KEY','');bucket=os.environ.get('SUPABASE_BUCKET','suncity-media')
        if not base.startswith('https://') or urlsplit(base).path or not key or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',bucket):raise StorageUnavailable('Cloud images require SUPABASE_URL, SUPABASE_SECRET_KEY and a private SUPABASE_BUCKET.')
        return base,key,bucket
    def request(self,method,route,data=None,mime=None):
        base,key,bucket=self.config();headers={'apikey':key,'User-Agent':'SunCityOptics/3'}
        # New sb_secret keys go in apikey only. Legacy service_role JWTs also use Bearer.
        if key.count('.')==2:headers['Authorization']='Bearer '+key
        if mime:headers['Content-Type']=mime;headers['x-upsert']='true'
        req=Request(base+'/storage/v1/'+route.format(bucket=quote(bucket,safe='')),data=data,headers=headers,method=method)
        try:
            with urlopen(req,timeout=25) as r:
                body=r.read(8*1024*1024+1)
                if len(body)>8*1024*1024:raise StorageUnavailable('Cloud image exceeds the supported size.')
                return body
        except HTTPError as e:
            if e.code==404 and method=='GET' and route.startswith('object/'):raise FileNotFoundError('Image not found.') from None
            raise StorageUnavailable('Cloud image request failed. Check the private bucket, server key and storage quota.') from None
        except (URLError,TimeoutError,OSError):raise StorageUnavailable('Cloud image service is unavailable. No local fallback was used.') from None
    def check(self):
        if not cloud_enabled():return 'Local files'
        value=json.loads(self.request('GET','bucket/{bucket}'))
        if value.get('public'):raise StorageUnavailable('Use a PRIVATE Supabase bucket for this application.')
        return 'Private bucket available'
class MediaObject:
    def __init__(self,store,name):self.store=store;self.name=name
    def write_bytes(self,data):
        if cloud_enabled():
            self.store.request('POST','object/{bucket}/'+self.name,data,mimetypes.guess_type(self.name)[0] or 'application/octet-stream')
        else:(self.store.path/self.name).write_bytes(data)
        return len(data)
    def read_bytes(self):
        if cloud_enabled():return self.store.request('GET','object/authenticated/{bucket}/'+self.name)
        return (self.store.path/self.name).read_bytes()
