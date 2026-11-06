FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-psycopg gunicorn ca-certificates tzdata && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app.py docx_import.py persistence.py cloud_media.py data_tools.py mailer.py migrate_to_supabase.py backup_local.py ./
COPY index.html admin.html style.css site.js admin.js eyewear.svg ./
RUN mkdir /data && chown www-data:www-data /data
ENV SUNCITY_DATA=/data
USER www-data
EXPOSE 8090
CMD ["/bin/sh", "-c", "exec python3 -m gunicorn --workers 2 --bind 0.0.0.0:${PORT:-8090} --timeout 45 app:application"]
