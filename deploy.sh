#!/usr/bin/env bash

set -Eeuo pipefail

APP_NAME="flask-service"
APP_USER="flaskapp"
APP_GROUP="flaskapp"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/opt/flask-service"
VENV_DIR="${APP_DIR}/.venv"

SERVICE_FILE="${SOURCE_DIR}/deploy/systemd/flask-service.service"
NGINX_FILE="${SOURCE_DIR}/deploy/nginx/flask-service.conf"

SYSTEMD_TARGET="/etc/systemd/system/flask-service.service"
NGINX_TARGET="/etc/nginx/sites-available/flask-service"
NGINX_LINK="/etc/nginx/sites-enabled/flask-service"

HEALTH_URL="http://127.0.0.1/health"
HEALTH_RETRIES=10
HEALTH_DELAY=2

log() {
    printf '[deploy] %s\n' "$1"
}

fail() {
    printf '[deploy] ERROR: %s\n' "$1" >&2
    exit 1
}

on_error() {
    local exit_code=$?

    printf '[deploy] Deployment failed on line %s\n' "${BASH_LINENO[0]}" >&2

    systemctl status "${APP_NAME}" --no-pager || true
    journalctl -u "${APP_NAME}" -n 30 --no-pager || true

    exit "${exit_code}"
}

trap on_error ERR

if [[ "${EUID}" -ne 0 ]]; then
    fail "Run this script with sudo"
fi

for required_file in \
    "${SOURCE_DIR}/app.py" \
    "${SOURCE_DIR}/requirements.txt" \
    "${SERVICE_FILE}" \
    "${NGINX_FILE}"
do
    [[ -f "${required_file}" ]] || fail "Missing file: ${required_file}"
done

id "${APP_USER}" >/dev/null 2>&1 || fail "User ${APP_USER} does not exist"

log "Installing operating-system dependencies"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
    nginx \
    python3 \
    python3-pip \
    python3-venv \
    rsync \
    curl

log "Creating application directory"

install -d \
    -o "${APP_USER}" \
    -g "${APP_GROUP}" \
    -m 0755 \
    "${APP_DIR}"

source_real="$(realpath "${SOURCE_DIR}")"
target_real="$(realpath "${APP_DIR}")"

if [[ "${source_real}" != "${target_real}" ]]; then
    log "Copying application files"

    rsync -a --delete \
        --exclude='.git/' \
        --exclude='.env' \
        --exclude='.env.backup' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='.pytest_cache/' \
        --exclude='.coverage' \
        "${SOURCE_DIR}/" \
        "${APP_DIR}/"
else
    log "Source and target directories are identical; file copy skipped"
fi

log "Setting application ownership"

chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

[[ -f "${APP_DIR}/.env" ]] || fail "${APP_DIR}/.env does not exist"

chmod 600 "${APP_DIR}/.env"
chown "${APP_USER}:${APP_GROUP}" "${APP_DIR}/.env"

log "Creating Python virtual environment"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
fi

log "Installing Python dependencies"

sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" -m pip install --upgrade pip
sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" -m pip install \
    -r "${APP_DIR}/requirements.txt"

log "Installing systemd service"

install -o root -g root -m 0644 \
    "${SERVICE_FILE}" \
    "${SYSTEMD_TARGET}"

log "Installing Nginx configuration"

install -o root -g root -m 0644 \
    "${NGINX_FILE}" \
    "${NGINX_TARGET}"

ln -sfn "${NGINX_TARGET}" "${NGINX_LINK}"
rm -f /etc/nginx/sites-enabled/default

log "Checking Nginx configuration"

nginx -t

log "Reloading systemd"

systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl enable nginx

log "Restarting application service"

systemctl restart "${APP_NAME}"
systemctl restart nginx

systemctl is-active --quiet "${APP_NAME}" ||
    fail "${APP_NAME} is not active"

systemctl is-active --quiet nginx ||
    fail "Nginx is not active"

log "Checking health endpoint"

for attempt in $(seq 1 "${HEALTH_RETRIES}"); do
    response_file="$(mktemp)"

    http_status="$(
        curl \
            --silent \
            --show-error \
            --output "${response_file}" \
            --write-out '%{http_code}' \
            --max-time 5 \
            "${HEALTH_URL}" ||
            true
    )"

    if [[ "${http_status}" == "200" ]]; then
        response_body="$(cat "${response_file}")"
        rm -f "${response_file}"

        log "Health check passed"
        printf '%s\n' "${response_body}"
        log "Deployment completed successfully"
        exit 0
    fi

    response_body="$(cat "${response_file}")"
    rm -f "${response_file}"

    log "Health check attempt ${attempt}/${HEALTH_RETRIES} failed: HTTP ${http_status}"
    [[ -n "${response_body}" ]] && printf '%s\n' "${response_body}"

    sleep "${HEALTH_DELAY}"
done

fail "Health endpoint did not return HTTP 200"
