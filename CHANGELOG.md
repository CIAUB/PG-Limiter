# Changelog

All notable changes to PG-Limiter are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-03

> **This release is the first published version of the CIAUB fork
> (<https://github.com/CIAUB/PG-Limiter>) of MatinDehghanian's
> PG-Limiter. All upstream attribution is preserved — see
> [CREDITS.md](CREDITS.md) and [NOTICE](NOTICE) for the full history.**

### Maintainer

- Original author (up to v0.9.8): **MatinDehghanian**
  <https://github.com/MatinDehghanian>
- This fork (v1.0.0+): **CIAUB** <https://github.com/CIAUB>

### Pasarguard compatibility

PG-Limiter is now fully compatible with **PasarGuard panel v5.3.0+**
(the current `main` branch, OpenAPI spec 5.3.0). All previously used
endpoints are still canonical; the fork adds support for new v5
features and several quality-of-life improvements.

### Added

- **API-key authentication** (PasarGuard v5+ `pg_key_<uuid>`). Set
  `PANEL_API_KEY` in `.env` (or pass `panel_api_key` programmatically)
  to authenticate without a `/api/admin/token` roundtrip. The key is
  sent via both `X-Api-Key` and `Authorization: ApiKey <key>` headers
  for cross-version safety. `utils/panel_api/auth.py`.
- **Lightweight user listing** via the new `/api/users/simple`
  endpoint — much cheaper than `/api/users` for population
  enumeration. `utils.panel_api.users.get_users_simple`.
- **Lightweight node listing** via `/api/nodes/simple`.
  `utils.panel_api.nodes.get_nodes_simple`.
- **Bulk user operations** that try the native
  `/api/users/bulk/{disable,enable}` endpoints first and fall back to
  concurrent per-user PUTs when the panel version doesn't support
  them. `utils.panel_api.bulk.{bulk_disable_users,bulk_enable_users,
  get_user_details_batch}`.
- **Bulk CLI subcommand**: `python cli_main.py bulk disable alice bob
  charlie` and `python cli_main.py bulk enable --from-file users.txt`.
- **Web dashboard** served by the existing API server at
  `GET /dashboard` (self-contained HTML, no CDN / no static mount /
  no template engine) with a JSON snapshot endpoint at
  `GET /api/dashboard/state`. Live counts, panel health, and config
  are surfaced.
- **REST bulk endpoints**: `POST /users/bulk/disable` and
  `POST /users/bulk/enable`.
- **Shared `httpx.AsyncClient`** used by every panel call. Honors
  `HTTP_POOL_SIZE` (default 100) and `HTTP2_ENABLED` (off by default
  to keep the install footprint minimal; switch on with
  `pip install httpx[http2]`). One TCP/TLS handshake per host, not
  one per call. `utils/panel_api/_connection.py`.
- **Unified retry helpers**: `async_retry` decorator with
  `RetryPolicy` (exponential backoff + jitter, `Retry-After` aware,
  HTTP-status classification). Replaces the ad-hoc retry loops that
  were previously duplicated in `auth.py`, `users.py`, `nodes.py`.
  `utils/panel_api/_retry.py`.
- **Typed response models** as light-weight dataclasses:
  `UserResponse`, `UserSimple`, `UsersResponse`, `UsersSimpleResponse`,
  `NodeResponse`, `NodesResponse`, `GroupResponse`, `GroupsResponse`,
  `AdminSummary`, `AdminsResponse`. `utils/panel_api/_models.py`.
- **Token TTL** is now read from the panel's
  `access_token_expires_minutes` field (with a 5% safety margin)
  instead of being hard-coded to 30 minutes.
- **New env vars**: `PANEL_API_KEY`, `PANEL_SCHEME`, `PANEL_INSECURE`,
  `PANEL_REQUEST_TIMEOUT`, `HTTP_POOL_SIZE`, `HTTP2_ENABLED`.
- **Test coverage**: `tests/test_pasarguard_compat.py` (16 smoke
  tests) and `tests/test_dashboard.py` (4 smoke tests).

### Changed

- `utils.check_usage.run_check_users_usage` now reads the polling
  interval through `utils.read_config.get_config_value(...)` instead
  of poking `data["monitoring"]["check_interval"]` directly. The CLI
  (`data["timing"]["check_interval"]`) and the main loop now read the
  same value; the historical `monitoring` / `timing` keys are
  retained as aliases for backward compat.
- `utils.read_config.read_config` accepts EITHER `PANEL_PASSWORD` OR
  `PANEL_API_KEY` for the `check_required_elements=True` path.
- `utils.types.PanelType` gained a `panel_api_key` attribute
  (optional, defaults to `None`).
- `utils.types.UserType` gained optional fields for the v5+
  `id`, `subscription_url`, `note`, and `next_plan` columns. All
  default to `None` so existing code paths are unaffected.
- `api_server.py` now passes `panel_api_key` into the
  `PanelType` it builds, so the bulk and dashboard endpoints honour
  the same auth method as the rest of the limiter.
- README restructured: a new **🧩 PasarGuard Compatibility** section
  at the top, a new **🌐 Web Dashboard** section, the bulk operations
  documented, and the architecture diagram updated.

### Fixed

- `monitoring.check_interval` (read by the limiter loop) and
  `timing.check_interval` (read by the CLI `status` command) used to
  disagree silently, with the loop defaulting to 60 s and the CLI to
  120 s. Both now resolve to the same `CHECK_INTERVAL` env var.

### Backward compatibility

- No existing env var is required; nothing breaks if you don't set
  any of the new ones.
- No endpoint or field used by the 0.9.x release has been removed or
  renamed.
- The HTTP client falls back to HTTP/1.1 when `h2` isn't installed
  (the `HTTP2_ENABLED` opt-in is no-op without the extra package).
- New `UserType` fields are optional and default to `None`; the
  existing `UserType` constructor call sites keep working.

## [0.9.8] - upstream

The previous release by `@MatinDehghanian`. See
[github.com/MatinDehghanian/PG-Limiter](https://github.com/MatinDehghanian/PG-Limiter)
for its history.
