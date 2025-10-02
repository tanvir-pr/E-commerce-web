# ADR 0003: Mandatory TOTP for staff

## Status

Accepted (Part 3)

## Context

Super admin and staff accounts must not receive a session from password alone.

## Decision

- Password login for staff returns `next=enroll` or `next=challenge` and sets a short-lived `__Host-enroll` / `__Host-challenge` JWT cookie.
- `__Host-access` and `__Host-refresh` are issued only after TOTP confirm or challenge (or a one-time recovery code).
- TOTP secrets are Fernet-encrypted with `TOTP_ENCRYPTION_KEY`.
- Staff permissions are deny-by-default: `support`, `warehouse`, `moderation`. Super admin bypasses permission checks.
- Customers still sign in with password only.

## Consequences

The seeded owner must enroll an authenticator before `/admin` works. Recovery codes are shown once at enrollment.
