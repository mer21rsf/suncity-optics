#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then
  echo 'Run with sudo: sudo bash install-pi.sh'
  exit 1
fi
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -e /opt/suncity-optics ]; then
  echo '/opt/suncity-optics already exists. See the README update instructions; this installer will not overwrite it.'
  exit 1
fi
printf 'Full website origin (for example https://optics.example.com, without trailing slash): '
read -r SUNCITY_ORIGIN
case "$SUNCITY_ORIGIN" in
  http://*|https://*) ;;
  *) echo 'Enter a full http:// or https:// URL.'; exit 1 ;;
esac
if ! /usr/bin/python3 - "$SUNCITY_ORIGIN" <<'PY'
import sys,urllib.parse
s=sys.argv[1];p=urllib.parse.urlsplit(s)
if not p.hostname or p.path not in ('','/') or p.query or p.fragment or p.username or any(c.isspace() or c in '"\'\\' for c in s):sys.exit(1)
PY
then echo 'Enter an origin only, with no path, spaces, or credentials.'; exit 1; fi
apt-get update
apt-get install -y python3 gunicorn ca-certificates tzdata
install -d -m 755 /opt/suncity-optics
cp "$SOURCE_DIR/app.py" "$SOURCE_DIR/docx_import.py" /opt/suncity-optics/
cp -R "$SOURCE_DIR/public" /opt/suncity-optics/
install -d -o www-data -g www-data -m 700 /var/lib/suncity-optics
if [ ! -e /etc/suncity-optics.env ]; then
  cp "$SOURCE_DIR/deploy/site.env.example" /etc/suncity-optics.env
  /usr/bin/python3 - "$SUNCITY_ORIGIN" <<'PY'
from pathlib import Path
import sys
p=Path('/etc/suncity-optics.env');p.write_text(p.read_text().replace('https://optics.example.com',sys.argv[1].rstrip('/')))
PY
  chown root:www-data /etc/suncity-optics.env
  chmod 640 /etc/suncity-optics.env
fi
runuser -u www-data -- env SUNCITY_DATA=/var/lib/suncity-optics /usr/bin/python3 /opt/suncity-optics/app.py setup
cp "$SOURCE_DIR/deploy/suncity-optics.service" "$SOURCE_DIR/deploy/suncity-mail.service" "$SOURCE_DIR/deploy/suncity-mail.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now suncity-optics.service suncity-mail.timer
echo 'Installed. Configure the Apache reverse proxy and SMTP using README.md.'
echo 'The app listens on 127.0.0.1:8090; existing Apache websites were not changed.'
