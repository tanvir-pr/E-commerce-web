# ADR 0002: Cookie sessions with rotating refresh

## Status

Accepted (Part 2)

## Context

Browser clients must stay signed in without storing tokens in `localStorage`. The Next.js app proxies `/api/v1` to FastAPI so cookies are first-party on `localhost:3000`.

## Decision

- Access token: short-lived HS256 JWT in `__Host-access` (HttpOnly, Secure, SameSite=Lax, Path=/).
- Refresh token: opaque random value stored only as SHA-256; cookie `__Host-refresh`. Rotated on every refresh. Reuse of a revoked refresh token revokes the whole family.
- CSRF: double-submit cookie `__Host-csrf` (not HttpOnly) must match header `X-CSRF-Token` on POST/PUT/PATCH/DELETE.
- Passwords: Argon2id, minimum 10 characters. `BREACH_CHECK=stub` skips Have I Been Pwned locally.

## Consequences

Chromium treats `http://localhost` as a secure context, so `__Host-` cookies work locally. Open the site as `http://localhost:3000`, not `http://127.0.0.1:3000`. Production must be HTTPS.
