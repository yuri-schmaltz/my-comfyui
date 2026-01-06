#!/bin/bash
set -e

# Configuration
NGINX_CONF_SRC="$(pwd)/nginx/comfyui_nginx.conf"
NGINX_CONF_DEST="/etc/nginx/sites-available/comfyui"
SSL_DIR="/etc/nginx/ssl"
HTPASSWD_FILE="/etc/nginx/.htpasswd"

echo "=== ComfyUI Proxy Helper Setup ==="

# Check dependencies
if ! command -v nginx &> /dev/null; then
    echo "[ERROR] Nginx not found. Please install: sudo apt install nginx"
    exit 1
fi

if ! command -v htpasswd &> /dev/null; then
    echo "[ERROR] htpasswd not found. Please install: sudo apt install apache2-utils"
    exit 1
fi

# Create SSL Directory
if [ ! -d "$SSL_DIR" ]; then
    echo "[INFO] Creating SSL directory..."
    sudo mkdir -p "$SSL_DIR"
fi

# Generate Self-Signed Certificate if missing
if [ ! -f "$SSL_DIR/comfyui_selfsigned.key" ]; then
    echo "[INFO] Generating Self-Signed SSL Certificate..."
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/comfyui_selfsigned.key" \
        -out "$SSL_DIR/comfyui_selfsigned.crt" \
        -subj "/C=BR/ST=SP/L=Sao Paulo/O=ComfyUI/OU=Dev/CN=localhost"
else
    echo "[INFO] SSL Certificate already exists."
fi

# Setup Basic Auth User
echo "[INFO] Setting up Authentication. You will be prompted for a password."
read -p "Enter username for ComfyUI: " USERNAME
sudo htpasswd -c "$HTPASSWD_FILE" "$USERNAME"

# Install Nginx Config
echo "[INFO] Installing Nginx configuration..."
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo "[WARN] Removing default Nginx site..."
    sudo rm /etc/nginx/sites-enabled/default || true
fi

sudo cp "$NGINX_CONF_SRC" "$NGINX_CONF_DEST"
sudo ln -sf "$NGINX_CONF_DEST" "/etc/nginx/sites-enabled/"

# Test and Reload
echo "[INFO] Testing Nginx config..."
sudo nginx -t

echo "[INFO] Reloading Nginx..."
sudo systemctl reload nginx

echo "=== Setup Complete ==="
echo "Access ComfyUI securely at: https://localhost:8443"
echo "Login with user: $USERNAME"
