FROM php:8.3-cli
WORKDIR /uploads
# the root flag lives outside the docroot: the php server serves everything
# in /uploads raw, so the flag must be readable only via command execution
COPY root.txt /var/root.txt
EXPOSE 8080
CMD ["php", "-S", "0.0.0.0:8080", "-t", "/uploads"]
