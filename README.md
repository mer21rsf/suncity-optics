# Eyeglass enquiries and customer moments

The update also includes an admin-managed **Eyeglass models** gallery (unique codes, search and enquiry buttons) and **Customer photos** slideshow (up to 10, configurable 4/5/7/10-second timing, full-image fit and pause controls). Read **BOOKING_AND_STORIES_UPDATE.md** for the complete feature/update guide. Existing notes, bookings, accounts and settings are preserved.

# Latest features

Read **BOOKING_AND_STORIES_UPDATE.md** for reapplication steps and behavior. Calendar bookings now respect opening hours, service duration and occupied intervals. Admins can delete bookings/messages, clean logs, and approve or remove community notes. The website editor can upload an eyeglass-model or AI-generated featured photo for the “Made for your point of view” area.

Existing Supabase users should deploy the code update without rerunning migration or account setup.

# Sun City Optics — complete local/cloud update

Read **CLOUD_SETUP.md** for the full steps and **../START_HERE.md** in the ZIP for the short checklist.

This package retains the optical site design, footer admin link, employee profiles, individual sign-ins, roles, password changes, audit history, booking requests, bottom-right message chatbox, Word import/preview/publishing, three alert recipients and Setmore shortcut. It includes the corrected first-login UI and booking/message session-check fix.

New: Supabase PostgreSQL for live records and private object storage for Word images; fail-closed cloud writes; migration from the existing Pi database preserving password hashes; private backup exports; an optional HTTPS mail sender; storage diagnostics and a data-preserving Pi updater.

No credentials are included. Existing Pi site credentials are in the database as hashes and are copied by migration; they are not embedded in code. The database password and Supabase server key belong only in private server environment settings.

| Host | Entry point |
| --- | --- |
| Pi family-site shortcut | `https://192.168.0.120/suncityoptics.html` |
| Pi optical homepage | `http://192.168.0.120:8081/suncityoptics/index.html` |
| Pi admin | `http://192.168.0.120:8081/suncityoptics/admin` |
| Render | Its assigned HTTPS URL, with `/admin` or `/suncityoptics/admin` |

The Pi layout remains `/var/www/html/suncityoptics/`, with its shortcut outside at `/var/www/html/suncityoptics.html`. The family `index.html` is retained. Private source, environment and data files remain protected by the existing global Apache rule; application routes whitelist public assets.

For an existing Pi installation use `update-pi.sh`. For a genuinely new Pi installation use `install-pi.sh`. For GitHub/Render upload the contents of this folder to the repository root, keeping the updated Dockerfile and new Python modules together.

Storage defaults to local SQLite/images unless cloud mode is explicitly configured. Local mode requires no PostgreSQL connection. The Dockerfile and Pi scripts install the optional PostgreSQL dependency. Native Python hosts can use `pip install -r requirements.txt`.

The cloud database schema is private `suncity`. There is no public browser database access and no external file synchronization through GitHub. Live Supabase data and private backup exports address different needs. Existing Setmore appointments are still separate; this package does not synchronize the Setmore API. Employee profiles and login accounts are separate, and the chatbox remains an FAQ/message interface rather than live chat or AI.

Migration into a nonempty destination is refused. Existing local records remain untouched. Do not rerun account setup on a populated site during an update. Supabase/Render Free have usage limits and inactivity behavior; verify your own deployment before real customer use.

Tests: `python3 -m unittest discover -s tests -v`. Tests include local application behavior and simulated cloud/migration/storage/mail failures; real cloud credentials are needed for final connection and persistence verification.
