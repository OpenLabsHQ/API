# ========= Builder Image =========
# Base setup stage
FROM python:3.12-slim AS builder

WORKDIR /code

RUN apt-get update && apt-get install -y git curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get install -y gnupg software-properties-common \
    && apt-get install -y wget \
    && apt-get install -y gnupg2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY api/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY api/src /code/src
COPY .env /code/.env

# For dynamic versioning
COPY .git /code/.git

EXPOSE 80

# ========= Test Builder Image =========
# Base test setup stage
FROM builder AS test_builder

COPY api/tests /code/tests

COPY api/dev-requirements.txt /code/dev-requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/dev-requirements.txt

COPY api/pyproject.toml /code/pyproject.toml 

# ========= API Debug Image =========
# Adds debug capabilities
FROM builder AS api_debug

RUN pip install --no-cache-dir debugpy

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
 CMD ["python", "-m", "src.scripts.health_check"]


# ========= API Test Image =========
# Adds test dependencies
FROM test_builder AS api_test

HEALTHCHECK --interval=5s --timeout=5s --start-period=300s --retries=3 \
 CMD ["python", "-m", "src.scripts.health_check"]


# ========= Worker Image =========
# Adds worker dependencies
FROM builder AS worker
    
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget gpg ca-certificates && \
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor > /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && \
    apt-get install -y terraform && \
    # Clean up to keep the image size down
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up terraform cache
WORKDIR src/app/core/cdktf
RUN mkdir -p "/root/.terraform.d/plugin-cache"
COPY api/src/app/core/cdktf/.terraformrc /root/.terraformrc 
RUN terraform init
RUN rm -rf .terraform*
WORKDIR /code

CMD ["arq", "src.app.worker.settings.WorkerSettings"]


# ========= Prod Image =========
# Extra prod goodies
FROM builder AS prod

HEALTHCHECK --interval=60s --timeout=5s --start-period=60s --retries=3 \
 CMD ["python", "-m", "src.scripts.health_check"]

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "4"]