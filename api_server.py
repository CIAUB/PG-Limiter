"""
REST API Server for Limiter
Run with: python api_server.py
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config files
CONFIG_FILE = "config.json"
BACKUP_FILE = "backup.json"
DISABLED_USERS_FILE = ".disable_users.json"

# Security
security = HTTPBasic()

# ═══════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════

class UserLimit(BaseModel):
    username: str
    limit: int

class UpdateLimit(BaseModel):
    limit: int

class ExceptUser(BaseModel):
    username: str

class DisabledUser(BaseModel):
    username: str
    disabled_at: float
    elapsed_seconds: int

class StatusResponse(BaseModel):
    general_limit: int
    check_interval: int
    reenable_time: int
    special_limits_count: int
    except_users_count: int
    disabled_users_count: int

class ConfigResponse(BaseModel):
    limits: Dict
    timing: Dict
    users: Dict
    settings: Dict

# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def load_config() -> dict:
    """Load config from file"""
    if not os.path.exists(CONFIG_FILE):
        raise HTTPException(status_code=500, detail="Config file not found")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config: dict):
    """Save config to file"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def load_backup() -> dict:
    """Load backup file"""
    if not os.path.exists(BACKUP_FILE):
        return {"special": {}, "except_users": []}
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_backup(backup: dict):
    """Save backup file"""
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2)

def load_disabled_users() -> dict:
    """Load disabled users"""
    if not os.path.exists(DISABLED_USERS_FILE):
        return {}
    try:
        with open(DISABLED_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "disabled_users" in data:
                return data["disabled_users"]
            elif "disable_user" in data:
                old_users = data.get("disable_user", [])
                if isinstance(old_users, list):
                    return {user: time.time() for user in old_users}
                return old_users
            return {}
    except:
        return {}

def save_disabled_users(users: dict):
    """Save disabled users"""
    with open(DISABLED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"disabled_users": users}, f, indent=2)


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify API credentials"""
    config = load_config()
    api_config = config.get("api", {})
    
    correct_username = api_config.get("username", "admin")
    correct_password = api_config.get("password", "admin")
    
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        correct_username.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ═══════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("🚀 Limiter API Server starting...")
    yield
    logger.info("🛑 Limiter API Server shutting down...")


app = FastAPI(
    title="Limiter API",
    description="REST API for IP Connection Limiter Management",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# Routes - Status
# ═══════════════════════════════════════════════════════════════

@app.get("/", tags=["Status"])
async def root():
    """API root - health check"""
    return {"status": "ok", "message": "Limiter API is running"}


@app.get("/status", response_model=StatusResponse, tags=["Status"])
async def get_status(username: str = Depends(verify_credentials)):
    """Get current limiter status"""
    config = load_config()
    disabled = load_disabled_users()
    
    limits = config.get("limits", {})
    timing = config.get("timing", {})
    users = config.get("users", {})
    
    return StatusResponse(
        general_limit=limits.get("general", 2),
        check_interval=timing.get("check_interval", 120),
        reenable_time=timing.get("time_to_active_users", 300),
        special_limits_count=len(limits.get("special", {})),
        except_users_count=len(users.get("except", [])),
        disabled_users_count=len(disabled)
    )


# ═══════════════════════════════════════════════════════════════
# Routes - User Limits
# ═══════════════════════════════════════════════════════════════

@app.get("/users/limits", tags=["User Limits"])
async def list_user_limits(username: str = Depends(verify_credentials)):
    """List all users with special limits"""
    config = load_config()
    backup = load_backup()
    
    special_limits = {}
    if "limits" in config and "special" in config["limits"]:
        special_limits.update(config["limits"]["special"])
    if "special" in backup:
        special_limits.update(backup["special"])
    
    return {
        "success": True,
        "data": [
            {"username": k, "limit": v}
            for k, v in sorted(special_limits.items())
        ]
    }


@app.get("/users/limits/{user}", tags=["User Limits"])
async def get_user_limit(user: str, username: str = Depends(verify_credentials)):
    """Get a specific user's limit"""
    config = load_config()
    backup = load_backup()
    
    limit = None
    if "limits" in config and "special" in config["limits"]:
        limit = config["limits"]["special"].get(user)
    if limit is None and "special" in backup:
        limit = backup["special"].get(user)
    
    general = config.get("limits", {}).get("general", 2)
    
    return {
        "success": True,
        "data": {
            "username": user,
            "limit": limit if limit is not None else general,
            "is_special": limit is not None,
            "general_limit": general
        }
    }


@app.post("/users/limits", tags=["User Limits"])
async def add_user_limit(user_limit: UserLimit, username: str = Depends(verify_credentials)):
    """Add or update a user's special limit"""
    config = load_config()
    backup = load_backup()
    
    if "limits" not in config:
        config["limits"] = {}
    if "special" not in config["limits"]:
        config["limits"]["special"] = {}
    if "special" not in backup:
        backup["special"] = {}
    
    config["limits"]["special"][user_limit.username] = user_limit.limit
    backup["special"][user_limit.username] = user_limit.limit
    
    save_config(config)
    save_backup(backup)
    
    return {"success": True, "message": f"Limit for {user_limit.username} set to {user_limit.limit}"}


@app.put("/users/limits/{user}", tags=["User Limits"])
async def update_user_limit(user: str, update: UpdateLimit, username: str = Depends(verify_credentials)):
    """Update a user's special limit"""
    config = load_config()
    backup = load_backup()
    
    if "limits" not in config:
        config["limits"] = {}
    if "special" not in config["limits"]:
        config["limits"]["special"] = {}
    if "special" not in backup:
        backup["special"] = {}
    
    config["limits"]["special"][user] = update.limit
    backup["special"][user] = update.limit
    
    save_config(config)
    save_backup(backup)
    
    return {"success": True, "message": f"Limit for {user} updated to {update.limit}"}


@app.delete("/users/limits/{user}", tags=["User Limits"])
async def delete_user_limit(user: str, username: str = Depends(verify_credentials)):
    """Delete a user's special limit"""
    config = load_config()
    backup = load_backup()
    
    removed = False
    
    if "limits" in config and "special" in config["limits"]:
        if user in config["limits"]["special"]:
            del config["limits"]["special"][user]
            save_config(config)
            removed = True
    
    if "special" in backup and user in backup["special"]:
        del backup["special"][user]
        save_backup(backup)
        removed = True
    
    if not removed:
        raise HTTPException(status_code=404, detail=f"User {user} not found in special limits")
    
    return {"success": True, "message": f"Special limit for {user} removed"}


# ═══════════════════════════════════════════════════════════════
# Routes - Except Users
# ═══════════════════════════════════════════════════════════════

@app.get("/users/except", tags=["Except Users"])
async def list_except_users(username: str = Depends(verify_credentials)):
    """List all except (whitelisted) users"""
    config = load_config()
    backup = load_backup()
    
    except_users = set()
    if "users" in config and "except" in config["users"]:
        except_users.update(config["users"]["except"])
    if "except_users" in backup:
        except_users.update(backup["except_users"])
    
    return {
        "success": True,
        "data": sorted(list(except_users))
    }


@app.post("/users/except", tags=["Except Users"])
async def add_except_user(user: ExceptUser, username: str = Depends(verify_credentials)):
    """Add a user to the except list"""
    config = load_config()
    backup = load_backup()
    
    if "users" not in config:
        config["users"] = {}
    if "except" not in config["users"]:
        config["users"]["except"] = []
    if "except_users" not in backup:
        backup["except_users"] = []
    
    if user.username in config["users"]["except"] or user.username in backup["except_users"]:
        raise HTTPException(status_code=400, detail=f"User {user.username} is already in except list")
    
    config["users"]["except"].append(user.username)
    backup["except_users"].append(user.username)
    
    save_config(config)
    save_backup(backup)
    
    return {"success": True, "message": f"User {user.username} added to except list"}


@app.delete("/users/except/{user}", tags=["Except Users"])
async def delete_except_user(user: str, username: str = Depends(verify_credentials)):
    """Remove a user from the except list"""
    config = load_config()
    backup = load_backup()
    
    removed = False
    
    if "users" in config and "except" in config["users"]:
        if user in config["users"]["except"]:
            config["users"]["except"].remove(user)
            save_config(config)
            removed = True
    
    if "except_users" in backup and user in backup["except_users"]:
        backup["except_users"].remove(user)
        save_backup(backup)
        removed = True
    
    if not removed:
        raise HTTPException(status_code=404, detail=f"User {user} not found in except list")
    
    return {"success": True, "message": f"User {user} removed from except list"}


# ═══════════════════════════════════════════════════════════════
# Routes - Disabled Users
# ═══════════════════════════════════════════════════════════════

@app.get("/users/disabled", tags=["Disabled Users"])
async def list_disabled_users_route(username: str = Depends(verify_credentials)):
    """List all currently disabled users"""
    disabled = load_disabled_users()
    current_time = time.time()
    
    data = []
    for user, disabled_time in disabled.items():
        elapsed = int(current_time - disabled_time)
        data.append({
            "username": user,
            "disabled_at": disabled_time,
            "disabled_at_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(disabled_time)),
            "elapsed_seconds": elapsed
        })
    
    return {
        "success": True,
        "data": sorted(data, key=lambda x: x["disabled_at"], reverse=True)
    }


@app.delete("/users/disabled/{user}", tags=["Disabled Users"])
async def enable_disabled_user(user: str, username: str = Depends(verify_credentials)):
    """Enable a disabled user (remove from disabled list)"""
    disabled = load_disabled_users()
    
    if user not in disabled:
        raise HTTPException(status_code=404, detail=f"User {user} is not in disabled list")
    
    del disabled[user]
    save_disabled_users(disabled)
    
    return {"success": True, "message": f"User {user} removed from disabled list"}


@app.delete("/users/disabled", tags=["Disabled Users"])
async def enable_all_disabled_users(username: str = Depends(verify_credentials)):
    """Enable all disabled users (clear the disabled list)"""
    disabled = load_disabled_users()
    count = len(disabled)
    
    save_disabled_users({})
    
    return {"success": True, "message": f"Cleared {count} users from disabled list"}


# ═══════════════════════════════════════════════════════════════
# Routes - Configuration
# ═══════════════════════════════════════════════════════════════

@app.get("/config", tags=["Configuration"])
async def get_config(username: str = Depends(verify_credentials)):
    """Get current configuration (sensitive data masked)"""
    config = load_config()
    
    # Mask sensitive data
    if "panel" in config:
        if "password" in config["panel"]:
            config["panel"]["password"] = "***"
    if "telegram" in config:
        if "bot_token" in config["telegram"]:
            config["telegram"]["bot_token"] = "***"
    if "api" in config:
        if "password" in config["api"]:
            config["api"]["password"] = "***"
    
    return {"success": True, "data": config}


@app.put("/config/limits/general", tags=["Configuration"])
async def set_general_limit(limit: int = Query(..., ge=1), username: str = Depends(verify_credentials)):
    """Set the general IP limit"""
    config = load_config()
    
    if "limits" not in config:
        config["limits"] = {}
    
    config["limits"]["general"] = limit
    save_config(config)
    
    return {"success": True, "message": f"General limit set to {limit}"}


@app.put("/config/timing/check_interval", tags=["Configuration"])
async def set_check_interval(interval: int = Query(..., ge=30), username: str = Depends(verify_credentials)):
    """Set the check interval in seconds"""
    config = load_config()
    
    if "timing" not in config:
        config["timing"] = {}
    
    config["timing"]["check_interval"] = interval
    save_config(config)
    
    return {"success": True, "message": f"Check interval set to {interval} seconds"}


@app.put("/config/timing/reenable_time", tags=["Configuration"])
async def set_reenable_time(seconds: int = Query(..., ge=60), username: str = Depends(verify_credentials)):
    """Set the time to automatically re-enable disabled users"""
    config = load_config()
    
    if "timing" not in config:
        config["timing"] = {}
    
    config["timing"]["time_to_active_users"] = seconds
    save_config(config)
    
    return {"success": True, "message": f"Re-enable time set to {seconds} seconds"}


# ═══════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════

class CleanupResult(BaseModel):
    special_limits_removed: List[str]
    except_users_removed: List[str]
    disabled_users_removed: List[str]
    user_groups_backup_removed: List[str]
    total_removed: int


@app.post("/cleanup", response_model=CleanupResult, tags=["Maintenance"])
async def cleanup_deleted_users(username: str = Depends(verify_credentials)):
    """
    Clean up users from limiter config that no longer exist in the panel.
    Removes deleted users from: special limits, except_users, disabled_users, and user groups backup.
    """
    from utils.read_config import read_config
    from utils.types import PanelType
    from utils.panel_api import cleanup_deleted_users as do_cleanup
    
    try:
        config = await read_config()
        panel_config = config.get("panel", {})
        
        if not panel_config.get("domain"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Panel not configured"
            )
        
        panel_data = PanelType(
            panel_username=panel_config.get("username", ""),
            panel_password=panel_config.get("password", ""),
            panel_domain=panel_config.get("domain", ""),
            panel_api_key=panel_config.get("api_key") or None,
        )

        result = await do_cleanup(panel_data)
        
        total_removed = (
            len(result["special_limits_removed"]) +
            len(result["except_users_removed"]) +
            len(result["disabled_users_removed"]) +
            len(result["user_groups_backup_removed"])
        )
        
        return CleanupResult(
            special_limits_removed=result["special_limits_removed"],
            except_users_removed=result["except_users_removed"],
            disabled_users_removed=result["disabled_users_removed"],
            user_groups_backup_removed=result["user_groups_backup_removed"],
            total_removed=total_removed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════
# Bulk operations (NEW — PasarGuard v5+/PG-Limiter)
# ═══════════════════════════════════════════════════════════════

class BulkRequest(BaseModel):
    usernames: List[str]


class BulkResponse(BaseModel):
    succeeded: List[str]
    failed: List[str]
    not_found: List[str]
    total: int


async def _build_panel_data() -> "PanelType":
    """Helper that returns a `PanelType` populated from the live config."""
    from utils.read_config import read_config
    from utils.types import PanelType
    config = await read_config()
    panel_config = config.get("panel", {})
    if not panel_config.get("domain"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Panel not configured",
        )
    return PanelType(
        panel_username=panel_config.get("username", ""),
        panel_password=panel_config.get("password", ""),
        panel_domain=panel_config.get("domain", ""),
        panel_api_key=panel_config.get("api_key") or None,
    )


@app.post(
    "/users/bulk/disable",
    response_model=BulkResponse,
    tags=["Bulk"],
    summary="Disable many users at once",
)
async def bulk_disable(
    body: BulkRequest,
    username: str = Depends(verify_credentials),
):
    """
    Disable multiple users. Tries the native
    `/api/users/bulk/disable` panel endpoint first, and falls back to
    concurrent per-user PUTs if the panel doesn't support it.
    """
    if not body.usernames:
        return BulkResponse(succeeded=[], failed=[], not_found=[], total=0)
    from utils.panel_api import bulk_disable_users as api_bulk_disable

    try:
        panel = await _build_panel_data()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")

    try:
        result = await api_bulk_disable(panel, body.usernames)
        d = result.as_dict()
        return BulkResponse(
            succeeded=d["succeeded"],
            failed=d["failed"],
            not_found=d["not_found"],
            total=len(body.usernames),
        )
    except Exception as e:
        logger.error(f"bulk_disable failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/users/bulk/enable",
    response_model=BulkResponse,
    tags=["Bulk"],
    summary="Enable many users at once",
)
async def bulk_enable(
    body: BulkRequest,
    username: str = Depends(verify_credentials),
):
    """
    Re-enable multiple users. Tries the native
    `/api/users/bulk/enable` panel endpoint first, and falls back to
    concurrent per-user PUTs if the panel doesn't support it.
    """
    if not body.usernames:
        return BulkResponse(succeeded=[], failed=[], not_found=[], total=0)
    from utils.panel_api import bulk_enable_users as api_bulk_enable

    try:
        panel = await _build_panel_data()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")

    try:
        result = await api_bulk_enable(panel, body.usernames)
        d = result.as_dict()
        return BulkResponse(
            succeeded=d["succeeded"],
            failed=d["failed"],
            not_found=d["not_found"],
            total=len(body.usernames),
        )
    except Exception as e:
        logger.error(f"bulk_enable failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# Dashboard (NEW — single-file, dependency-free)
# ═══════════════════════════════════════════════════════════════

class DashboardState(BaseModel):
    generated_at: str
    panel_domain: str
    auth_mode: str  # "password" | "api_key"
    config: dict
    counts: dict
    health: dict
    recent_logs: List[str]


@app.get("/dashboard", tags=["Dashboard"], response_class=HTMLResponse)
async def dashboard_page(username: str = Depends(verify_credentials)):
    """Return the single-file dashboard UI."""
    try:
        with open("api/dashboard.html", "r", encoding="utf-8") as fh:
            return HTMLResponse(content= fh.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>api/dashboard.html missing</h1>",
            status_code=500,
        )


@app.get(
    "/api/dashboard/state",
    response_model=DashboardState,
    tags=["Dashboard"],
    summary="Aggregated state for the dashboard UI",
)
async def dashboard_state(username: str = Depends(verify_credentials)):
    """
    Aggregate a JSON snapshot of the limiter for the dashboard UI.
    Backed by the same files/config the CLI uses, plus panel health.
    """
    from utils.panel_api import get_panel_health

    config = load_config()
    panel_cfg = config.get("panel", {}) or {}
    auth_mode = "api_key" if panel_cfg.get("api_key") else "password"

    # Disabled users (uses the legacy JSON store, same as the CLI).
    disabled: list[str] = []
    try:
        with open(DISABLED_USERS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            du = data.get("disabled_users") or data.get("disable_user") or {}
            if isinstance(du, dict):
                disabled = list(du.keys())
            elif isinstance(du, list):
                disabled = du
    except FileNotFoundError:
        pass
    except Exception as e:  # noqa: BLE001
        logger.warning(f"dashboard: failed to read disabled users: {e}")

    counts = {
        "special_limits": len((config.get("limits") or {}).get("special") or {}),
        "except_users": len(config.get("users", {}).get("except", []) or []),
        "disabled_users": len(disabled),
    }

    return DashboardState(
        generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        panel_domain=panel_cfg.get("domain", ""),
        auth_mode=auth_mode,
        config={
            "general_limit": (config.get("limits") or {}).get("general"),
            "check_interval": config.get("timing", {}).get("check_interval")
                or config.get("monitoring", {}).get("check_interval")
                or config.get("check_interval"),
            "time_to_active_users": config.get("timing", {}).get("time_to_active_users")
                or config.get("time_to_active_users"),
            "country_code": config.get("country_code"),
        },
        counts=counts,
        health=get_panel_health(),
        recent_logs=[],  # Could be wired to a ring buffer; left empty for now.
    )


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    # Load config for API settings
    try:
        config = load_config()
        api_config = config.get("api", {})
        host = api_config.get("host", "0.0.0.0")
        port = api_config.get("port", 8307)
    except:
        host = "0.0.0.0"
        port = 8307
    
    print(f"""
╔═══════════════════════════════════════════╗
║         🛡️  LIMITER API  🛡️               ║
║     REST API for IP Connection Limiter    ║
╠═══════════════════════════════════════════╣
║  Docs: http://{host}:{port}/docs          ║
╚═══════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host=host, port=port)
