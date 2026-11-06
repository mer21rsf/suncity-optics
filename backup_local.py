import argparse,io,json,zipfile,os
from pathlib import Path
from datetime import datetime
from data_tools import sqlite_records,referenced_images,MAX_BACKUP
p=argparse.ArgumentParser(description='Create a PRIVATE backup without uploading credentials anywhere.')
p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
records=sqlite_records(a.source);source=Path(a.source);output=Path(a.output)
if output.exists():raise SystemExit('Output already exists. Choose a new filename.')
# Opening with mode x prevents overwriting any existing backup.
fd=os.open(str(output),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as file:
    with zipfile.ZipFile(file,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('records.json',json.dumps({'format':'suncity-backup','version':1,'created':datetime.now().isoformat(),'tables':records}))
        for name in referenced_images(records):z.write(source/'media'/name,'media/'+name)
        z.writestr('README.txt','PRIVATE: customer records and password hashes. No server environment credentials or active sessions included. Keep this outside your web root and source repository.')
print('Private backup created at the output path you specified.')
