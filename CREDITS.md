# Credits

This file lists everyone who has contributed to PG-Limiter, in
chronological order of when they joined the project. The fork
maintained here credits both the original author and the current
fork maintainer; nothing in this list is intended to replace or
override the AGPL-3.0 license under which the code is distributed.

## Original author

- **MatinDehghanian** — <https://github.com/MatinDehghanian>
  Created PG-Limiter in 2024 as an IP-connection limiter for the
  PasarGuard panel, building on his earlier work in the V2IpLimit
  ecosystem. All releases up to and including 0.9.8 are his.
  Upstream repository: <https://github.com/MatinDehghanian/PG-Limiter>

## Fork maintainer

- **CIAUB** — <https://github.com/CIAUB>
  Maintains the present fork, which targets the current PasarGuard
  panel API (v5.3.0+, OpenAPI spec 5.3.0). Adds API-key authentication,
  shared HTTP connection pooling, bulk enable/disable operations, a
  single-file web dashboard, typed response models, and unified retry
  helpers. See `CHANGELOG.md` for the full v1.0.0 changelog.

## Upstream project this work is based on

- **V2IpLimit** by [houshmand-2005](https://github.com/houshmand-2005)
  — <https://github.com/houshmand-2005/V2IpLimit>
  The original IP-limiting concept for the Marzban / PasarGuard
  ecosystem on which PG-Limiter is built.

## How to add yourself

If you contribute code, documentation, or translations to this fork,
please add a line under the **Fork maintainer** or a new section
above and open a pull request. The same applies to the upstream
repository at <https://github.com/MatinDehghanian/PG-Limiter>.
