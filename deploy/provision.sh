#!/usr/bin/env bash
# ClauseGuard VPS provisioning script.
#
# Turns a fresh Ubuntu 24.04 box into a host ready to run the ClauseGuard
# stack: system update, a non-root sudo user, ufw firewall, SSH hardening,
# and Docker. Idempotent-ish; safe to re-read as a reference.
#
# Run as root on a fresh box, or adapt the user-creation section. This mirrors
# the manual steps done during the first deploy so re-hosting is repeatable.
#
# USAGE (as root):
#   NEW_USER=raj bash provision.sh
# Then set the user's password and add your SSH public key (see notes).
set -euo pipefail

NEW_USER="${NEW_USER:-raj}"

echo "==> Updating system"
apt-get update && apt-get upgrade -y

echo "==> Creating non-root user '${NEW_USER}' (set password separately with: passwd ${NEW_USER})"
if ! id -u "${NEW_USER}" >/dev/null 2>&1; then
	adduser --disabled-password --gecos "" "${NEW_USER}"
fi
usermod -aG sudo "${NEW_USER}"

echo "==> Copying root's authorized SSH key to ${NEW_USER}"
mkdir -p "/home/${NEW_USER}/.ssh"
if [ -f /root/.ssh/authorized_keys ]; then
	cp /root/.ssh/authorized_keys "/home/${NEW_USER}/.ssh/authorized_keys"
fi
chown -R "${NEW_USER}:${NEW_USER}" "/home/${NEW_USER}/.ssh"
chmod 700 "/home/${NEW_USER}/.ssh"
chmod 600 "/home/${NEW_USER}/.ssh/authorized_keys" 2>/dev/null || true

echo "==> Configuring firewall (SSH, HTTP, HTTPS)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Hardening SSH (disable root login and password auth)"
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sshd -t
systemctl restart ssh

echo "==> Installing Docker Engine + Compose plugin"
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
	$(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
	> /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "${NEW_USER}"

echo "==> Provisioning complete."
echo "    Next: set the user's password ('passwd ${NEW_USER}'), then log in as"
echo "    ${NEW_USER}, clone the repo, create .env from deploy/.env.prod.example,"
echo "    and run ./deploy/redeploy.sh"