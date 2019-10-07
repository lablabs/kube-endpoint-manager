# https://hub.docker.com/r/lablabs/kube-endpoint-manager
ARG PYTHON_VERSION=3.7-alpine

# Build stage
FROM python:${PYTHON_VERSION} as builder
RUN apk add --no-cache \
            --upgrade \
            libffi-dev \
            alpine-sdk \
            libressl-dev \
            musl-dev

COPY . /build/
COPY ./requirements.txt /wheels/requirements.txt

WORKDIR /build
RUN set -ex; \
    python setup.py sdist bdist_wheel -d /wheels;

WORKDIR /wheels
RUN set -ex; \
    pip install -U pip; \
    pip wheel -r /wheels/requirements.txt;


# Final stage
FROM python:${PYTHON_VERSION}

COPY --from=builder /wheels /wheels

RUN set ex; \
    pip install -U pip; \
    pip install -r /wheels/requirements.txt \
                -f /wheels; \
    pip install kube_endpoint_manager -f /wheels; \
    rm -rf /wheels; \
    rm -rf /root/.cache/pip/*;

CMD kube-endpoint-manager