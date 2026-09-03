# NOTICE

Project-level attribution for PG-Limiter. The full AGPLv3 license text
is in the [LICENSE](LICENSE) file in this directory. This NOTICE
exists so the project can credit both the original author and the
fork maintainer without modifying the AGPLv3 license body itself.

## Original project

- **Project:** PG-Limiter
- **Original Copyright (C) 2024-2026 MatinDehghanian**
- **Original Author:** MatinDehghanian
- **Original Repository:** <https://github.com/MatinDehghanian/PG-Limiter>

## This fork

This is a modified version.

- **Modifications Copyright (C) 2026 CIAUB**
- **Modified Repository:** <https://github.com/CIAUB/PG-Limiter>
- **Fork Maintainer:** CIAUB
- **Contact:** <https://github.com/CIAUB>

The full list of modifications is documented in
[CHANGELOG.md](CHANGELOG.md). Notable additions in this fork include:

- Compatibility with PasarGuard panel v5.3.0+ (OpenAPI spec 5.3.0).
- API-key authentication (`pg_key_<uuid>`) as an alternative to
  username/password.
- A shared `httpx.AsyncClient` connection pool with optional HTTP/2
  support.
- Unified retry helpers (`async_retry` with exponential backoff +
  jitter).
- Typed response models (`utils/panel_api/_models.py`).
- Bulk enable/disable operations with native-endpoint preference and
  per-user fallback.
- A single-file web dashboard served by the REST API at
  `/dashboard` (see AGPL §13 source-link notice in its footer).
- A new `bulk` subcommand in the CLI.
- New env vars: `PANEL_API_KEY`, `PANEL_SCHEME`, `PANEL_INSECURE`,
  `PANEL_REQUEST_TIMEOUT`, `HTTP_POOL_SIZE`, `HTTP2_ENABLED`.
- Fix for the historical `monitoring.check_interval` vs
  `timing.check_interval` config-key mismatch.
- Comprehensive tests for compatibility, the dashboard, and the CLI.

## Upstream project this work is based on

- **V2IpLimit** by [houshmand-2005](https://github.com/houshmand-2005) —
  <https://github.com/houshmand-2005/V2IpLimit>

## License notice

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program. If not, see
<https://www.gnu.org/licenses/>.

The full license text is reproduced verbatim in the [LICENSE](LICENSE)
file. The AGPLv3 license body is **unmodified**.
