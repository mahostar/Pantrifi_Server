# Pantrifi Scheduler Service - Simple Guide

## What This Does
Runs your `scheduler.py` continuously in the background on Linux servers with automatic restart if it crashes.

## Installation (One-Time Setup)

### Step 1: Copy Files to Linux Server
```bash
# Upload your entire pantrifi_server folder to Linux
scp -r pantrifi_server/ user@server:/home/user/
```

### Step 2: Install Service
```bash
# Navigate to your project folder
cd /home/user/pantrifi_server

# Make script executable
chmod +x install_service.sh

# Install service (requires sudo)
sudo ./install_service.sh
```

**That's it!** The script automatically:
- Detects your current directory
- Detects your username  
- Creates the service file with correct paths
- Installs and enables the service

## Daily Commands

### Start the Service
```bash
sudo systemctl start pantrifi-scheduler
```

### Stop the Service
```bash
sudo systemctl stop pantrifi-scheduler
```

### Check if Running
```bash
sudo systemctl status pantrifi-scheduler
```

### View Live Logs
```bash
sudo journalctl -u pantrifi-scheduler -f
```

### Restart Service
```bash
sudo systemctl restart pantrifi-scheduler
```

## Auto-Start on Boot

### Enable (starts automatically when server boots)
```bash
sudo systemctl enable pantrifi-scheduler
```

### Disable (won't start automatically)
```bash
sudo systemctl disable pantrifi-scheduler
```

## Troubleshooting

### Service Won't Start?
```bash
# Check what's wrong
sudo systemctl status pantrifi-scheduler

# See error messages
sudo journalctl -u pantrifi-scheduler -n 20

# Test manually first
cd /your/project/path
python3 scheduler.py
```

### Wrong Paths?
```bash
# Check current service settings
sudo systemctl cat pantrifi-scheduler

# Reinstall from correct directory
cd /correct/path/to/pantrifi_server
sudo ./install_service.sh
```

## Important Notes

- **Always run install script from your project directory**
- **Service runs as your user, not root**
- **Automatically restarts if crashes**
- **Logs saved in system journal**
- **Works from any directory path**

## Quick Reference
```bash
# Essential commands (copy-paste ready)
sudo systemctl start pantrifi-scheduler     # Start
sudo systemctl stop pantrifi-scheduler      # Stop  
sudo systemctl status pantrifi-scheduler    # Check status
sudo journalctl -u pantrifi-scheduler -f    # Live logs
sudo systemctl restart pantrifi-scheduler   # Restart
```

---
**Remember**: Run `sudo ./install_service.sh` from the directory containing your `scheduler.py` file!