# Authentication and learner identity

KHOLLELAB supports two deliberately separate identities. Every browser receives an
HttpOnly `khollelab_learner` UUID for anonymous use. A registered account receives a
new, stable `learner_id`; it is not derived from its email or anonymous UUID. While a
valid account session is present, existing learner-scoped services transparently use
that stable ID. Logging out returns the browser to its independent anonymous identity.

`user_accounts` stores the normalized email and an Argon2id password hash.
`auth_sessions` stores only the SHA-256 digest of a fresh 256-bit random opaque token.
The raw token exists only in the `khollelab_session` cookie, which is HttpOnly,
SameSite=Lax, Path=/, bounded to 30 days by default, and Secure in production.
Expired, revoked, or disabled-account sessions are rejected. `last_seen_at` is updated
at most hourly.

Registration can transactionally move all sessions belonging to the current anonymous
browser to the new account. Attempts, evaluations, and tutor assessments remain linked
and are never copied. Explicit post-login claiming provides the same operation and is
idempotent. If both identities have an active session for one problem, the account's
session wins: the anonymous session is retained as abandoned before ownership moves.

Login on another device immediately exposes the account's history, profile, and
adaptive evidence. It never silently claims that device's anonymous work. Logout
revokes the current session; logout-all revokes every session. Password changes keep
the current session and revoke all other devices.

The login/registration limiter is deliberately small and in-process. It is bounded but
not shared between replicas; production deployments should replace it with a shared
rate limiter. PR17 does not provide email verification, password reset, or social login.
Generated problems remain a global shared catalogue and contain no account identity.
