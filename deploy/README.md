# Shared ReadCine navigation

`nginx/rc-home-nav.conf` is the versioned source of ECS `/etc/nginx/snippets/rc-home-nav.conf`.
The existing `/etc/nginx/conf.d/rc-home-nav-map.conf` keeps per-host placement; do not overwrite it.

Deploy index.html, headlines.json and icons/ to `/var/www/moviehome-landing` using sibling temporary files, SHA-256 verification, then atomic mv. Keep backups outside the web root. This same main branch is GitHub Pages source.

For the nginx snippet: keep a backup, transfer to a sibling temporary file, verify SHA-256, mv, run nginx -t, then reload. OAuth/SSO and proxy routes are not changed.
