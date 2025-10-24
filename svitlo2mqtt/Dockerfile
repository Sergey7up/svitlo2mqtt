ARG BUILD_FROM
FROM $BUILD_FROM

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# System deps
RUN apk add --no-cache python3 py3-pip tzdata

# Create and prepare venv (PEP 668: do not touch system site-packages)
RUN python3 -m venv /venv \
    && /venv/bin/python -m pip install --upgrade pip setuptools wheel
ENV PATH="/venv/bin:$PATH"

# Python deps
COPY requirements.txt /tmp/requirements.txt
RUN /venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# App code
COPY telethon_mqtt.py /app/telethon_mqtt.py
COPY parse_kyiv.py /app/parse_kyiv.py

# Entrypoint
COPY run.sh /run.sh
RUN chmod +x /run.sh && sed -i 's|kyiv_telethon_mqtt.py|telethon_mqtt.py|g' /run.sh || true

CMD ["/run.sh"]
