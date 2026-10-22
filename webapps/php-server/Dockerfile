FROM php:8.3-cli
WORKDIR /uploads
# the root flag lives outside the docroot: the php server serves everything
# in /uploads raw, so the flag must be readable only via command execution
COPY root.txt /var/root.txt
# "TV feed": router sends / -> /feed and streams feed.mp4 (kept outside the docroot)
COPY router.php /srv/router.php
COPY feed.mp4 /srv/feed.mp4
EXPOSE 8080
CMD ["php", "-S", "0.0.0.0:8080", "-t", "/uploads", "/srv/router.php"]
