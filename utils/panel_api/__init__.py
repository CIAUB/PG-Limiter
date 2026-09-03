"""
Panel API module for interacting with the PasarGuard panel.

This module provides functions to interact with the panel API including:
- Authentication and token management (auth.py + connection.py + retry.py)
- User operations (list, enable, disable, etc.) — users.py
- Node operations — nodes.py
- Group operations — groups.py
- Admin operations — admins.py
- Bulk operations — bulk.py
- Typed response models — _models.py
- Shared HTTP client — _connection.py
- Reusable retry helpers — _retry.py
"""

# Auth functions
from utils.panel_api.auth import (
    get_token,
    invalidate_token_cache,
    safe_send_logs_panel,
)

# User operations
from utils.panel_api.users import (
    all_user,
    get_all_panel_users,
    get_users_simple,        # NEW (lightweight /api/users/simple)
    check_user_exists,
    get_user_details,
    get_user_admin,
    update_user_groups,
    enable_all_user,
    enable_user_by_status,
    enable_user_by_group,
    enable_selected_users,
    disable_user_by_status,
    disable_user_by_group,
    disable_user,
    disable_user_with_punishment,
    enable_dis_user,
    cleanup_deleted_users,
    fix_stuck_disabled_users,
    get_users_in_disabled_group,
)

# Node operations
from utils.panel_api.nodes import (
    get_nodes,
    get_nodes_simple,        # NEW
    invalidate_nodes_cache,
)

# Group operations
from utils.panel_api.groups import (
    get_groups,
)

# Admin operations
from utils.panel_api.admins import (
    get_admins,
)

# Bulk operations (NEW)
from utils.panel_api.bulk import (
    bulk_disable_users,
    bulk_enable_users,
    get_user_details_batch,
    BulkResult,
)

# Typed models (NEW)
from utils.panel_api._models import (
    UserResponse,
    UserSimple,
    UsersResponse,
    UsersSimpleResponse,
    NodeResponse,
    NodesResponse,
    GroupResponse,
    GroupsResponse,
    AdminSummary,
    AdminsResponse,
)

# Connection management (NEW)
from utils.panel_api._connection import (
    get_panel_client,
    close_panel_client,
    reset_panel_client,
    panel_client_config,
)

# Retry helpers (NEW)
from utils.panel_api._retry import (
    RetryPolicy,
    async_retry,
    parse_retry_after,
    is_retryable_status,
    is_terminal_status,
)

# Request helper functions
from utils.panel_api.request_helper import (
    check_panel_availability,
    wait_for_panel,
    get_panel_health,
    reset_panel_health,
    is_panel_available,
)

__all__ = [
    # Auth
    "get_token",
    "invalidate_token_cache",
    "safe_send_logs_panel",
    # Users
    "all_user",
    "get_all_panel_users",
    "get_users_simple",
    "check_user_exists",
    "get_user_details",
    "get_user_admin",
    "update_user_groups",
    "enable_all_user",
    "enable_user_by_status",
    "enable_user_by_group",
    "enable_selected_users",
    "disable_user_by_status",
    "disable_user_by_group",
    "disable_user",
    "disable_user_with_punishment",
    "enable_dis_user",
    "cleanup_deleted_users",
    "fix_stuck_disabled_users",
    "get_users_in_disabled_group",
    # Nodes
    "get_nodes",
    "get_nodes_simple",
    "invalidate_nodes_cache",
    # Groups
    "get_groups",
    # Admins
    "get_admins",
    # Bulk
    "bulk_disable_users",
    "bulk_enable_users",
    "get_user_details_batch",
    "BulkResult",
    # Models
    "UserResponse",
    "UserSimple",
    "UsersResponse",
    "UsersSimpleResponse",
    "NodeResponse",
    "NodesResponse",
    "GroupResponse",
    "GroupsResponse",
    "AdminSummary",
    "AdminsResponse",
    # Connection
    "get_panel_client",
    "close_panel_client",
    "reset_panel_client",
    "panel_client_config",
    # Retry
    "RetryPolicy",
    "async_retry",
    "parse_retry_after",
    "is_retryable_status",
    "is_terminal_status",
    # Request helper
    "check_panel_availability",
    "wait_for_panel",
    "get_panel_health",
    "reset_panel_health",
    "is_panel_available",
]
