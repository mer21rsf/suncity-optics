# Sun City Optics — Raspberry Pi web-root edition

This edition implements the requested layout, without replacing your family homepage:

| File or folder | Purpose |
| --- | --- |
| `/var/www/html/index.html` | Your existing family homepage; installer does not modify it |
| `/var/www/html/suncityoptics.html` | Shortcut that opens the optical shop on port 8081 |
| `/var/www/html/suncityoptics/index.html` | Optical shop homepage |
| `/var/www/html/suncityoptics/admin.html` | Staff studio interface |
| `/var/www/html/suncityoptics/app.py`, `docx_import.py` | Python backend and Word importer |
| `/var/www/html/suncityoptics/style.css`, `site.js`, `admin.js`, `eyewear.svg` | Site assets |
| `/var/www/html/suncityoptics/data/` | Database and imported Word images |
| `/var/www/html/suncityoptics/site.env` | Private environment and email configuration |
| `/var/www/html/suncityoptics/deploy/` | Apache/systemd configuration templates |

All application code, assets, records, imported images and private settings are under `suncityoptics`. Apache and systemd also need their normal configuration entries under `/etc`; the installer copies the included templates there.

## How the address works

On your home network, visit your existing site's shortcut:

`https://192.168.0.120/suncityoptics.html`

It redirects the browser to:

`http://192.168.0.120:8081/suncityoptics/index.html`

The shortcut uses the hostname you visited, so changing the Pi's IP does not require editing its JavaScript. Its no-JavaScript fallback uses the original `192.168.0.120` address. This is an HTTP port 8081 setup for your home network. To publish the site online, configure a dedicated HTTPS domain/reverse proxy and update `PUBLIC_ORIGIN`. Do not publish this HTTP test shortcut as a final public login flow.

Admin: `http://192.168.0.120:8081/suncityoptics/admin`.

The optical site remains independent of the family site and Yowie. Its service runs on loopback port 8090, with Apache forwarding port 8081 to it. The physical files stay in your requested folder. Python processes the booking forms and logins; opening `index.html` as a local file or serving it as plain static HTML does not run the backend.

## Install using WinSCP and PuTTY

1. Download the updated ZIP onto Windows. Keep the ZIP intact for transfer.
2. In WinSCP, use SFTP, your Pi IP, port 22 and your Pi credentials. Upload the ZIP to your Pi user's home directory, **not directly into the public web root**. The installer protects the destination before copying private files into it.
3. In PuTTY, connect using SSH to your Pi, then run:

```bash
cd ~
sudo apt-get install -y unzip
unzip -o Sun_City_Optics_Website.zip -d suncity-root-setup
cd ~/suncity-root-setup/suncityoptics
sudo bash install-pi.sh
```

4. At the origin prompt, press Enter for `http://192.168.0.120:8081` or enter your actual Pi address with port 8081. Enter an origin only, not `/suncityoptics` or a filename.
5. Choose your admin username and a password of at least 12 characters. Password typing is hidden. This creates a permanent local account; no shared temporary password is included.
6. The installer configures the optical shop's separate Apache port and starts the web service and email timer. It does not replace your family `index.html` or change your existing virtual-host files.
7. Open the shortcut or direct shop URL above.

The installer stops if an earlier optical installation, destination folder, configuration or occupied port is found. Do not delete those files or your database. Share the message so the existing installation can be migrated while preserving records. The included installer is for a fresh installation, not an automatic migration or update.

## Why the directory is protected

This folder holds Python source, credentials and customer records. The installer adds a global Apache `Directory` rule denying direct filesystem access to `/var/www/html/suncityoptics`, and adds `.htaccess` as a secondary safeguard. It enables the protection before copying private files.

On your normal family-site port, `/suncityoptics/app.py`, `/suncityoptics/site.env`, and all other files in that folder should return **403 Forbidden**. The optical site on port 8081 is served through the Python app, which explicitly serves only approved pages and image assets. Its source, environment and database paths return **404**. The root `suncityoptics.html` shortcut remains accessible on your family site. Do not remove these protections to make static folder URLs work on port 443; use the port 8081 shortcut.

After installation, check in your browser:

- `https://192.168.0.120/index.html` — your existing homepage.
- `https://192.168.0.120/suncityoptics.html` — opens the optical site on 8081.
- `https://192.168.0.120/suncityoptics/site.env` — 403; must never display credentials.
- `http://192.168.0.120:8081/suncityoptics/app.py` — 404.

Exact behavior on your Pi must be verified after installing, because your existing Apache configuration is not available in this package's test environment.

## Staff accounts and change history

Sign in through Staff admin. Admins can create individual sign-ins under **Login accounts**, assign Admin or Staff roles, disable accounts and reset temporary passwords. Each new or reset account must choose its own password before using the studio. Employee public profiles and sign-in accounts are separate records. Staff can edit the shop, bookings, Word pages, profiles and messages. Only admins can manage accounts, change notification recipients or view the change history.

The **Change history** tab records the responsible username for website setting edits, booking status and assignment changes, employee updates, Word imports/publication, account changes and other tracked actions. Passwords are not logged. It displays the newest 500 entries, with a text filter. Logs are stored locally with the database; they are not an independent tamper-proof audit service.

## Microsoft Word homepage

Import a `.docx` file in **Word page import**, preview it, then publish it. Paragraphs, headings, basic formatting, simple tables, hyperlinks and embedded PNG/JPEG/GIF/WebP images are supported. Use pictures **In Line with Text**. Complex Word shapes, positioning, columns, fonts and pagination may differ or be omitted. Use `#booking` as a Word hyperlink to jump to the retained booking section. The website header, visit details, booking form, footer and bottom-right chatbox remain available with a published Word page.

## Bookings, messages and Setmore

Website bookings are requests requiring staff confirmation, not guaranteed available slots. Staff can change status, assign an employee and export CSV. The chatbox gives quick answers and accepts messages for staff; it is not live chat or AI. Staff reply through their email app.

The supplied Setmore link remains available. Existing Setmore appointments are not automatically imported or synchronized into this dashboard. The business details originally came from the shop's Setmore page; review them before launch. No employee names, reviews or customer counts were invented.

## Configure email alerts on your Pi

In Admin → Email & security, save up to three recipient addresses. Edit the server-side SMTP settings:

```bash
sudo nano /var/www/html/suncityoptics/site.env
```

Fill in the values from the shop's email provider:

```ini
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_FROM=bookings@your-domain.example
SMTP_USER=bookings@your-domain.example
SMTP_PASSWORD=your-private-app-password
```

Use provider-specific SMTP credentials, not the website admin password. Port 587 uses STARTTLS; 465 uses TLS from connection. Save, then run:

```bash
sudo systemctl restart suncity-optics
sudo systemctl start suncity-mail.service
sudo systemctl status suncity-mail.timer
```

The installer runs the mail queue every minute. Configure recipients before submitting a test request and check all inboxes/junk folders. Email delivery has to be verified using your real provider. Alerts contain a dashboard link and reference, without customer details. Changes to booking status do not automatically email customers. Failed delivery retries up to ten times; retry failed alerts from admin after correcting settings.

## Editing, backups and password recovery

Use admin for content, staff and Word changes. You can locate all code and data in the one requested folder using WinSCP. Protected system-owned files may require `sudo` through PuTTY; do not make credentials or the database world-writable to enable editing.

Back up the complete `data` folder and `site.env` privately before updates. Stop the web service and email timer and wait for any active mail run to finish before a filesystem backup. Never place a backup ZIP containing credentials or customer records in `/var/www/html` outside the protected directory.

Reset the admin accounts only if needed (this replaces all sign-in accounts, while retaining shop data and logs):

```bash
sudo -u www-data env SUNCITY_DATA=/var/www/html/suncityoptics/data python3 /var/www/html/suncityoptics/app.py setup
```

Logs:

```bash
sudo journalctl -u suncity-optics -n 50
sudo journalctl -u suncity-mail.service -n 50
```

## Testing and portability

Application tests run with Python 3.9+ and system timezone data:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers authentication, roles, account bootstrap, migration of original accounts, bookings, messages, Word links/images, mail simulation and the requested nested routes. JavaScript syntax and installer embedded Python are checked separately. Browser visual QA and execution against your Pi's Apache/systemd/SMTP were not available here.

The included Dockerfile remains a portable option for a Python/container-capable host. It expects `/data` for persistent records. On Render Free, local records are disposable and normal SMTP ports are blocked; use only sample data. For Pi hosting, no Render settings are required. The SQLite schema is version 2 and retains the account migration from the earlier package.
