# Keep your Pi logins and make Render records durable

The server can use either local SQLite/files on your Pi, or Supabase PostgreSQL/private object storage. It never silently switches to local storage when a cloud operation fails.

**Your current Pi site password stays private.** It is stored as a salted password hash in `data/site.sqlite3`, not in `app.py`. The migration copies those hashes directly. There is no need to send or embed any plaintext site password.

## 1. Update your existing Pi installation

Use WinSCP to upload the new `Sun_City_Optics_Website.zip` to your Pi user's home directory. In PuTTY:

```bash
cd ~
unzip -o Sun_City_Optics_Website.zip -d suncity-cloud-update
cd ~/suncity-cloud-update/suncityoptics
sudo bash update-pi.sh
```

This is an **update**, not a reinstall. It preserves `/var/www/html/suncityoptics/site.env`, your `data/` folder and the family homepage. It creates private rollback backups under `/var/backups/suncityoptics/`. Do not run `install-pi.sh` or `app.py setup` on the existing installation; setup replaces sign-in accounts. The update leaves the Pi's existing local storage mode unchanged.

The script checks for the expected existing web-root installation and Apache protection. If it stops because they are missing, retain the existing files and share the non-secret message rather than deleting your database.

Open the Pi's admin, sign in with the existing username/password, and verify normal operation after the update. The Overview page now includes **Download private backup** and **Check cloud connection**.

## 2. Create the Supabase project

1. Open https://supabase.com/dashboard and create a new project on the Free plan.
2. Choose a region suitable for the shop and a strong **database password**. This is a separate credential from your website admin password.
3. In Storage, create a bucket named `suncity-media`. Leave **Public bucket OFF**. No public read/write policies are required; the website's server key accesses the private bucket.
4. Click **Connect**, choose **Session pooler**, and copy the PostgreSQL connection URI. The session pooler supports IPv4 and is appropriate for the Pi/Render connection. Use port 5432 as shown by Supabase. Replace the database password placeholder with your password; URI-encode reserved characters in the password (`@`, `:`, `/`, `#`, `%`, and so on).
5. Copy the project URL, such as `https://PROJECT_REF.supabase.co`.
6. Under the project's API keys, create/copy a **server secret key** (`sb_secret_...`). The legacy `service_role` key is also supported. An `anon` or publishable key is not suitable for this server-side integration.

Use credentials from the **same Supabase project** for the database and image bucket. Never put the database URI or server secret key in HTML, JavaScript or GitHub. The server uses verified TLS. If Supabase supplies a project-specific CA certificate, save that certificate on the server and set `PGSSLROOTCERT` to its path; do not disable certificate verification.

The app creates a private `suncity` PostgreSQL schema on first connection. It does not put your accounts or bookings in the public Data API schema and does not use Supabase Auth; it retains your existing website login system. The optional `deploy/supabase_schema.sql` shows the schema and can be run in SQL Editor if your connection user needs initialization beforehand. Do not expose the `suncity` schema through the browser Data API or grant browser roles access.

## 3. Migrate the existing Pi records BEFORE enabling cloud mode in Render

This operation imports into an **empty destination**. If a cloud account, audit log, booking or other app record already exists, the tool refuses to overwrite it. Initialize/migrate first, then deploy Render against that populated destination. This avoids creating a temporary Render admin that would conflict with the Pi accounts.

Create a private configuration file on the Pi:

```bash
sudo nano /var/www/html/suncityoptics/cloud.env
```

Paste your values, one per line. Do not paste them into chat:

```ini
STORAGE_MODE=supabase
DATABASE_URL=postgresql://postgres.PROJECT_REF:URL_ENCODED_DATABASE_PASSWORD@YOUR_SESSION_POOLER_HOST:5432/postgres
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_SECRET_KEY=YOUR_PRIVATE_SERVER_KEY
SUPABASE_BUCKET=suncity-media
```

The exact database host and username come from Supabase's Session pooler connection URI. Save with Ctrl+O, Enter, then Ctrl+X. Protect the file:

```bash
sudo chown root:www-data /var/www/html/suncityoptics/cloud.env
sudo chmod 640 /var/www/html/suncityoptics/cloud.env
```

Prevent new records while making the final migration, then run it:

```bash
sudo systemctl stop suncity-optics suncity-mail.timer suncity-mail.service
sudo python3 /var/www/html/suncityoptics/migrate_to_supabase.py --source /var/www/html/suncityoptics/data --env /var/www/html/suncityoptics/cloud.env
```

Success prints counts only, never passwords. Copied data includes accounts and roles, password hashes, settings and notification recipients, staff profiles, bookings, messages, outbox state, change history and images referenced by Word drafts/live pages. Active sessions and rate limits are not copied; sign in again afterward. SMTP/API credentials from `site.env` are not imported and must be configured separately on each server. External hero-image URLs remain URLs. Unreferenced old image files and the original Word documents are not part of the live page migration.

The original Pi database and images are not modified or deleted. If migration fails, check the safe error text, database settings, private bucket, missing source images or destination-emptiness requirement. Uploads use content hashes, so a failed attempt can leave unused image objects but does not commit partial records; fix the error and retry. Do not delete a cloud database that may contain real data merely to bypass the guard.

If you need to resume the Pi's **local** site while investigating a failed migration:

```bash
sudo systemctl start suncity-optics suncity-mail.timer
```

A successful migration is a point-in-time copy. Writes to the old local database after migration are not automatically copied to Supabase. Choose one authoritative live site, or configure both Pi and Render to use the same Supabase destination as described below.

## 4. Reapply the full code to GitHub and deploy Render

In the extracted ZIP, open `suncityoptics`. Upload its **contents** to the same GitHub location as your existing `app.py` and `Dockerfile`, replacing the corresponding code files and preserving subfolders. Include `persistence.py`, `cloud_media.py`, `data_tools.py`, `mailer.py`, `docx_import.py` and the new Dockerfile. Do not upload the ZIP itself, a runtime `data/` folder, `site.env`, `cloud.env`, backups, passwords, database URIs or API keys. The example environment files contain placeholders only. The Pi-only root shortcut `suncityoptics.html` does not need uploading to Render.

The updated backend serves the root asset files first and also supports the earlier `public/` layout. Its nested `/suncityoptics/...` routes work on both hosts. The first-login screen fix and public form session-check fix are included.

In Render, keep **Language: Docker** and your chosen Free instance. Set these environment variables:

| Key | Value |
| --- | --- |
| `STORAGE_MODE` | `supabase` |
| `DATABASE_URL` | Your private Session pooler PostgreSQL URI |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SECRET_KEY` | Your private server secret key |
| `SUPABASE_BUCKET` | `suncity-media` |
| `SUNCITY_DATA` | `/data` (temporary work directory; authoritative records/images are in Supabase) |
| `PORT` | `8090` |
| `MAIL_AUTORUN` | `1` if using email alerts |

Remove the old `IS_FREE_PREVIEW=1` setting or leave it; the new app will correctly identify durable cloud mode. Remove old `ADMIN_USERNAME` and `ADMIN_PASSWORD` bootstrap values when migrating existing Pi accounts. You will use those existing accounts, not a newly embedded account.

Remove an incorrect/example `PUBLIC_ORIGIN` value. The app uses Render's automatic `RENDER_EXTERNAL_URL`. If using a custom domain, set `PUBLIC_ORIGIN` to that exact HTTPS origin without a path or trailing slash. Keep `PGSSLROOTCERT` only if you actually provided a suitable server CA file at that path.

Commit the code changes. Select **Save, rebuild, and deploy** or **Manual Deploy → Deploy latest commit**. Use the new Dockerfile so the required PostgreSQL driver is installed. Changing only `app.py` is insufficient for this update.

After deployment, open the Render site and sign in with your **existing Pi username and password**. Do not run a reset command to make this work. Overview should report **Supabase cloud storage**. Click **Check cloud connection** and verify both the database and the private image bucket.

## 5. Optional: use the SAME cloud records on the Pi

Only do this after the migration succeeds. Keep the existing local `data/` folder as a rollback copy. In PuTTY:

```bash
sudo nano /var/www/html/suncityoptics/site.env
```

Add the five cloud settings from your private `cloud.env` file. Keep the Pi's existing `PUBLIC_ORIGIN=http://192.168.0.120:8081`, its local `SUNCITY_DATA=/var/www/html/suncityoptics/data`, and any email sender settings. Set `MAIL_AUTORUN=0` on the Pi when its systemd mail timer is enabled. Then:

```bash
sudo systemctl start suncity-optics suncity-mail.timer
sudo systemctl restart suncity-optics
```

Pi and Render now read/write the same cloud database and images. You can use both URLs with the same accounts. Each host keeps its own configured origin for request validation. Email alerts use the origin of whichever worker delivers them. If both hosts run mail workers, database leases prevent normal concurrent duplicate claims; SMTP remains at-least-once delivery in a crash, as with most queued email.

If you leave the Pi in local mode instead, it remains a separate independent copy. It will not synchronize future changes with Render. To roll back to local mode, remove the five cloud settings and restart; remember that the local copy does not contain newer cloud records.

## 6. Email alerts on Render Free

Render Free blocks the normal SMTP ports. Supabase data storage does not remove that restriction. This update includes an optional HTTPS sender using Resend:

1. Create your provider account at https://resend.com and follow its sender-domain verification requirements.
2. Create an email-sending API key.
3. In Render Environment, set `RESEND_API_KEY` and `MAIL_FROM` to your authorized sender address, and `MAIL_AUTORUN=1`.
4. In the website admin, save up to three recipient addresses under Email & security.
5. Submit a test request and check all three inboxes and the dashboard's mail queue/error counts.

The provider's test sender may restrict recipients; a verified sender domain is needed to deliver to arbitrary recipients. Provider plans, quotas and domain costs are separate. No email account or domain has been created for you. SMTP remains available on your Pi if its network/provider permits it. Choose one mail mechanism per host; the HTTPS key takes priority when configured.

The web app starts a mail queue worker per process when `MAIL_AUTORUN=1`. It runs while the service is awake, every minute. Render can sleep; queued records remain in Supabase and delivery resumes on wake. This does not guarantee immediate notifications during idle spin-down. Failed alerts are retained and can be retried from admin.

## 7. Backups and final checks

In admin Overview, choose **Download private backup**. This exports all application record tables plus images referenced by the Word pages, up to 32 MB uncompressed. It excludes active sessions, rate limits and environment secrets. The archive includes customer records and password hashes: store it in a private file repository, not a public GitHub repository or unprotected web folder. It is a portable backup export; this version does not provide a browser-based restore button. Larger datasets should use database-provider exports plus separate bucket backups.

A local Pi backup is also available without cloud credentials:

```bash
sudo python3 /var/www/html/suncityoptics/backup_local.py --source /var/www/html/suncityoptics/data --output /var/backups/suncityoptics/manual-backup.zip
```

Choose a new output filename each time; existing backups are never overwritten. Cloud storage is live persistence, not a substitute for a separate backup.

Before accepting real customers:

- Confirm your existing username/password works in Render.
- Check the database and private bucket from the Overview button.
- Create a sample booking and message while signed into admin; both must succeed.
- Import/publish a sample Word page with an image and open its link.
- Redeploy Render and verify accounts, bookings, content and the image remain.
- Verify staff permissions, one logged change under that staff username, and a private backup download.
- If enabling email, test actual delivery to each configured recipient.

Supabase Free currently offers 500 MB database and 1 GB file storage, with usage limits and pausing after one week of inactivity. Render's web service can still sleep. External records are not tied to Render's disposable filesystem once configured, but provider limits, pauses and outages can make the site unavailable. The app returns an error instead of claiming a cloud save succeeded when it did not.

## Verification limits and references

The local feature tests, account/hash migration checks and simulated cloud/error tests pass. JavaScript and installer syntax are checked. A live Supabase/PostgreSQL connection, real Storage requests, actual sender delivery and execution on your Pi were not verified here: your project credentials are not present, and this build environment could not install the PostgreSQL test runtime. The supplied driver is installed by the deployment Dockerfile/Pi updater. Complete the checks above on your deployment.

Official references: https://supabase.com/docs/guides/database/connecting-to-postgres, https://supabase.com/docs/guides/getting-started/api-keys, https://supabase.com/docs/guides/storage, https://supabase.com/pricing, https://render.com/docs/free, https://render.com/docs/configure-environment-variables, https://resend.com/docs/api-reference/emails/send-email.
