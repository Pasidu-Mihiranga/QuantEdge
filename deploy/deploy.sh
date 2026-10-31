#!/usr/bin/env bash
# Runs on your computer: sends the repository's files to the server and installs them.
#
#   deploy/deploy.sh <server-address> [ssh-user] [key-file]
#
# Only files git tracks or would track are sent, so keys, .env and .venv never leave this machine.
set -euo pipefail

HOST="${1:?usage: deploy/deploy.sh <server-address> [ssh-user] [key-file]}"
USER_NAME="${2:-ubuntu}"
KEY="${3:-qunatage.pem}"
SSH=(ssh -i "$KEY" -o IdentitiesOnly=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new "$USER_NAME@$HOST")

cd "$(git rev-parse --show-toplevel)"
"${SSH[@]}" 'rm -rf ~/quantedge-release && mkdir ~/quantedge-release'
git ls-files -z --cached --others --exclude-standard | COPYFILE_DISABLE=1 tar --no-xattrs --null -T - -czf - | "${SSH[@]}" 'tar -xzf - -C ~/quantedge-release'
"${SSH[@]}" 'sudo bash ~/quantedge-release/deploy/setup_server.sh && rm -rf ~/quantedge-release'
echo "Open http://$HOST"
