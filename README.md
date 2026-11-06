# Sun City Optics — website & staff studio

A responsive ivory / forest-green website for the Surrey optical shop, prepared by Mervin's request. Includes a complete Python + SQLite backend, without Node.js or PHP. Compatible with Raspberry Pi OS Bookworm, including 32-bit userspace. This package has not been installed on your Pi or connected to the shop's email account.


## NEW: Render Free preview, individual accounts and change history

This update adds account roles, forced first-login password changes, and an application activity history. It can initialize an administrator through Render Environment settings; no Render Shell is required.

### Replace the files in GitHub

Extract this ZIP. In your GitHub repository, upload the contents of the included `suncity-optics` folder at the same level as your existing `app.py`, preserving `public/`, `deploy/` and `tests/` paths. Replace existing files and commit. Do not upload the ZIP as a source file. This updates your original package; it is not a separate application.

### Render Free setup

Use a **Web Service**, Language **Docker**, and the **Free** compute plan. Do not add a disk; disks require paid hosting. Set these variables in the service's **Environment** page:

| Key | Value |
| --- | --- |
| `ADMIN_USERNAME` | `tempadmin` |
| `ADMIN_PASSWORD` | A private temporary password you choose, 12–128 characters |
| `IS_FREE_PREVIEW` | `1` |
| `SUNCITY_DATA` | `/data` |
| `PORT` | `8090` |

No temporary password is included in this ZIP. Enter it directly in Render, not in GitHub files, screenshots or chat. Keep these bootstrap variables while testing so a fresh database can recreate your initial login.

Remove an old or example `PUBLIC_ORIGIN` value to let this version use Render's automatic `RENDER_EXTERNAL_URL`. If you use a custom domain, set `PUBLIC_ORIGIN` to that exact HTTPS origin with no path or trailing slash. Then choose **Save, rebuild, and deploy** and wait until the new version is live. (If GitHub auto-deploy already ran, saving and deploying the current build is sufficient.)

Open the site → **Staff admin** at the bottom → sign in as `tempadmin` with your chosen temporary password. The first screen requires changing it. After saving, sign in again with the new password.

The environment credentials only create an account when the accounts table is empty. They do not overwrite an existing account or change a saved password. Changing `ADMIN_PASSWORD` is not a password reset for an existing database. On the free plan, a reset of local storage recreates the initial environment login, with another mandatory password change. A normal in-app password change does not modify the Render environment value.

### Create individual employee logins

As an admin, open **Login accounts**. Enter the person's name, a unique username (letters, numbers, `.`, `_`, `@` or `-`), their access role and a temporary password of at least 12 characters. Share credentials privately. Each new or reset account must change its password before accessing shop data.

| Role | Access |
| --- | --- |
| Admin | Shop features, notification recipients, user account management and activity history |
| Staff | Website editing, Word publishing, bookings, employee profiles and messages; can change their own password |

Employee public profiles and sign-in accounts are separate. An account's display name identifies the person, while the audit history records their unique username. Give each person their own account. You can edit roles, disable accounts, or reset another account's temporary password. There is no account deletion button, preserving attribution in history. Permission changes and password resets revoke that account's sessions. Your own password can only be changed with your current password. The app prevents disabling/demoting your own admin account or removing the last enabled administrator.

You may create a personal admin account, sign in with it and then disable `tempadmin`. On a free-plan storage reset, the environment account will be recreated because all saved accounts will have disappeared.

### Review who changed what

Open **Change history** as an admin. It shows the newest 500 entries and supports filtering by account, action or details. Logged actions include sign-in/out, password changes (never the password), account changes, website setting edits, Word imports/publication, employee record changes, booking status/assignment updates, message read status, alert retries and CSV exports. Public website settings include shortened before/after values. Employee email/phone edits record that the field changed, without copying contact values into the log. Word imports record the action and document size, not a full copy of the document. Raw database access is outside this application log; the log is not independently tamper-proof.

### Free-plan limitations

Render Free loses local database contents and images on restarts, redeployments and idle spin-down. This includes accounts, new passwords, bookings, messages, employee records, Word pages and change history. It is a demonstration, not durable storage for real customers. The preview banner reminds admins of this. Original code and artwork remain in GitHub.

Render Free also blocks SMTP ports 25, 465 and 587. The SMTP alerts supplied with this package cannot deliver on this plan. The dashboard and message inbox still work while the instance is running. An HTTPS email-provider integration and external database/image storage would require additional development; this update does not add those services. For durable operation, use paid hosting with a persistent disk or your Pi, and configure email delivery plus the mail worker.

Official references checked 6 November 2026: https://render.com/docs/free, https://render.com/docs/configure-environment-variables, https://render.com/docs/environment-variables.

## What is included

- A public homepage with six editable services, opening hours, contact information, directions, Facebook and Setmore links, and optional public team introductions.
- A footer-only **Staff admin** link. Real server-side login protects private records; the position of the link is not the security mechanism.
- Admin username/password set during installation, with no shared default password. Password changes and server-side password resets are supported.
- Website editing: headlines, story, contact details, image URL, accent colour, services and hours.
- **Microsoft Word import**: upload `.docx` → preview draft → publish as main content. Switch back to the built-in homepage at any time.
- Booking **requests**, status tracking, employee assignment, searching, filtering and CSV export. Shop staff must contact customers and confirm availability. Requests may overlap; this is not a real-time availability calendar.
- Employee records: name, role, email, phone, introduction and optional public visibility. Contact details stay private. Employee profiles are separate from the individual sign-in accounts managed under Login accounts.
- A chatbox fixed in the **bottom-right**, with current shop information and a message form. Staff messages appear in the admin inbox. The FAQ helper is not AI or live chat; staff reply by email.
- Up to **three notification email addresses**, configurable in admin. SMTP sends short alerts with a dashboard link, without customer details. Sending credentials remain on the server. The Pi installer runs the mail worker every minute.

## First install on your Raspberry Pi

This creates a dedicated application at `/opt/suncity-optics`, stores its records at `/var/lib/suncity-optics`, and leaves your existing family and Yowie Apache configurations alone. Do not place the backend or database in `/var/www/html`.

1. Copy this extracted `suncity-optics` folder to your Pi, such as `/home/mervin/suncity-optics`.
2. Open a terminal:

```bash
cd /home/mervin/suncity-optics
sudo bash install-pi.sh
```

3. Enter the full public origin you plan to use, such as `https://optics.example.com`. You can instead start with a LAN URL, such as `http://192.168.0.120:8081`, if configuring the LAN test below. The origin must match the browser address exactly, including scheme and port. Do not include `/index.html` or a subdirectory. This app expects its own domain or port, at the URL root.
4. Choose the admin username and a password of at least 12 characters. Store them privately. The installer will not overwrite an existing `/opt/suncity-optics` installation.
5. Connect Apache using one of the following routes. The Python service listens only on `127.0.0.1:8090`, so visitors reach it through Apache or another reverse proxy.

### Option A — test on your home network using a separate port

Keep your existing ports 80, 443 and 8443. Check that 8081 is available before choosing it. Use another free port if needed and update the origin accordingly.

```bash
sudo a2enmod proxy proxy_http
sudo nano /etc/apache2/sites-available/suncity-lan.conf
```

Paste:

```apache
Listen 8081
<VirtualHost *:8081>
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8090/
    ProxyPassReverse / http://127.0.0.1:8090/
    LimitRequestBody 10485760
</VirtualHost>
```

Then:

```bash
sudo a2ensite suncity-lan.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Open `http://192.168.0.120:8081/`, replacing the IP if your Pi uses another address. The Staff admin link is at the bottom. LAN HTTP is for initial private testing. Use HTTPS for a public site and admin login.

### Option B — public domain on your Pi

Use a dedicated domain/subdomain. `deploy/apache-vhost.conf` is an example for a separate Apache virtual host; replace its example domain. Configure DNS and an HTTPS certificate using your hosting/network provider. The home connection must be reachable, or use an HTTPS tunnel to Apache/the local service. A tunnel can avoid router port forwarding, but the Pi still needs power, internet and uptime. Follow the tunnel provider's current setup instructions. DNS alone does not make a private `192.168...` address reachable online.

Enable the proxy modules with `sudo a2enmod proxy proxy_http`. Add your separate site configuration, test with `sudo apache2ctl configtest`, and reload Apache. Preserve existing sites.

When your public HTTPS address is ready, edit:

```bash
sudo nano /etc/suncity-optics.env
```

Set `PUBLIC_ORIGIN=https://your-exact-domain` (without a trailing slash), then:

```bash
sudo systemctl restart suncity-optics
```

The app sets Secure admin cookies when the origin uses HTTPS. Configure your proxy/tunnel to serve the complete site on that single origin; cross-origin frontend/backend separation is not included.

## Set up the three email alerts

In Staff admin → Email & security, enter up to three recipient addresses and save. Separately, use your email provider's SMTP settings in `/etc/suncity-optics.env`:

```ini
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_FROM=bookings@your-domain.example
SMTP_USER=bookings@your-domain.example
SMTP_PASSWORD=your-provider-app-password
```

Port 587 uses STARTTLS; port 465 uses TLS from the start. An email app password or SMTP credentials may be required by your provider. Do not put real credentials in GitHub or public HTML. The `.env` file is readable only by root and the service group.

```bash
sudo systemctl restart suncity-optics
sudo systemctl start suncity-mail.service
sudo systemctl status suncity-mail.timer
```

Submit a test request after configuring recipients and SMTP. Check all three inboxes, junk folders, the dashboard's queued/error counts and `sudo journalctl -u suncity-mail.service`. The test suite uses a simulated SMTP server; actual email delivery must be tested with your account. Failed alerts retry up to ten runs. Use **Retry failed alerts** after correcting settings. Delivery is not a confirmed customer appointment; the shop contacts customers separately. Requests made before adding recipient addresses do not retroactively create alerts.

## Design a homepage in Microsoft Word

1. Create a normal **Word document (.docx)**. Legacy `.doc`, PDF and macro-enabled `.docm` files are not supported.
2. Use Heading 1/2/3 for headings and normal paragraphs for text. Add bold, italic, underline and text colours if desired.
3. Insert photos using **Insert → Pictures** and choose **In Line with Text**. Use embedded PNG, JPEG, GIF or WebP files. Linked/cloud-only pictures and SVG/EMF/WMF/HEIC images are not imported; convert those images first.
4. Add links using **Insert → Link** or Ctrl+K. Supported link types are HTTP/HTTPS, `mailto:`, `tel:` and same-page anchors. Use `#booking` to jump to the site's appointment form. A link's destination must already exist; uploading a Word document does not create other webpages.
5. Use simple tables for structured content. Documents reflow for smaller screens. Exact Word pagination, font families/sizes, columns, shapes, text boxes, floating positioning, headers and footers are not preserved. Keep important copy in ordinary document paragraphs.
6. Sign in → Word page import → select your document (under 10 MB) → **Import as draft**.
7. Review the preview, then **Publish Word homepage**. The website header, booking form, visit details, chatbox and footer remain outside the imported content.
8. To revert, choose **Use built-in homepage**. Your latest Word draft stays available. The importer keeps embedded image files; originals and older image assets are not automatically garbage-collected. Back up the data directory and retain your original Word documents separately.

The importer constructs a restricted set of HTML from document text. Source HTML, macros, JavaScript links, embedded objects and external image relationships are not executed or imported.

## Existing Setmore appointments

The verified business details were sourced from `https://suncityoptics.setmore.com/` on 6 November 2026. Please review the shop's details before launch. Facebook is linked as supplied; its page content could not be reliably extracted. No employee names, reviews, customer counts or brand partnerships were invented.

The homepage links to the existing Setmore booking page. Admin contains a shortcut to Setmore. **There is no Setmore API synchronization in this package.** Appointments made on Setmore remain in Setmore and follow its notification settings. To display those appointments in this dashboard automatically, a separate authorized Setmore integration is needed. The website's own request form and message form feed this dashboard and its three alert addresses.

## Can this launch through GitHub?

**GitHub can store the source and connect it to hosting. GitHub Pages alone cannot run this application.** Pages serves static files and cannot execute the Python backend, save SQLite records, process Word files or send these server-side email alerts.

For the complete site, push the source to a GitHub repository, then deploy it to either:

- Your Raspberry Pi using this installer and Apache/HTTPS.
- A Linux server or Python/container-capable web host with HTTPS and persistent disk storage, using the Dockerfile or Gunicorn.

Do not include the `data/` folder, real environment files, database files, customer information or passwords in GitHub. The included `.gitignore` excludes them. GitHub Actions deployment is not configured because the repository and hosting account have not been chosen.

### Example container deployment on a Linux host

Build from the project folder:

```bash
docker build -t suncity-optics .
docker volume create suncity-data
docker run --rm -it -v suncity-data:/data suncity-optics python3 app.py setup
```

Create a private environment file on the host containing your real `PUBLIC_ORIGIN`, `SMTP_*` values and `SUNCITY_DATA=/data`, then launch:

```bash
docker run -d --name suncity-web --restart unless-stopped --env-file /secure/path/suncity.env -p 127.0.0.1:8090:8090 -v suncity-data:/data suncity-optics
```

Configure a reverse proxy with HTTPS to port 8090. The same persistent volume must survive rebuilds/redeployments. If your provider does not run Docker with persistent disks, use a VM or a compatible Python service instead. A static-only host will not work. To deliver email, schedule the command `python3 app.py mail` once a minute using the same environment and data volume, for example with a host scheduler running:

```bash
docker exec suncity-web python3 app.py mail
```

The container starts only the web process; the mail schedule is essential. The Docker recipe and Raspberry Pi installer are provided but were not executed against your machine or a hosting account.

## Password reset, logs and updates

Reset the admin account (replaces the username/password and signs out all sessions):

```bash
sudo -u www-data env SUNCITY_DATA=/var/lib/suncity-optics python3 /opt/suncity-optics/app.py setup
```

Logs:

```bash
sudo journalctl -u suncity-optics -n 50
sudo journalctl -u suncity-mail.service -n 50
```

Before an update, stop the web service and timer, wait for any running mail service to finish, then back up `/var/lib/suncity-optics` and the private environment file to a protected location. This directory includes the database and imported images; both are needed for a full restore. Keep customer records out of public shares.

For a code update, replace only `/opt/suncity-optics/app.py`, `docx_import.py` and `public/` with the new version. Keep `/var/lib/suncity-optics` and `/etc/suncity-optics.env`. Then restart `suncity-optics` and `suncity-mail.timer`. Follow any future version's migration instructions before replacing code. This package uses schema version 2. On first startup it adds the user-role fields and activity table automatically and invalidates legacy sessions. Existing accounts become admins and keep their saved passwords.

## Local development & validation

Python 3.9 or newer with system timezone data is required. No third-party Python packages are needed for the application itself. Production runs under Gunicorn.

```bash
python3 app.py setup
python3 app.py
```

Open `http://localhost:8090/`. The built-in server is a development option, not the public hosting process. For another browser address, set `PUBLIC_ORIGIN` to that exact origin. Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

Ten integration tests cover named accounts, bootstrap initialization, forced password changes, roles, disabled/reset accounts, audit attribution, migration of the original schema, and login, CSRF/origin checks, private-record access, booking submission/validation and assignments, the inbox, password changes, DOCX draft/publish/restore and clickable links/images, submission limits, CSV export, and simulated mail success/failure. JavaScript syntax was checked with Node. Browser-based visual verification was unavailable in the build environment; responsive layouts still need a check on your phone after installation. Real SMTP delivery, Apache, systemd, Docker and public DNS/HTTPS require deployment verification.
