#!/bin/bash

# Pantrifi Scheduler Service Installation Script

set -e

echo "🍽️ Installing Pantrifi Scheduler Service..."

# Get current user and working directory
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

echo "📍 Current user: $CURRENT_USER"
echo "📍 Current directory: $CURRENT_DIR"

# Check if running as root for service installation
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo) to install systemd service"
    exit 1
fi

# Get the actual user who called sudo
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
    ACTUAL_HOME=$(eval echo ~$SUDO_USER)
else
    ACTUAL_USER="$CURRENT_USER"
    ACTUAL_HOME="$HOME"
fi

echo "📍 Service will run as user: $ACTUAL_USER"
echo "📍 Working directory will be: $CURRENT_DIR"

# Define paths
SERVICE_FILE="pantrifi-scheduler.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE"

# Check if scheduler.py exists
if [ ! -f "$CURRENT_DIR/scheduler.py" ]; then
    echo "❌ scheduler.py not found in $CURRENT_DIR"
    echo "Please run this script from the directory containing scheduler.py"
    exit 1
fi

# Check if schedule configuration exists
if [ ! -f "$CURRENT_DIR/schedule_config.json" ]; then
    echo "⚠️ Warning: schedule_config.json not found. Run 'python3 schedule_config.py' first."
fi

# Create service file with actual paths
echo "📋 Creating service file with your paths..."
cat > "$SERVICE_PATH" << EOF
[Unit]
Description=Pantrifi Scheduler Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$ACTUAL_USER
Group=$ACTUAL_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=$CURRENT_DIR
Environment=PYTHONUTF8=1
ExecStart=/usr/bin/python3 $CURRENT_DIR/scheduler.py
Restart=always
RestartSec=10
KillMode=process
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pantrifi-scheduler

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$CURRENT_DIR
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
chmod 644 "$SERVICE_PATH"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
systemctl enable pantrifi-scheduler

echo "🎉 Installation complete!"
echo ""
echo "📖 Service Configuration:"
echo "  User: $ACTUAL_USER"
echo "  Working Directory: $CURRENT_DIR"
echo "  Service File: $SERVICE_PATH"
echo ""
echo "📖 Usage:"
echo "  Start:   sudo systemctl start pantrifi-scheduler"
echo "  Stop:    sudo systemctl stop pantrifi-scheduler"
echo "  Status:  sudo systemctl status pantrifi-scheduler"
echo "  Logs:    sudo journalctl -u pantrifi-scheduler -f"
echo ""
echo "📚 Full documentation: service_usage_doc.md"