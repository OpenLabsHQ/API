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
    
RUN wget -O- https://apt.releases.hashicorp.com/gpg | \
    gpg --dearmor | \
    tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null

RUN echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
    https://apt.releases.hashicorp.com bookworm main" | \
    tee /etc/apt/sources.list.d/hashicorp.list
RUN apt-get update && apt-get install -y terraform

# Install python dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY src /code/src
COPY .env /code/.env

# Set up terraform cache
WORKDIR src/app/core/cdktf
RUN mkdir -p "/root/.terraform.d/plugin-cache"
COPY src/app/core/cdktf/.terraformrc /root/.terraformrc 
RUN terraform init
RUN rm -rf .terraform*
WORKDIR /code

# For dynamic versioning
COPY .git /code/.git

EXPOSE 80

HEALTHCHECK --interval=60s --timeout=5s --start-period=60s --retries=3 \
 CMD ["python", "-m", "src.scripts.health_check"]


# ========= Debug Image =========
# Adds debug capabilities
FROM builder AS debug

RUN pip install --no-cache-dir debugpy


# ========= Test Image =========
# Adds test dependencies
FROM debug AS test

COPY tests /code/tests

COPY ./dev-requirements.txt /code/dev-requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/dev-requirements.txt


# ========= Prod Image =========
# Extra prod goodies
FROM builder AS prod

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "4"]