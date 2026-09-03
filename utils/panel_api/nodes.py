"""
Node operations for panel API.
"""

import time

from utils.logs import get_logger
from utils.types import PanelType, NodeType
from utils.panel_api.auth import safe_send_logs_panel
from utils.panel_api.request_helper import panel_get
from utils.panel_api._models import NodesResponse, NodeResponse as _NodeResponseModel

# Try to import Redis cache
try:
    from utils.redis_cache import (
        get_cached_nodes, cache_nodes, invalidate_nodes as redis_invalidate_nodes
    )
    REDIS_CACHE_AVAILABLE = True
except ImportError:
    REDIS_CACHE_AVAILABLE = False

# Module logger
nodes_logger = get_logger("panel_api.nodes")

# Fallback in-memory nodes cache (1 hour cache)
_nodes_cache = {
    "nodes": None,
    "expires_at": 0,
    "panel_domain": None
}


async def invalidate_nodes_cache():
    """Invalidate the cached nodes list"""
    if REDIS_CACHE_AVAILABLE:
        try:
            await redis_invalidate_nodes(_nodes_cache.get("panel_domain", "default"))
        except Exception as e:
            nodes_logger.warning(f"Failed to invalidate Redis nodes cache: {e}")
    
    _nodes_cache["nodes"] = None
    _nodes_cache["expires_at"] = 0
    nodes_logger.info("🖥️ Nodes cache invalidated")


async def get_nodes(
    panel_data: PanelType,
    force_refresh: bool = False,
    enabled_only: bool = True,
) -> list[NodeType] | ValueError:
    """
    Get the IDs of all nodes from the panel API.
    Results are cached for 1 hour in Redis (or in-memory fallback).

    Args:
        panel_data (PanelType): A PanelType object containing
            the username, password, and domain for the panel API.
        force_refresh (bool): If True, bypass cache and fetch fresh nodes.
        enabled_only (bool): If True (default), only fetch enabled nodes.

    Returns:
        list[NodeType]: The list of IDs and other information of all nodes.

    Raises:
        ValueError: If the function fails to get the nodes from both the HTTP
        and HTTPS endpoints.
    """
    # Try Redis cache first
    if not force_refresh and REDIS_CACHE_AVAILABLE:
        try:
            cached_nodes = await get_cached_nodes(panel_data.panel_domain)
            if cached_nodes:
                # Convert cached dicts back to NodeType objects
                nodes_list = [
                    NodeType(
                        node_id=n["node_id"],
                        node_name=n["node_name"],
                        node_ip=n["node_ip"],
                        status=n["status"],
                        message=n.get("message", ""),
                    )
                    for n in cached_nodes
                ]
                nodes_logger.debug(f"🖥️ Using Redis cached nodes list ({len(nodes_list)} nodes)")
                return nodes_list
        except Exception as e:
            nodes_logger.warning(f"Redis cache error: {e}, falling back to in-memory")
    
    # Fallback: Check in-memory cache
    if not force_refresh and _nodes_cache["nodes"] is not None:
        current_time = time.time()
        # Check if cache is still valid and for same panel
        if (_nodes_cache["expires_at"] > current_time and 
            _nodes_cache["panel_domain"] == panel_data.panel_domain):
            time_left = int(_nodes_cache["expires_at"] - current_time)
            nodes_logger.debug(f"🖥️ Using in-memory cached nodes list (expires in {time_left // 60} minutes)")
            return _nodes_cache["nodes"]
    
    nodes_logger.info(f"🖥️ Fetching nodes from panel (force_refresh={force_refresh})...")
    
    # Build endpoint with optional enabled filter
    endpoint = "/api/nodes?enabled=true" if enabled_only else "/api/nodes"
    
    response = await panel_get(panel_data, endpoint, force_refresh=force_refresh)
    
    if response is None:
        message = (
            "Failed to get nodes after all retries. Make sure the panel is running "
            "and the username and password are correct."
        )
        await safe_send_logs_panel(message)
        nodes_logger.error(message)
        raise ValueError(message)
    
    try:
        user_inform = response.json()
    except Exception as json_error:
        nodes_logger.error(f"Failed to parse JSON: {json_error}")
        raise ValueError(f"Failed to parse nodes response: {json_error}")
    
    # Handle both list and dict responses
    nodes_list = None
    if isinstance(user_inform, list):
        nodes_list = user_inform
    elif isinstance(user_inform, dict):
        if "nodes" in user_inform:
            nodes_list = user_inform["nodes"]
        elif "data" in user_inform:
            nodes_list = user_inform["data"]
        else:
            nodes_logger.warning(f"Unexpected nodes dict structure. Keys: {list(user_inform.keys())}")
            if "id" in user_inform and "name" in user_inform:
                nodes_list = [user_inform]
            else:
                message = f"Cannot parse nodes from dict: {user_inform}"
                nodes_logger.error(message)
                raise ValueError(message)
    else:
        message = f"Nodes response is neither list nor dict: {type(user_inform)}"
        nodes_logger.error(message)
        raise ValueError(message)
    
    if not nodes_list or not isinstance(nodes_list, list):
        message = "Failed to extract nodes list from response"
        nodes_logger.error(message)
        raise ValueError(message)
    
    all_nodes = []
    for node in nodes_list:
        all_nodes.append(
            NodeType(
                node_id=node["id"],
                node_name=node["name"],
                node_ip=node["address"],
                status=node["status"],
                message=node.get("message", ""),
            )
        )
    
    # Cache the nodes list for 1 hour (3600 seconds)
    # Store in Redis if available
    if REDIS_CACHE_AVAILABLE:
        try:
            # Convert NodeType objects to dicts for JSON serialization
            nodes_dicts = [
                {
                    "node_id": n.node_id,
                    "node_name": n.node_name,
                    "node_ip": n.node_ip,
                    "status": n.status,
                    "message": n.message,
                }
                for n in all_nodes
            ]
            await cache_nodes(panel_data.panel_domain, nodes_dicts)
            nodes_logger.debug("🖥️ Nodes cached in Redis")
        except Exception as e:
            nodes_logger.warning(f"Failed to cache nodes in Redis: {e}")
    
    # Always store in in-memory cache as fallback
    _nodes_cache["nodes"] = all_nodes
    _nodes_cache["expires_at"] = time.time() + 3600
    _nodes_cache["panel_domain"] = panel_data.panel_domain
    
    nodes_logger.info(f"🖥️ Fetched {len(all_nodes)} nodes (cached for 1 hour)")
    for node in all_nodes:
        nodes_logger.debug(f"  └─ {node.node_name} (id={node.node_id}, status={node.status})")

    return all_nodes


async def get_nodes_simple(
    panel_data: PanelType,
    *,
    timeout: float = 15.0,
    enabled_only: bool = False,
) -> list[dict] | ValueError:
    """
    Fetch a lightweight list of nodes from `/api/nodes/simple`.

    Returns a list of `{id, name}` dicts. Cheaper than `get_nodes()` and
    intended for dashboards, health checks, and configuration screens
    that don't need the full node details.

    Args:
        panel_data:    Panel connection info.
        timeout:       Per-request timeout in seconds.
        enabled_only:  When True, only enabled nodes are returned.

    Returns:
        list of dicts with `id` and `name` keys.
    """
    nodes_logger.debug("🖥️ Fetching simple node list...")
    endpoint = "/api/nodes/simple"
    if enabled_only:
        endpoint += "?enabled=true"

    response = await panel_get(panel_data, endpoint, timeout=timeout, max_retries=2)
    if response is None:
        raise ValueError("Failed to fetch /api/nodes/simple")

    if response.status_code >= 400:
        nodes_logger.warning(
            f"/api/nodes/simple returned {response.status_code}: {response.text[:120]}"
        )
        raise ValueError(f"/api/nodes/simple returned {response.status_code}")

    try:
        parsed = NodesResponse.from_json(response.json())
    except Exception as exc:  # noqa: BLE001
        nodes_logger.error(f"Failed to parse /api/nodes/simple: {exc}")
        raise ValueError(f"Failed to parse /api/nodes/simple: {exc}")

    return [
        {"id": n.id, "name": n.name, "status": n.status, "enabled": n.enabled}
        for n in parsed.nodes
    ]
