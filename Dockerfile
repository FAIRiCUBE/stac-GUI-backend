FROM python:3.11.1

ENV PROMETHEUS_MULTIPROC_DIR /var/tmp/prometheus_multiproc_dir
RUN mkdir $PROMETHEUS_MULTIPROC_DIR \
    && chown www-data $PROMETHEUS_MULTIPROC_DIR \
    && chmod g+w $PROMETHEUS_MULTIPROC_DIR

WORKDIR /srv/service
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ADD . /srv/service

USER www-data


CMD ["uvicorn", "--host=0.0.0.0", "--port", "5000", "--log-level=debug", "fairicube_catalog_backend:app", "--workers", "5"]

EXPOSE 5000