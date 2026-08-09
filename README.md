# Tasks Widget & MCP Server (Unofficial for Google Tasks)

> 🚀 **Coming Soon to Linux App Stores (Flathub & Snapcraft)!**  
> We are currently preparing the native Flatpak/Snap packages and submitting the application for official Google OAuth verification. Stay tuned!

> [!IMPORTANT]
> **Legal Disclaimer**: This application is an independent, unofficial client and is NOT affiliated with, authorized, maintained, sponsored, or endorsed by Google LLC or any of its affiliates. "Google Tasks" is a trademark of Google LLC.

A transparent, sticky, interactive desktop widget and **Model Context Protocol (MCP) Server** for Google Tasks built specifically for Linux desktop environments (GNOME / Wayland / X11). It supports syncing tasks from multiple Google Accounts simultaneously.

---

## 🌟 Key Features

- **Desktop Widget**: Transparent, borderless, always-on-top desktop widget with modern dark glassmorphic styling.
- **MCP Server Integration**: Built-in MCP Server (`google-tasks-mcp`) allowing AI assistants (Claude Code, Claude Desktop, Antigravity, Cursor, Windsurf) to manage your Google Tasks via `stdio`.
- **Multi-Account Support**: Manage and view tasks from multiple Google Accounts in a single aggregated list.
- **Interactive Task Management**: Add tasks with due dates/repeat settings, check them off, or delete them directly from your desktop.
- **Smart Due Dates**: Human-readable relative date badges (**Today**, **Tomorrow**, **Overdue**, **Wednesday**) with color coding.
- **Recurring Tasks**: Native support for repeat settings (Daily, Weekly, Monthly) with 🔁 indicators.
- **Real-time Search Bar**: Filter tasks instantly across all accounts as you type.
- **Linux Integration**: Built-in `install.sh` script adding launcher shortcuts to your Application Menu and Autostart.

---

## 🛠️ Prerequisites & OAuth Setup

To run this application locally, you will need a Google Cloud OAuth Client ID:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Tasks API**.
3. Configure your OAuth Consent Screen and create OAuth 2.0 Client Credentials (**Desktop Application** type).
4. Download the credentials as `credentials.json`.
5. Place `credentials.json` in:
   `~/.config/google-tasks-widget/credentials.json`

---

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/google-tasks-widget.git
   cd google-tasks-widget
   ```

2. Run the automated installation script:
   ```bash
   ./install.sh
   ```
   *(This creates a virtual environment, installs dependencies, and creates Linux Application Menu & Autostart shortcuts).*

---

## 💻 Usage & CLI

### 1. Authenticate an Account
Use the included CLI manager to link your Google Accounts:
```bash
./venv/bin/google-tasks-cli add-account "Work"
./venv/bin/google-tasks-cli add-account "Personal"
```

### 2. Manage Accounts
```bash
# List configured accounts
./venv/bin/google-tasks-cli list-accounts

# Remove an account
./venv/bin/google-tasks-cli remove-account "Work"
```

### 3. Launch the Desktop Widget
```bash
./venv/bin/google-tasks-widget
```
*(Or launch it from your Linux Application Menu by searching for **Tasks Widget**).*

---

## 🤖 MCP Server Setup for AI Assistants

This repository includes a secure, stdio-based MCP Server binary (`google-tasks-mcp`).

### Claude Code CLI
```bash
claude mcp add google-tasks /path/to/your/venv/bin/google-tasks-mcp
```

### Antigravity AI / Cursor / Claude Desktop
Add this to your MCP configuration file:

```json
{
  "mcpServers": {
    "google-tasks": {
      "command": "/path/to/your/venv/bin/google-tasks-mcp"
    }
  }
}
```

### Available AI Tools:
- `get_accounts`: List connected Google accounts.
- `list_tasks(account_name)`: Get pending tasks and lists.
- `create_task(account_name, list_id, title, notes, due_date, repeat_frequency)`: Create a new task.
- `complete_task(account_name, list_id, task_id)`: Mark a task as completed.
- `delete_task(account_name, list_id, task_id)`: Delete a task.

---

## 📄 License

Distributed under the GNU General Public License v3.0 (GPLv3). See `LICENSE` for details.
