#!/usr/bin/env bash
# Runs on the server, from the unpacked release folder: installs the app as a service behind nginx with HTTPS.
# Works on Ubuntu/Debian and Amazon Linux. Safe to run again for every new release.
set -euo pipefail

RELEASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR=/opt/quantedge
DOMAIN=quantedge.gmora.dev
export UV_PYTHON_INSTALL_DIR="$HOME_DIR/python" UV_CACHE_DIR="$HOME_DIR/.uv-cache"

echo "==> System packages"
if command -v apt-get >/dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq nginx curl tar certbot python3-certbot-nginx
    SITE=/etc/nginx/sites-enabled/quantedge.conf
    rm -f /etc/nginx/sites-enabled/default
elif command -v dnf >/dev/null; then
    dnf install -y -q nginx tar
    SITE=/etc/nginx/conf.d/quantedge.conf
    # Amazon Linux ships a default server on port 80 inside nginx.conf; ours replaces it.
    sed -i '/^    server {/,/^    }/d' /etc/nginx/nginx.conf
else
    echo "Unsupported system: needs apt-get or dnf" >&2
    exit 1
fi

echo "==> Swap (small instances run out of memory while installing)"
if [ "$(awk '/MemTotal/ {print $2}' /proc/meminfo)" -lt 3000000 ] && [ "$(awk '/SwapTotal/ {print $2}' /proc/meminfo)" -eq 0 ]; then
    dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Network (BBR keeps long-distance transfers fast)"
printf 'net.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr\n' > /etc/sysctl.d/90-quantedge-bbr.conf
sysctl -q --system || true

echo "==> Application files"
id quantedge >/dev/null 2>&1 || useradd --system --home-dir "$HOME_DIR" --shell /usr/sbin/nologin quantedge
mkdir -p "$HOME_DIR"
rm -rf "$HOME_DIR/app"
cp -a "$RELEASE" "$HOME_DIR/app"

echo "==> Python 3.12 and the pinned packages"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin INSTALLER_NO_MODIFY_PATH=1 sh
export PATH="/usr/local/bin:$PATH"
uv venv --allow-existing --python 3.12 "$HOME_DIR/venv"
(cd "$HOME_DIR/app" && uv pip install --quiet --python "$HOME_DIR/venv/bin/python" -r requirements.txt -e .)
chown -R quantedge:quantedge "$HOME_DIR"

echo "==> Service and web server"
install -m 644 "$HOME_DIR/app/deploy/quantedge.service" /etc/systemd/system/quantedge.service
install -m 644 "$HOME_DIR/app/deploy/nginx-quantedge.conf" "$SITE"
nginx -t
systemctl daemon-reload
systemctl enable --now nginx quantedge
systemctl restart quantedge
systemctl reload nginx

echo "==> HTTPS (issues the certificate once, then reinstalls it into the fresh nginx site on every release)"
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect --keep-until-expiring

echo "==> Health check"
for _ in $(seq 1 30); do
    if curl -fs "https://$DOMAIN/_stcore/health" >/dev/null; then
        echo "App is up behind nginx"
        exit 0
    fi
    sleep 2
done
echo "App did not start: see journalctl -u quantedge" >&2
exit 1
