import argparse,sys
from data_tools import load_env_file,migrate
from persistence import StorageUnavailable
p=argparse.ArgumentParser(description='Copy existing Pi accounts and records into an EMPTY Supabase destination. Source remains unchanged.')
p.add_argument('--source',required=True,help='Folder containing site.sqlite3 and media/')
p.add_argument('--env',required=True,help='Private environment file with cloud credentials')
a=p.parse_args()
try:
    load_env_file(a.env);result=migrate(a.source)
except (ValueError,StorageUnavailable) as e:
    print('Migration stopped: '+str(e),file=sys.stderr);sys.exit(1)
except OSError:
    print('Migration stopped. Verify the source folder, empty destination, private bucket, PostgreSQL dependency and credentials. No source data was deleted.',file=sys.stderr);sys.exit(1)
print('Migration completed. Existing website password hashes were preserved. Source was not changed.')
for table,count in result['records'].items():print(table+': '+str(count))
print('Images: '+str(result['images']))
