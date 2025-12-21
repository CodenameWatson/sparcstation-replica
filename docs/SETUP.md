
---

## `docs/SETUP.md`
```markdown
# Setup Guide (Raspberry Pi OS Bookworm)

## 1) Prerequisites
- Raspberry Pi OS (Bookworm) with desktop
- Auto-login enabled (recommended)
- Network access for apt installs

## 2) Install packages
```bash
sudo apt update
sudo apt install -y qemu-system-sparc qemu-utils python3 python3-pip tigervnc-viewer
pip3 install --break-system-packages pygame psutil
