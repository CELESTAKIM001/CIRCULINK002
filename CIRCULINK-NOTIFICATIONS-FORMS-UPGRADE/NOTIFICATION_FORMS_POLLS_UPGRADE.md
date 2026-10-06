# CIRCULINK Communication, Forms & Polls Upgrade

This upgrade adds a platform-wide notification center and targeted communication workflow.

## Website notifications
- Notification bell is present in the authenticated global header.
- Broadcast notices can be shown to every user.
- Targeted notices can be sent to one account.
- Service alerts can explain unavailable or temporarily disabled areas.
- Notifications can contain an internal link to a form, poll, transaction, certificate or other page.
- Users can open a full notification center and mark one/all as read.

## Admin shared forms
- `/admin/forms` creates controlled forms.
- Fields are defined one per line: `Label | type | required`.
- Forms can be public or assigned to one verified CIRCULINK account.
- The generated `/forms/<slug>` URL can be copied/shared.
- Submissions are stored in MongoDB and reviewed under the form's Responses page.

## System polls
- `/admin/polls` creates polls with multiple options.
- Polls can be public or targeted to one account.
- One response per signed-in account is enforced.
- Results and vote counts are visible to administrators.

## Material posting
- `/dashboard/inventory` now clearly exposes `Post material + upload photos`.
- The posting workflow remains `/marketplace/add` and requires at least one real photo.
