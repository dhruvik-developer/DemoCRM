# ==========================================================
# BASE IMAGE
# ==========================================================
FROM python:3.12-slim-bookworm


# ==========================================================
# PYTHON ENVIRONMENT
# ==========================================================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# ==========================================================
# WORKING DIRECTORY
# ==========================================================
WORKDIR /app


# ==========================================================
# SYSTEM DEPENDENCIES
# ==========================================================
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


# ==========================================================
# PYTHON DEPENDENCIES
# ==========================================================
COPY backend_new/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ==========================================================
# COPY DJANGO PROJECT
# ==========================================================
COPY backend_new/crm/ /app/


# ==========================================================
# DJANGO PORT
# ==========================================================
EXPOSE 8000


# ==========================================================
# DEFAULT COMMAND
# ==========================================================
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
