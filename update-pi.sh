#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then echo 'Run: sudo bash update-pi.sh'; exit 1; fi
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_DIR=/var/www/html/suncityoptics
if [ ! -f "$TARGET_DIR/app.py" ] || [ ! -f "$TARGET_DIR/site.env" ]; then
    echo 'Existing web-root installation was not found. Nothing was replaced. For a new installation use install-pi.sh.'
    exit 1
fi
if [ ! -e /etc/apache2/conf-enabled/suncity-protect.conf ]; then
    echo 'The expected Apache protection configuration is missing. Nothing was replaced; check the existing installation first.'
    exit 1
fi
apt-get update
apt-get install -y python3 python3-psycopg gunicorn ca-certificates tzdata
BACKUP_DIR=/var/backups/suncityoptics
STAMP=$(date +%Y%m%d-%H%M%S)
install -d -m 700 "$BACKUP_DIR"
umask 077
tar -czf "$BACKUP_DIR/code-$STAMP.tar.gz" --exclude='./data' --exclude='./__pycache__' -C "$TARGET_DIR" .
if [ -f "$TARGET_DIR/data/site.sqlite3" ]; then
    python3 "$SOURCE_DIR/backup_local.py" --source "$TARGET_DIR/data" --output "$BACKUP_DIR/data-$STAMP.zip"
fi
python3 -m py_compile "$SOURCE_DIR/app.py" "$SOURCE_DIR/persistence.py" "$SOURCE_DIR/cloud_media.py" "$SOURCE_DIR/data_tools.py" "$SOURCE_DIR/mailer.py"
STOPPED=0
rollback_update() {
    RESULT=$?
    if [ "$RESULT" -ne 0 ] && [ "$STOPPED" -eq 1 ]; then
        tar -xzf "$BACKUP_DIR/code-$STAMP.tar.gz" -C "$TARGET_DIR" || true
        systemctl start suncity-optics suncity-mail.timer || true
        echo 'Update failed. Previous code was restored where possible; check the service status.'
    fi
}
trap rollback_update EXIT
systemctl stop suncity-mail.timer suncity-mail.service suncity-optics
STOPPED=1
# Preserve site.env, data/, the existing accounts and the family homepage.
for FILE in app.py docx_import.py persistence.py cloud_media.py data_tools.py mailer.py migrate_to_supabase.py backup_local.py admin.html admin.js index.html style.css site.js eyewear.svg requirements.txt README.md CLOUD_SETUP.md; do
    cp "$SOURCE_DIR/$FILE" "$TARGET_DIR/$FILE"
    chown root:www-data "$TARGET_DIR/$FILE"
    chmod 640 "$TARGET_DIR/$FILE"
done
cp "$SOURCE_DIR/deploy/cloud.env.example" "$TARGET_DIR/deploy/cloud.env.example"
python3 -m py_compile "$TARGET_DIR/app.py" "$TARGET_DIR/persistence.py" "$TARGET_DIR/cloud_media.py" "$TARGET_DIR/data_tools.py" "$TARGET_DIR/mailer.py"
systemctl start suncity-optics suncity-mail.timer
STOPPED=0
echo 'Updated. Existing accounts, data and site.env were preserved.'
echo 'Private rollback backups: /var/backups/suncityoptics/'
echo 'The Pi still uses its existing storage mode. Follow CLOUD_SETUP.md to migrate.'
