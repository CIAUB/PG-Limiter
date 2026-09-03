# 🛡️ PG-Limiter

<div align="center">

### Advanced IP Connection Limiter for PasarGuard Panel

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=20&pause=1000&color=8B0000&center=true&vCenter=true&width=500&lines=Sharingan-sharp+IP+Tracking;Real--time+SSE+Log+Streaming;Telegram+%2B+CLI+%2B+REST+API;Redis--cached%2C+Battle--tested" alt="Typing SVG" />

![Python](https://img.shields.io/badge/Python-3.10+-8B0000?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL--3.0-8B0000)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-8B0000)
![Version](https://img.shields.io/badge/Version-1.0.0-8B0000)
![PasarGuard](https://img.shields.io/badge/PasarGuard-5.3.0%2B-8B0000)
![Docker](https://img.shields.io/badge/Docker-Supported-8B0000)
![Redis](https://img.shields.io/badge/Redis-Optional-8B0000)

Monitor • Limit • Warn • Recover — Telegram Bot • CLI • REST API • Web Dashboard

<a href="https://nowpayments.io/donation/MattDev" target="_blank" rel="noreferrer noopener">
    <img src="https://nowpayments.io/images/embeds/donation-button-black.svg" alt="Crypto donation button by NOWPayments">
</a>

</div>

---

<p align="center">
  <b>Monitor and limit concurrent IP connections per user with real-time SSE log streaming,</b>
  <br>
  Telegram bot control, REST API, CLI interface, Redis caching, and intelligent warning system.
</p>

---

<div align="center">

[Credits](#-credits--attribution) • [License](#-license) • [Compatibility](#-pasarguard-compatibility) • [Features](#-features) • [Installation](#-installation) • [Telegram Bot](#-telegram-bot) • [REST API](#-rest-api) • [Web Dashboard](#-web-dashboard-new) • [FAQ](#-faq)

</div>

---

## 📜 Credits / Attribution

**Original author:** [MatinDehghanian](https://github.com/MatinDehghanian)
— original repository: <https://github.com/MatinDehghanian/PG-Limiter>

This is a **modified version** maintained by **[CIAUB](https://github.com/CIAUB)**
at <https://github.com/CIAUB/PG-Limiter>. See [NOTICE.md](NOTICE.md) and
[CREDITS.md](CREDITS.md) for the full attribution chain, and
[CHANGELOG.md](CHANGELOG.md) for what was changed.

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3
(AGPLv3)** — the same license as the upstream project. See the
[LICENSE](LICENSE) file for the complete, unmodified license text. The
project-level copyright notice (MatinDehghanian as the original author,
CIAUB as the fork maintainer) lives in [NOTICE.md](NOTICE.md).

---

## 🔧 Modifications

This fork adds PasarGuard panel v5.3.0+ compatibility, an API-key
authentication path, a shared HTTP connection pool, bulk enable/disable
operations, a single-file web dashboard, typed response models, and
unified retry helpers. See [CHANGELOG.md](CHANGELOG.md) for the full
list of what changed and when.

---

## 🧩 PasarGuard Compatibility

This fork is fully compatible with **PasarGuard panel v5.3.0+** (the
current `main` branch, OpenAPI spec version 5.3.0). Compared to the
upstream 0.9.8 release:

```text
Endpoints (/api/admin/token, /api/users, /api/user/{username},
/api/nodes, /api/groups, /api/admins, /api/user/{username}/revoke_sub)
        │
        ▼
Still canonical in v5.x — existing code keeps working as-is
        │
        ▼
New user fields (id, subscription_url, note, next_plan, group_names,
proxy_settings) parsed via typed dataclasses in _models.py
        │
        ▼
New lightweight endpoints used where they help:
  • GET /api/users/simple   → cheap population enumeration
  • GET /api/nodes/simple   → fast node lists
  • POST /api/users/bulk/disable | /bulk/enable → bulk ops
        │
        ▼
Auth extended with API key support (pg_key_<uuid>) via
X-Api-Key / Authorization: ApiKey headers
        │
        ▼
Connection-pooled httpx.AsyncClient (optional HTTP/2)
        │
        ▼
Token expiry read from access_token_expires_minutes (5% margin)
        │
        ▼
Unified async_retry decorator (backoff + jitter) across
auth.py / users.py / nodes.py / bulk ops
```

The CLI gains a `bulk` subcommand:

```bash
python cli_main.py bulk disable alice bob
python cli_main.py bulk enable --from-file users.txt
```

> 💡 The 0.9.x behaviour is preserved when none of the new env vars are set, so existing deployments need no config changes.

---

## ✨ Features

### Core Features

* 🔒 **IP Limiting** — limit concurrent connections per user (global or per-user)
* 📊 **Real-time Monitoring** — SSE-based log streaming from all nodes
* 🤖 **Telegram Bot** — full control with inline keyboards and buttons
* 🖥️ **CLI Interface** — manage everything from command line
* 🌐 **REST API** — HTTP API for external integrations
* 🌍 **Country Filtering** — count only IPs from specific countries (IR, RU, CN)
* ⚠️ **Warning System** — monitor period before disabling users
* 🔄 **Auto Recovery** — automatic user re-enabling after timeout
* 📁 **Group-based Disable** — move users to restricted group instead of disabling
* 📱 **Multi-node Support** — monitor all connected PasarGuard nodes
* 🆕 **Web Dashboard** — single-file dashboard served by the API server (no CDN, no static mount)
* ⚡ **Bulk Operations** — disable/enable many users at once via CLI or REST API

### Advanced Features

* 🚀 **Redis Caching** — high-performance caching with Redis (in-memory fallback)
* 📝 **Enhanced Logging** — comprehensive logging with file rotation and colored output
* 🏗️ **Modular Architecture** — clean, maintainable codebase with separated handlers
* 👤 **Admin Filter** — filter users by admin ownership
* 👥 **Group Filter** — only monitor specific user groups
* ⚖️ **Punishment System** — auto-escalate penalties for repeat violators
* 🔍 **ISP Detection** — detect and cache ISP information for IPs
* 💿 **SQLite Database** — fast persistent storage with async support
* 🐳 **Docker + Redis** — production-ready Docker Compose setup
* 🧰 **Shared HTTP Pool** — connection-pooled `httpx.AsyncClient` reused across all panel calls (HTTP/2 optional)
* 🔁 **Unified Retry Helpers** — `async_retry` decorator with exponential backoff + jitter
* 🧪 **Typed API Models** — `UserResponse`/`NodesResponse`/etc. dataclasses for clean parsing
* 🔐 **API Key Auth** — `PANEL_API_KEY` (`pg_key_<uuid>`) supported as an alternative to username/password

### Data Management

* 💾 **Backup/Restore** — backup and restore all settings via Telegram
* 🚫 **Exception List** — exclude specific users from limiting
* 🧹 **Auto Cleanup** — remove deleted users from limiter config
* 🔍 **Smart Skip** — skip disabling users that don't exist in panel

---

## 📋 Requirements

```text
Python 3.10+
PasarGuard Panel (latest version)
Telegram Bot Token (from @BotFather)
Redis (optional, but recommended for production)
```

---

## 🛠 Installation

### Quick Install with Docker (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/MatinDehghanian/PG-Limiter/main/pg-limiter.sh -o /tmp/pg-limiter.sh
sudo bash /tmp/pg-limiter.sh install
```

This will:

```text
1 ─ Install Docker (if not present)
2 ─ Create configuration at /etc/opt/pg-limiter/
3 ─ Store data at /var/lib/pg-limiter/
4 ─ Guide you through interactive setup
```

### 🖥️ Management Commands

```text
pg-limiter start      # Start the service
pg-limiter stop       # Stop the service
pg-limiter restart    # Restart the service
pg-limiter status     # Show service status
pg-limiter logs       # View logs (follow mode)
pg-limiter update     # Update to latest version
pg-limiter backup     # Create backup zip
pg-limiter restore    # Restore from backup
pg-limiter config     # Edit configuration
pg-limiter uninstall  # Remove PG-Limiter
```

### Manual Installation (Without Docker)

```bash
git clone https://github.com/MatinDehghanian/PG-Limiter.git
cd PG-Limiter

pip install -r requirements.txt

cp .env.example .env
nano .env

python3 limiter.py
```

### 📂 Directory Structure

| مسیر | توضیح |
| --- | --- |
| `/etc/opt/pg-limiter/` | Configuration files (.env, docker-compose.yml) |
| `/var/lib/pg-limiter/` | Persistent data (database, logs) |
| `/var/lib/pg-limiter/data/` | SQLite database |

Docker volumes:

```text
/var/lib/pg-limiter/  → Persistent storage for database and logs
redis-data             → Redis persistence (AOF enabled)
```

### Fixing "externally-managed-environment" Error

```bash
# Option 1: Use system package (Ubuntu/Debian)
sudo apt install python3-httpx python3-aiohttp

# Option 2: Use --break-system-packages
pip3 install -r requirements.txt --break-system-packages

# Option 3: Use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Configuration is split into two parts:

* **Environment variables (.env)** — static settings like panel credentials, bot token, admin IDs
* **Database** — dynamic settings that can be changed via Telegram bot

### Environment Variables (.env)

```bash
# Panel Settings (Required)
# Either PANEL_USERNAME/PANEL_PASSWORD OR PANEL_API_KEY is required.
PANEL_DOMAIN=your-panel.com:PORT
PANEL_USERNAME=admin
PANEL_PASSWORD=your_password
# PANEL_API_KEY=pg_key_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Telegram Bot (Required)
BOT_TOKEN=123456:ABC-YOUR-BOT-TOKEN
ADMIN_IDS=123456789,987654321

# Limiter Settings
GENERAL_LIMIT=2
CHECK_INTERVAL=60
TIME_TO_ACTIVE_USERS=900
COUNTRY_CODE=IR

# API Server (Optional) - also serves the dashboard
API_ENABLED=false
API_HOST=0.0.0.0
API_PORT=8080
API_USERNAME=admin
API_PASSWORD=secret

# HTTP client tuning (NEW)
HTTP_POOL_SIZE=100
HTTP2_ENABLED=false
PANEL_REQUEST_TIMEOUT=30
# PANEL_INSECURE=false

# Redis Cache (Optional - falls back to in-memory if unavailable)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Timezone
TZ=Asia/Tehran

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/pg_limiter.db
```

### Configuration Options

| گزینه | نوع | پیش‌فرض | توضیح |
|--------|------|---------|-------------|
| `PANEL_DOMAIN` | string | - | Panel address with port |
| `PANEL_USERNAME` | string | admin | Panel admin username |
| `PANEL_PASSWORD` | string | - | Panel admin password |
| `PANEL_API_KEY` | string | - | PasarGuard v5+ API key; takes precedence over password |
| `PANEL_SCHEME` | string | "" | Force `https` or `http` (default: auto-fallback) |
| `PANEL_INSECURE` | bool | false | Skip TLS cert verification |
| `PANEL_REQUEST_TIMEOUT` | float | 30 | Per-request timeout in seconds |
| `HTTP_POOL_SIZE` | int | 100 | Max concurrent connections per host |
| `HTTP2_ENABLED` | bool | false | Enable HTTP/2 (needs `httpx[http2]`) |
| `BOT_TOKEN` | string | - | Telegram bot token |
| `ADMIN_IDS` | string | - | Comma-separated admin chat IDs |
| `GENERAL_LIMIT` | int | 2 | Default IP limit for all users |
| `CHECK_INTERVAL` | int | 60 | Check interval in seconds |
| `TIME_TO_ACTIVE_USERS` | int | 900 | Re-enable timeout in seconds |
| `COUNTRY_CODE` | string | "" | Filter IPs by country (IR/RU/CN) |
| `REDIS_URL` | string | redis://localhost:6379/0 | Redis connection URL |
| `REDIS_PASSWORD` | string | "" | Redis password (optional) |

### Dynamic Settings (via Telegram Bot)

```text
Special Limits        — Per-user custom limits
Except Users           — Users excluded from limiting
Disable Method         — status or group
Disabled Group ID      — Group ID for group-based disable
Enhanced Details       — Show detailed ISP info
Punishment System      — Auto-escalate repeat violators
Group Filter           — Only monitor specific user groups
Admin Filter           — Filter users by admin ownership
```

---

## 🤖 Telegram Bot

### Main Menu

```text
🏠 Main Menu
├── ⚙️ Settings      → Configure bot settings
├── 🎯 Limits        → Manage IP limits
├── 👥 Users         → Manage users & disabled list
├── 📡 Monitoring    → View connection status
├── 📊 Reports       → Generate reports
└── 👑 Admin         → Manage bot admins
```

### Settings Menu

| گزینه | توضیح |
|--------|-------------|
| 🔧 Panel Config | Set panel domain, username, password |
| 🌍 Country Code | Filter IPs by country (IR, RU, CN, None) |
| 🔑 IPInfo Token | Set IPInfo API token for location data |
| ⏱️ Check Interval | How often to check connections (60-300s) |
| ⏰ Active Time | Time before re-enabling users (300-1800s) |
| 📋 Enhanced Details | Show detailed node/protocol info |
| 1️⃣ Single IP Users | Show/hide single IP users in logs |
| 🚫 Disable Method | Choose between status or group-based disable |

### Limits Menu

| گزینه | توضیح |
|--------|-------------|
| 🎯 Set Special Limit | Set custom limit for specific user |
| 📋 Show Special Limits | View all users with custom limits |
| 🔢 Set General Limit | Set default limit for all users |

### Users Menu

| گزینه | توضیح |
|--------|-------------|
| ➕ Add Except User | Add user to exception list |
| ➖ Remove Except User | Remove user from exceptions |
| 📋 Show Except Users | View exception list |
| 🚫 Disabled Users | View/manage disabled users |
| ✅ Enable All | Re-enable all disabled users |
| 🧹 Cleanup Deleted | Remove users deleted from panel |

### Commands

| دستور | توضیح |
|---------|-------------|
| `/start` | Show main menu |
| `/help` | Show all commands |
| `/backup` | Download config backup |
| `/restore` | Restore from backup file |

---

## 🖥️ CLI Interface

Run CLI commands with `python cli_main.py`:

### User Limits

```bash
python cli_main.py user list
python cli_main.py user add USERNAME 5
python cli_main.py user delete USERNAME
python cli_main.py user update USERNAME 10
```

### Exception Users

```bash
python cli_main.py except list
python cli_main.py except add USERNAME
python cli_main.py except delete USERNAME
python cli_main.py except check USERNAME
```

### Disabled Users

```bash
python cli_main.py disabled list
python cli_main.py disabled enable USERNAME
python cli_main.py disabled enable-all
```

### Configuration

```bash
python cli_main.py config show
python cli_main.py config set-limit 3
python cli_main.py config set-interval 120
python cli_main.py config set-reenable-time 1800
python cli_main.py config set-country IR
python cli_main.py config cleanup
```

### Bulk operations (NEW)

```text
Try native /api/users/bulk/* endpoint
        │
        ▼
Fallback → concurrent per-user PUTs
```

```bash
# Disable three users at once
python cli_main.py bulk disable alice bob charlie

# Re-enable from a file (one username per line)
python cli_main.py bulk enable --from-file users.txt

# Skip the confirmation prompt
python cli_main.py bulk disable --yes alice bob
```

---

## 🌐 Web Dashboard (NEW)

A minimal, dependency-free web dashboard is bundled with the REST API
server. No templates, no static mount, no CDN — a single HTML file that
polls `/api/dashboard/state` every 5 seconds.

```bash
python api_server.py
```

```
http://localhost:8307/dashboard
```

It shows:

```text
Panel domain + auth mode (password vs API key)
Counts: disabled users, special limits, except users
Current general_limit, check_interval, country_code
Panel health (HTTPS/HTTP failure counts, last successful scheme,
consecutive failures, availability)
```

```bash
curl -u admin:secret http://localhost:8307/api/dashboard/state | jq
```

Bulk endpoints:

```bash
curl -u admin:secret -X POST http://localhost:8307/users/bulk/disable \
  -H "Content-Type: application/json" \
  -d '{"usernames": ["alice", "bob", "carol"]}'

curl -u admin:secret -X POST http://localhost:8307/users/bulk/enable \
  -H "Content-Type: application/json" \
  -d '{"usernames": ["alice", "bob"]}'
```

---

## 🌐 REST API

```bash
python api_server.py
```

Runs on port `8307` by default — docs at `http://localhost:8307/docs`

### Authentication

```text
HTTP Basic Auth using Telegram admin credentials
Username: admin
Password: First admin's chat ID from config
```

### Endpoints

| متد | مسیر | توضیح |
|--------|----------|-------------|
| GET | `/` | Welcome message |
| GET | `/status` | Get limiter status |
| GET | `/users/limits` | List all special limits |
| POST | `/users/limits` | Add special limit |
| PUT | `/users/limits/{username}` | Update limit |
| DELETE | `/users/limits/{username}` | Remove limit |
| GET | `/users/except` | List except users |
| POST | `/users/except` | Add except user |
| DELETE | `/users/except/{username}` | Remove except user |
| GET | `/users/disabled` | List disabled users |
| POST | `/users/disabled/{username}/enable` | Enable user |
| POST | `/users/disabled/enable-all` | Enable all users |
| GET | `/config` | Get full config |
| PUT | `/config/limit` | Set general limit |
| PUT | `/config/interval` | Set check interval |
| PUT | `/config/reenable-time` | Set re-enable time |
| PUT | `/config/country` | Set country filter |
| POST | `/cleanup` | Remove deleted users from config |

### Example Requests

```bash
curl -u admin:123456789 http://localhost:8307/status

curl -u admin:123456789 -X POST \
  http://localhost:8307/users/limits \
  -H "Content-Type: application/json" \
  -d '{"username": "vip_user", "limit": 5}'

curl -u admin:123456789 -X POST \
  http://localhost:8307/users/disabled/john_doe/enable

curl -u admin:123456789 -X POST \
  http://localhost:8307/cleanup
```

---

## 🚫 Disable Methods

### Status-based (Default)

```json
{
  "disable_method": "status",
  "disabled_group_id": null
}
```

User cannot connect at all — status shows as "disabled" in panel.

### Group-based (New)

```json
{
  "disable_method": "group",
  "disabled_group_id": 5
}
```

```text
When user exceeds limit → Original groups saved → Moved to disabled group
        │
        ▼
After timeout (or manual enable) → Original groups restored
```

**Setup via Telegram:**

```text
1 ─ Go to Settings → 🚫 Disable Method
2 ─ Click 📁 Use Group
3 ─ Select a group from the list
```

---

## 🚀 Redis Caching

### Cache TTL Settings

| نوع کش | TTL | توضیح |
|------------|-----|-------------|
| Token | 30 min | Panel API access tokens |
| Nodes | 1 hour | Node list and status |
| Config | 5 min | Dynamic configuration |
| ISP | 7 days | IP-to-ISP mappings |
| Panel Users | 1 min | User list from panel |

### Docker Compose with Redis

```yaml
services:
  pg-limiter:
    image: ghcr.io/matindehghanian/pg-limiter:latest
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 128mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
```

### Running Without Redis

```text
In-memory cache is used automatically if:
  • Redis is not installed
  • REDIS_URL is not set
  • Redis connection fails
```

---

## 📝 Logging

| خروجی | توضیح |
|--------|-------------|
| Console | Colored output for easy reading |
| File | Rotating log files in `/var/lib/pg-limiter/logs/` |
| Telegram | Critical errors sent to admins |

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

| فایل | توضیح |
|------|-------------|
| `limiter.log` | Main application logs |
| `api.log` | API request/response logs |
| `telegram.log` | Telegram bot logs |

---

## 🏗️ Project Architecture

```text
PG-Limiter/
├── limiter.py              # Main entry point
├── api_server.py           # REST API server + dashboard routes (NEW)
├── cli_main.py             # CLI interface
├── run_telegram.py         # Telegram bot runner
│
├── api/                    # NEW — dashboard
│   ├── __init__.py
│   └── dashboard.html      # Self-contained UI (no external deps)
│
├── telegram_bot/
│   ├── main.py            # Bot initialization
│   ├── keyboards.py       # Inline keyboards
│   └── handlers/          # Modular command handlers
│       ├── admin.py       # Admin management
│       ├── backup.py      # Backup/restore
│       ├── limits.py      # Limit management
│       ├── monitoring.py  # Connection monitoring
│       ├── punishment.py  # Punishment system
│       ├── reports.py     # Report generation
│       ├── settings.py    # Bot settings
│       └── users.py       # User management
│
├── utils/
│   ├── redis_cache.py     # Redis caching layer
│   ├── logs.py            # Logging configuration
│   ├── isp_detector.py    # ISP detection
│   ├── read_config.py     # Configuration management
│   └── panel_api/         # Panel API client
│       ├── auth.py        # Authentication (+ API-key support)
│       ├── users.py       # User operations (+ get_users_simple)
│       ├── nodes.py       # Node operations (+ get_nodes_simple)
│       ├── groups.py      # Group operations
│       ├── admins.py      # Admin operations
│       ├── bulk.py        # NEW — bulk enable/disable
│       ├── _connection.py # NEW — shared httpx.AsyncClient
│       ├── _models.py     # NEW — typed response models
│       ├── _retry.py      # NEW — async_retry decorator
│       └── request_helper.py  # Common request plumbing
│
├── cli/                    # CLI subcommands
│   ├── user.py
│   ├── except_user.py
│   ├── disabled.py
│   ├── config.py
│   └── bulk.py            # NEW — bulk enable/disable
│
└── db/
    ├── database.py        # Database connection
    ├── models.py          # SQLAlchemy models
    └── crud/              # Database operations
        ├── config.py
        ├── users.py
        ├── limits.py
        └── violations.py
```

---

## ❓ FAQ

<details>
<summary><b>Why do IP counts decrease over time?</b></summary>

The SSE implementation is stable. If issues occur:
- Check node connectivity
- Verify panel logs are enabled
- Try restarting the limiter
</details>

<details>
<summary><b>Why do connections persist after disabling?</b></summary>

This is Xray core behavior. Active connections remain until:
- Client reconnects
- Connection times out
- Client closes the connection
</details>

<details>
<summary><b>Do I need to restart after config changes?</b></summary>

No, changes apply automatically within seconds.
</details>

<details>
<summary><b>Can I run on a different server?</b></summary>

Yes, the limiter works on any server with network access to your panel.
</details>

<details>
<summary><b>No logs appearing?</b></summary>

1. Ensure xray log level is set to `info`:
```json
{
  "log": {
    "loglevel": "info"
  }
}
```

2. For HAProxy, add `option forwardfor` to config.
</details>

<details>
<summary><b>How to run as a service?</b></summary>

```bash
sudo nano /etc/systemd/system/pg-limiter.service
```

```ini
[Unit]
Description=PG-Limiter Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/limiter
ExecStart=/usr/bin/python3 limiter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pg-limiter
sudo systemctl start pg-limiter
```
</details>

<details>
<summary><b>How to use cron for auto-restart?</b></summary>

```bash
crontab -e
```

```bash
# Restart every 6 hours
0 */6 * * * cd /path/to/limiter && python3 limiter.py

# Run on reboot
@reboot cd /path/to/limiter && python3 limiter.py
```
</details>

<details>
<summary><b>Is Redis required?</b></summary>

No, Redis is optional. PG-Limiter automatically falls back to in-memory caching if Redis is unavailable. However, Redis is recommended for production as it provides:
- Cache persistence across restarts
- Better performance for high-traffic scenarios
- Shared cache for multiple instances
</details>

<details>
<summary><b>How do I check cache status?</b></summary>

```text
✓ Redis cache connected
```
or
```text
⚠ Redis not available, using in-memory cache fallback
```
</details>

---

## 📄 License

This project is licensed under the **AGPL-3.0 License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author & Maintainer

* **Original author / upstream:** [MatinDehghanian](https://github.com/MatinDehghanian) — [MatinDehghanian/PG-Limiter](https://github.com/MatinDehghanian/PG-Limiter)
* **This fork is maintained by:** [CIAUB](https://github.com/CIAUB)

This fork builds on the original 0.9.8 release by MatinDehghanian and
extends it to track the current PasarGuard panel API (v5.3.0+). All
upstream attribution is preserved — see [CREDITS.md](CREDITS.md) for the
full history.

---

## 🙏 Credits

Based on [V2IpLimit](https://github.com/houshmand-2005/V2IpLimit) by [houshmand-2005](https://github.com/houshmand-2005), adapted and enhanced for PasarGuard panel by [MatinDehghanian](https://github.com/MatinDehghanian), and further developed and maintained in this fork by [CIAUB](https://github.com/CIAUB). See [CREDITS.md](CREDITS.md).

---

<p align="center">
<img src="https://raw.githubusercontent.com/CIAUB/CIAUB/main/sharingan.jpg" width="500" alt="Sharingan" />
</p>

---

# 📞 ارتباط با توسعه‌دهنده

* 👨‍💻 Telegram: https://t.me/CIAUB
* 🐙 GitHub: https://github.com/CIAUB

---

### ⭐ Support

If you find this project useful, please give it a ⭐, or support with a crypto donation from the button at the top of the page.

<sub><sub>Original work by MatinDehghanian — maintained as an AGPL-3.0 fork by CIAUB</sub></sub>
