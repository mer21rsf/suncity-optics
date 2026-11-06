# Booking calendar, admin cleanup, Sun City Stories and featured photos

This is a code update for your existing Pi/Render/Supabase installation. It preserves your accounts, saved content and records. Existing duplicates are not deleted automatically.

## Apply to Render through GitHub

1. Download and extract the latest `Sun_City_Optics_Website.zip`.
2. Open the extracted `suncityoptics` folder. Upload its **contents** into your GitHub repository at the existing `app.py` / `Dockerfile` level. Replace matching files and preserve subfolders. This update needs the full runtime files, including `scheduling.py`, `booking.js`, `stories.js`, `catalog.js`, `customer-photos.js`, `persistence.py`, `data_tools.py`, the updated HTML/JS/CSS and the Dockerfile. Replacing only `app.py` is not enough.
3. Keep your Render environment variables and certificate Secret File. Do not upload `site.env`, `cloud.env`, databases, customer backups or passwords to GitHub.
4. Commit, then in Render select **Manual Deploy → Deploy latest commit** if auto-deploy does not start. Wait until Live.
5. Refresh the website and admin with Ctrl+F5. No Pi-to-Supabase migration or account reset is needed again. The app adds the calendar/note tables and duration column on startup without removing records.

## Apply to your existing Pi

Upload the new ZIP to your Pi user's home directory using WinSCP, then in PuTTY:

```bash
cd ~
unzip -o Sun_City_Optics_Website.zip -d suncity-feature-update
cd ~/suncity-feature-update/suncityoptics
sudo bash update-pi.sh
```

Use the updater, not the installer or account-setup command. The updater preserves the database and private settings, creates private rollback backups and restarts the application. Your family root `index.html` remains unchanged.

If both Pi and Render use the same Supabase settings, the calendar and notes are shared. A Pi still in local mode remains a separate copy; no automatic synchronization was added between local SQLite and Supabase.

## Appointment calendar

- Visitors choose a service first, then an available calendar day and time button. All dates/times use **America/Vancouver (Surrey)**, regardless of the visitor's browser timezone.
- Times start every **15 minutes relative to opening time**, within a 180-day window. The whole appointment must finish by closing time. A one-hour service cannot start 30 minutes before closing.
- Each reservation keeps the service duration captured when it was submitted. Editing a service duration later does not shorten existing reservations. Older reservations without a duration are initialized from the matching current service, or 60 minutes if that service no longer exists; review unusual old records.
- **One shared shop appointment at a time**, across all services and employee assignments. This version does not provide parallel employee calendars.
- Requested, Confirmed and Completed appointments block their full interval. Cancelled appointments do not. Cancelling or deleting a booking releases the time; adjacent appointments can meet at the same end/start time.
- The server validates every submission again and holds a database transaction lock while checking/inserting. SQLite uses `BEGIN IMMEDIATE`; PostgreSQL uses a transaction advisory lock. Two visitors cannot both reserve an overlapping interval through this app. If availability changes after the page was opened, the second submission is rejected and the calendar refreshes.
- Public availability responses contain only dates and slot availability, without patient names, email addresses or private block labels.
- In **Admin → Bookings**, use **Block unavailable time** for lunch, absences or an entire day. Blocks that overlap existing bookings are refused; contact the customer and cancel/rearrange affected bookings first. You can remove a block later.
- Existing duplicate/out-of-hours records appear in an admin review notice. They stay in the database until you review them. There is no automatic cancellation or deletion of old customer records.
- This calendar covers bookings made through the new website only. Existing **Setmore bookings are not synchronized**. Block the matching time manually or use one booking system as your authoritative calendar to avoid cross-system conflicts.

## Delete bookings and messages

Only Admin-role accounts get deletion controls. Staff-role accounts cannot call the delete API either. Each Delete button asks for confirmation. Deleting a record removes its linked notification queue/history rows; it does not recall email already delivered. A small audit entry records which admin deleted the record, by ID rather than copying its private contents.

Deleting a booking makes its interval available again. If you need to preserve the record, Cancel it instead.

## Clean up logs

In **Admin → Change history**:

- Select rows, then **Delete selected logs**.
- Choose **Older than 7 / 30 / 90 / 180 days**, then **Clean old logs**.
- Or choose **Clear all history**.

These controls are Admin only and require confirmation. One fresh cleanup receipt remains showing the responsible admin and number removed. Cleanup is manual; no scheduled automatic retention deletion was enabled. Download a private backup before irreversible cleanup if needed. Deleting rows makes space reusable; database file/quota displays may not shrink immediately. The updater does not run disruptive database compaction commands.

## Sun City Stories — community sticky notes

The public **Sun City Stories** wall appears on the main page, including when a Word page is published. Visitors can enter a first name/initials and a short note of up to 600 characters. An optional email remains private. Publication consent is required, and the form asks visitors not to include medical or other private details.

All notes start **Pending**. They are not returned by the public stories API until an Admin approves them. Open **Admin → Sun City Stories** to approve, reject/hide, or delete a note. Staff-role accounts cannot moderate. The wall starts empty; no patient testimonials were invented. Notes are plain text, not arbitrary HTML. New notes can queue alerts to the already configured three recipient addresses when email delivery is configured.

## Change the featured eyeglass / AI-generated photo

In **Admin → Website design**:

1. Find **Upload featured eyeglass model / AI photo**.
2. Choose a JPG, PNG, WebP or GIF file under 8 MB.
3. Click **Upload and use photo**.
4. The preview updates immediately. Add a useful photo description and choose **Save website details** to save text changes.

This changes the single featured image in the **“Made for your point of view”** area. You can swap eyeglass models or AI-generated photos whenever needed. **Use default artwork** restores the included illustration. This changes the one featured image. The separate Eyeglass models gallery below provides multiple model cards.

The built-in homepage uses this image. A Word-designed main content area uses the images in the Word document instead. Featured photos and Word images use local files on a local-mode Pi, or Supabase Storage in cloud mode. Photos are stored as files/objects; the database stores their references. Old image objects are retained because they may also be referenced by Word pages; this update does not automatically purge unused storage objects.

## Backups and verification

Private backups now include calendar blocks, pending/approved/rejected notes and image references, as well as the existing records. Active sessions, rate limits and server credentials remain excluded. Keep backups private.

After applying:

1. Request an available time; verify it becomes blocked for an overlapping service.
2. Verify an appointment cannot run past closing or occur on a closed/blocked day.
3. Cancel/delete your test booking and refresh availability; verify it opens again.
4. Submit a note. Verify it is hidden until an admin approves it, and that an optional email never appears publicly.
5. Upload a featured photo; refresh the homepage and verify it appears.
6. Confirm a staff account cannot delete records, clean logs or approve stories.
7. On Render/Supabase, redeploy and check persistence of your test booking, note and photo.

Application tests, concurrent local booking submissions, JavaScript syntax, HTML/controller structure and Pi updater rollback simulations were checked. Live Supabase/PostgreSQL concurrency and visual/browser QA were not available in this build environment; verify those on your deployment. The PostgreSQL adapter uses the same advisory transaction lock as the tested SQLite critical section. The website does not bypass cloud failures with temporary local saves.


## Eyeglass-model gallery and code-based enquiries

Open **Admin → Eyeglass models**. Add a photo, model name, optional style description and unique code such as `SC-001`. Codes use letters, numbers, dashes or underscores and are stored in uppercase. Upload the photo first, then save the model. You can edit, hide or delete a model. Only Admin-role accounts can manage the gallery.

The public gallery supports search by name/code and more-model pagination. Each card displays its model code. **Ask about price & availability** opens the existing bottom-right message form, prefilled with that model code and name. The visitor adds their contact details and sends the enquiry. The inbox and configured alerts receive it as a chat message; staff reply by email.

The gallery does not claim live stock quantities or invent prices, and no sample products were seeded. Staff confirm the exact frame, availability and price. Deleting a model does not remove existing customer enquiry messages containing its old code.

## Customer photos / review-card slideshow (up to 10)

A **Framed with a smile** slideshow sits before the eyeglass-model gallery. It stays hidden until an admin adds at least one visible photo. It gently changes every five seconds by default, with previous/next, photo-selection dots and Pause/Play controls. Autoplay stops for background tabs and pauses on hover/focus. Visitors who request reduced motion start with autoplay off; they can choose Play explicitly.

In **Admin → Customer photos**:

1. Choose a customer photo or review card (JPG, PNG, WebP or GIF, under 8 MB).
2. Click **Upload customer photo**.
3. Add an accessibility description and optional title/caption.
4. Confirm permission to publish. Choose a display-order number; smaller numbers come first.
5. Choose whether it should be visible, then **Save photo**.

Up to 10 photo records may be saved, including hidden photos. Edit/replace one or delete it to make room. You can change timing to 4, 5, 7 or 10 seconds. Images fit fully rather than cropping review-card text. Clicking a photo opens its full image for easier reading.

Your provided example is included in `sample-assets/customer-review-example.png` for easy selection from the downloaded ZIP. It is **not automatically published** or treated as a verified customer testimonial. Add it from admin if appropriate and with the required permission. No fictional customer photos or quotes were added.

Both product photos and customer slideshow photos are included in private backups and the cloud/local image-reference handling. Removing a gallery/slideshow record does not automatically delete the underlying image object because it may be shared with a Word page or another feature.
