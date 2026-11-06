#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run with sudo: sudo bash install-pi.sh'
    exit 1
fi
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_DIR=/var/www/html/suncityoptics
if [ -e "$TARGET_DIR" ] || [ -e /opt/suncity-optics ] || [ -e /etc/systemd/system/suncity-optics.service ]; then
    echo 'An optical-site folder or service already exists. Nothing was overwritten.'
    echo 'Keep your records. Share this message so we can migrate the existing installation.'
    exit 1
fi
if [ ! -f "$SOURCE_DIR/../suncityoptics.html" ]; then
    echo 'Keep the extracted ZIP structure: suncityoptics.html beside the suncityoptics folder.'
    exit 1
fi
if ! command -v apache2ctl >/dev/null 2>&1; then
    echo 'Apache was not found. This installer is for your Pi with the existing Apache family site.'
    exit 1
fi
for SUNCITY_PORT in 8081 8090; do
    if [ -n "$(ss -H -ltn "sport = :$SUNCITY_PORT")" ]; then
        echo "Port $SUNCITY_PORT is already in use. Nothing was overwritten. Share this output before continuing."
        exit 1
    fi
done
if [ -e /etc/apache2/sites-available/suncity-8081.conf ] || [ -e /etc/apache2/conf-available/suncity-protect.conf ]; then
    echo 'An optical-site Apache configuration already exists. Keep it and share this output before continuing.'
    exit 1
fi
printf 'Website origin [http://192.168.0.120:8081]: '
read -r SUNCITY_ORIGIN
SUNCITY_ORIGIN=${SUNCITY_ORIGIN:-http://192.168.0.120:8081}
if ! /usr/bin/python3 - "$SUNCITY_ORIGIN" <<'PY'
import sys, urllib.parse
s=sys.argv[1];p=urllib.parse.urlsplit(s)
try:
    valid=(p.scheme=='http' and bool(p.hostname) and p.port==8081 and p.path in ('','/') and not p.query and not p.fragment and not p.username and not any(c.isspace() or c in '"\'\\' for c in s))
except ValueError:valid=False
if not valid:sys.exit(1)
PY
then
    echo 'Enter an origin such as http://192.168.0.120:8081, without a folder or filename.'
    exit 1
fi
apt-get update
apt-get install -y python3 python3-psycopg gunicorn ca-certificates tzdata
# Deny direct Apache access BEFORE any private application files enter the web root.
cp "$SOURCE_DIR/deploy/suncity-protect.conf" /etc/apache2/conf-available/suncity-protect.conf
a2enconf suncity-protect
apache2ctl configtest
systemctl reload apache2
install -d -m 750 -o root -g www-data "$TARGET_DIR"
cp -R "$SOURCE_DIR/." "$TARGET_DIR/"
chown -R root:www-data "$TARGET_DIR"
chmod 750 "$TARGET_DIR"
install -d -m 700 -o www-data -g www-data "$TARGET_DIR/data"
cp "$TARGET_DIR/deploy/site.env.example" "$TARGET_DIR/site.env"
/usr/bin/python3 - "$SUNCITY_ORIGIN" <<'PY'
from pathlib import Path
import sys
p=Path('/var/www/html/suncityoptics/site.env');p.write_text(p.read_text().replace('http://192.168.0.120:8081',sys.argv[1].rstrip('/')))
PY
chown root:www-data "$TARGET_DIR/site.env"
chmod 640 "$TARGET_DIR/site.env"
# If a previous root shortcut exists, retain it inside the protected app folder.
if [ -e /var/www/html/suncityoptics.html ]; then
    install -d -m 750 "$TARGET_DIR/install-backups"
    cp -p /var/www/html/suncityoptics.html "$TARGET_DIR/install-backups/suncityoptics.html"
fi
cp "$SOURCE_DIR/../suncityoptics.html" /var/www/html/suncityoptics.html
chmod 644 /var/www/html/suncityoptics.html
runuser -u www-data -- env SUNCITY_DATA="$TARGET_DIR/data" /usr/bin/python3 "$TARGET_DIR/app.py" setup
cp "$TARGET_DIR/deploy/suncity-optics.service" "$TARGET_DIR/deploy/suncity-mail.service" "$TARGET_DIR/deploy/suncity-mail.timer" /etc/systemd/system/
a2enmod proxy proxy_http
cp "$TARGET_DIR/deploy/suncity-8081.conf" /etc/apache2/sites-available/suncity-8081.conf
a2ensite suncity-8081
apache2ctl configtest
systemctl daemon-reload
systemctl enable --now suncity-optics.service suncity-mail.timer
systemctl reload apache2
printf '\nInstalled. Your family index.html was not modified.\n'
printf 'Shop: %s/suncityoptics/index.html\n' "$SUNCITY_ORIGIN"
printf 'Admin: %s/suncityoptics/admin\n' "$SUNCITY_ORIGIN"
printf 'Root shortcut: open /suncityoptics.html on your existing family website.\n'
