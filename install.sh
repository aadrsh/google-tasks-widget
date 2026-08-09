#!/bin/bash

echo "🚀 Installing Tasks Widget (Unofficial)..."

# 1. Setup Python Virtual Environment and Install
python3 -m venv venv
./venv/bin/pip install .

# Get the absolute path to executable and icon
PROJECT_DIR="$(pwd)"
EXEC_PATH="$PROJECT_DIR/venv/bin/google-tasks-widget"
CLI_PATH="$PROJECT_DIR/venv/bin/google-tasks-cli"
ICON_PATH="$PROJECT_DIR/resources/icon.png"

echo "📝 Generating Desktop Shortcuts..."

# 2. Create Application Menu Shortcut (so it looks like a normal app)
mkdir -p ~/.local/share/applications
cat <<EOF > ~/.local/share/applications/google-tasks-widget.desktop
[Desktop Entry]
Version=1.0
Name=Tasks Widget (Unofficial)
Comment=Transparent desktop widget for Google Tasks (Unofficial Client)
Exec=env QT_QPA_PLATFORM=wayland $EXEC_PATH
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Office;Utility;
EOF
echo "✅ Added to Application Menu!"

# 3. Create Autostart Shortcut (so it launches on reboot)
mkdir -p ~/.config/autostart
cat <<EOF > ~/.config/autostart/google-tasks-widget.desktop
[Desktop Entry]
Type=Application
Name=Tasks Widget (Unofficial)
Comment=Starts the Tasks Desktop Widget on startup
Exec=env QT_QPA_PLATFORM=wayland $EXEC_PATH
Icon=$ICON_PATH
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
echo "✅ Added to Startup Menu!"

echo ""
echo "🎉 Installation Complete!"
echo "To add an account, run: $CLI_PATH add-account <name>"
