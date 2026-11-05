FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CAFE_DATA_DIR=/data DJANGO_STATIC_ROOT=/app/server/staticfiles
WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY server server
COPY index.html menu.html contacts.html style.css script.js menu-render.js menu-data.json admin_server.py ./
COPY assets assets
RUN python server/build_static.py && DJANGO_DEBUG=1 python server/manage.py collectstatic --noinput && useradd --uid 10001 --create-home cafe && mkdir -p /data && chown cafe:cafe /data
USER cafe
EXPOSE 8000
CMD ["sh","-c","python server/manage.py migrate --noinput && python server/manage.py import_menu && exec gunicorn --chdir server config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 60"]
