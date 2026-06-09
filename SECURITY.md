## Security Review Report — `game-ai-platform`

I completed an in-depth repository security review focused on backend auth/RBAC, worker callbacks, rate limiting, upload/orchestration, container execution, config safety, and test gaps. I did **not** implement code changes yet because the review uncovered several broad policy-impacting authorization changes that should be applied incrementally with tests.

---

## Executive Summary

The platform currently does **not** satisfy the intended Anonymous / Guest / User / Admin / Worker policy.

Most important issues:

1. **Critical:** Worker callback/mutation endpoints are unauthenticated and can be called anonymously.
2. **Critical:** `x-api-key` on normal JWT-protected routes is treated as an admin user, so worker API keys implicitly bypass user RBAC across the API.
3. **High:** Guest users can create, update, and delete resources because most mutating endpoints require only `get_current_user`, not verified `user` role.
4. **High:** Several match and leaderboard read endpoints are anonymous despite the intended “only landing/auth lifecycle anonymous” policy.
5. **High:** Rate limiting is incomplete, hard-coded, not centrally configurable, and absent on most app-data and worker endpoints.
6. **High:** Submission upload and ZIP/build pipeline lacks size/file-count/compression-ratio controls and Docker build network remains enabled.
7. **Medium:** Agent update schema/service allows user-controlled stat fields unless schema excludes them.
8. **Medium:** File deletion/download trusts DB-stored filesystem paths without containment validation.
9. **Medium:** Production safety settings are incomplete for worker key, rate-limit bypass controls, proxy trust controls, and centralized limit config.

---

# Prioritized Findings

## Critical

### C-1 — Anonymous users can mutate worker callback endpoints

**Affected files**

- `backend/app/api/routes/jobs.py:43-62`
- `backend/app/api/routes/jobs.py:92-108`
- `backend/app/api/routes/matches.py:117-137`
- `backend/app/api/routes/agent_containers.py:39-48`
- `backend/app/api/routes/agent_containers.py:51-65`

**Evidence**

Worker-intended mutation endpoints have no auth dependency:

- `PATCH /api/v1/jobs/build/{job_id}` updates build job status/logs/image IDs.
- `PATCH /api/v1/jobs/match/{job_id}` updates match job status.
- `PATCH /api/v1/matches/{match_id}` updates match status, logs, result, and game state.
- `POST /api/v1/agent_containers/upsert` writes telemetry snapshots.
- `PATCH /api/v1/agent_containers/{container_id}` updates container records.

**Exploit scenario**

An unauthenticated internet client can mark arbitrary builds as completed/failed, inject fake image tags/logs, corrupt match results, forge game states, manipulate leaderboard-affecting match outcomes, or pollute container telemetry.

**Impact**

Integrity compromise of submissions, matches, jobs, leaderboards, and operational telemetry. This can destroy competition fairness and may trigger workers to consume attacker-controlled state.

**Recommended fix**

- Add `Depends(require_worker_api_key)` to all worker callback endpoints.
- Do **not** allow JWT users/admins to call worker callbacks unless explicitly intended.
- Consider splitting routers:
  - `/worker/jobs/...`
  - `/worker/matches/...`
  - `/worker/agent-containers/...`
- Validate callback state transitions server-side.
- Bound `logs`, `result`, and `game_state` payload sizes.

**Suggested regression tests**

- Anonymous request to each worker callback returns `403`.
- JWT `guest`, `user`, and `admin` requests without `x-api-key` return `403`.
- Valid `x-api-key` succeeds.
- Invalid state transitions are rejected.

---

### C-2 — Worker API key is accepted as an admin identity on normal user routes

**Affected files**

- `backend/app/api/deps/auth.py:24-38`
- `backend/app/api/deps/auth.py:41-67`
- `backend/app/api/deps/permissions.py:16-37`

**Evidence**

`get_current_user()` calls `verify_worker_api_key`; if valid, it returns a synthetic user:

```python
User(
    id=UUID("00000000-0000-0000-0000-000000000000"),
    username="worker",
    role=UserRole.ADMIN,
    email_verified=True,
)
```

That synthetic user then passes `CurrentAdmin` and admin checks.

**Exploit scenario**

If a worker API key leaks from an orchestration container, compose env, CI logs, or host filesystem, the holder can call ordinary admin endpoints such as user listing, role updates, deletions, scheduler config, submission downloads, and agent/container admin APIs.

**Impact**

Full administrative compromise via a credential intended only for worker callbacks.

**Recommended fix**

- Remove worker API-key fallback from `get_current_user()`.
- Keep JWT user auth and worker API-key auth as separate dependencies.
- Worker endpoints should use only `require_worker_api_key`.
- Admin endpoints should use only JWT `CurrentAdmin`.

**Suggested regression tests**

- `x-api-key` alone cannot access `/api/v1/users`, `/api/v1/users/{id}/role`, `/api/v1/submissions/{id}/download`, `/api/v1/matches/scheduler/config`, etc.
- Valid admin JWT cannot call worker callback endpoints unless policy explicitly permits it.

---

## High

### H-1 — Guest users can perform mutations intended only for approved users/admins

**Affected files**

- `backend/app/api/routes/agents.py:15-33`
- `backend/app/api/routes/agents.py:85-121`
- `backend/app/api/routes/submissions.py:19-34`
- `backend/app/api/routes/submissions.py:102-116`
- `backend/app/api/routes/matches.py:82-98`
- `backend/app/api/routes/users.py:65-128`

**Evidence**

Most mutating routes require only `Depends(get_current_user)` or `CurrentUser`; they do not enforce:

- email verified, or
- minimum role `UserRole.USER`, or
- guest read-only semantics.

Examples:

- `POST /agents`
- `PATCH /agents/{agent_id}`
- `DELETE /agents/{agent_id}`
- `POST /submissions`
- `DELETE /submissions/{submission_id}`
- `POST /matches`
- `PATCH /users/me`
- `POST /users/change-password`

Login already blocks unverified users, so the main gap is **verified guests**.

**Exploit scenario**

A newly registered and verified guest can upload ZIPs, trigger Docker builds, create agents, create matches, consume worker resources, and mutate/delete their resources without being promoted to approved participant.

**Impact**

Competition policy bypass, resource exhaustion, untrusted code execution by unapproved accounts, and guest-to-user privilege escalation in practice.

**Recommended fix**

- Define explicit dependencies:
  - `VerifiedGuestOrHigher`
  - `VerifiedUserOrHigher`
  - `AdminOnly`
- Apply `VerifiedUserOrHigher` to resource mutations: agents, submissions, match creation.
- Keep guests read-only after login.
- Decide whether profile/password changes are allowed for guests; if “strictly read-only” is literal, restrict them too or document these as auth-lifecycle exceptions.

**Suggested regression tests**

- Verified guest receives `403` on all create/update/delete routes for agents, submissions, matches, jobs, containers, users/roles.
- Verified user can mutate only own allowed resources.
- Admin can manage admin resources.

---

### H-2 — Anonymous access exists beyond landing/auth lifecycle endpoints

**Affected files**

- `backend/app/api/routes/agents.py:35-44`
- `backend/app/api/routes/matches.py:101-113`
- `backend/app/api/routes/matches.py:140-152`
- `backend/app/api/routes/matches.py:155-230`
- `backend/app/api/routes/jobs.py:28-40`
- `backend/app/api/routes/jobs.py:77-89`

**Evidence**

Anonymous endpoints include:

- `GET /agents/leaderboard/{game_type}`
- `GET /matches/{match_id}`
- `GET /matches`
- `GET /matches/{match_id}/stream`
- `GET /jobs/build/{job_id}`
- `GET /jobs/match/{job_id}`

The SSE route explicitly states: “No authentication is required — spectating is public.”

**Exploit scenario**

Anonymous clients can enumerate matches, inspect match data/logs/results, stream game state, query job status, and potentially scrape operational data.

**Impact**

Policy violation, information disclosure, unauthenticated resource consumption via SSE, and possible job/result enumeration.

**Recommended fix**

- Require at least verified logged-in guest for all app-data endpoints unless explicitly designated landing API.
- If public leaderboards or public spectating are intentional, list them as landing/public exceptions and rate-limit aggressively.
- Add auth and connection limits to SSE.

**Suggested regression tests**

- Anonymous requests to every non-auth endpoint return `401` except explicit allowlist.
- Public allowlisted endpoints are documented and rate-limited.

---

### H-3 — Rate limiting is incomplete, hard-coded, and below required coverage

**Affected files**

- `backend/app/api/routes/auth.py:28,35,80,124,146`
- `backend/app/api/routes/email.py:35,42,79,121`
- `backend/app/api/routes/users.py:38,45,56,67,101,134,183,212,248,277`
- No rate-limit decorators observed on `agents.py`, `submissions.py`, `matches.py`, `jobs.py`, `agent_containers.py`.
- `backend/app/core/config.py:38` only has `RATE_LIMITING_ENABLED`.

**Evidence**

Existing limits are inconsistent with required defaults:

- Login is `30/minute;200/day`, required `10/minute + 60/hour`.
- Register is `20/hour`, required `6/minute + 40/hour`.
- Password reset request is `10/hour`, required `6/minute + 20/hour`.
- Email verification is `10/minute`, required `6/minute + 20/hour`.
- Most authenticated read/mutation/upload/match/worker routes have no limit.
- No observed settings for:
  - `RATE_LIMIT_BYPASS`
  - `DISABLE_IP_RATE_LIMITING`
  - `TRUST_PROXY_HEADERS`
  - per-category configurable limits.

**Exploit scenario**

Attackers can brute force auth flows more aggressively than intended, spam uploads/matches to exhaust workers, flood worker callbacks, hold SSE connections, scrape reads, and abuse admin endpoints if credentials are compromised.

**Impact**

DoS/resource exhaustion, credential attack amplification, and inability to tune limits for production/hackathon contexts.

**Recommended fix**

Centralize rate limiting:

- Add settings for all required categories.
- Use user-id keyed limits for authenticated routes.
- Use IP-keyed limits for anonymous routes unless `DISABLE_IP_RATE_LIMITING=true`.
- Ensure `RATE_LIMIT_BYPASS=true` is rejected in production.
- Ensure `RATE_LIMITING_ENABLED=false` disables all limits only intentionally.
- Add worker callback limits keyed by API key or exempt only in trusted private networks.

**Suggested regression tests**

- Settings expose all required rate-limit strings.
- Production rejects `RATE_LIMIT_BYPASS=true`.
- Limit decorators or middleware coverage exists for every route category.
- Authenticated user-id limits still work when IP limits are disabled.

---

### H-4 — Upload and ZIP/build handling lacks size, count, compression, and build-network protections

**Affected files**

- `backend/app/api/services/submission.py:36-82`
- `orchestration/lib/agent_builder.py:25-35`
- `orchestration/lib/agent_builder.py:187-236`

**Evidence**

Backend upload:

- Accepts `.zip` based only on filename suffix.
- Streams file to disk without max size enforcement.
- No content-type validation.
- No quota per user.

ZIP extraction:

- Has path traversal check, but no max uncompressed size, max file count, max nested depth, or compression ratio checks.

Docker build:

- `network_mode="default"` during image build.
- User-provided Docker context is copied directly into build context.
- Dockerfile base likely limits arbitrary Dockerfile execution because `Dockerfile.agent` is controlled, but user files and Python dependency/build behavior can still consume resources.

**Exploit scenario**

A verified guest/user uploads a ZIP bomb or huge archive to fill disk/memory, overload extraction/content hashing, cause expensive Docker builds, or use build-time package hooks/network access to fetch malicious/large resources.

**Impact**

Worker/backend DoS, disk exhaustion, network egress abuse during builds, and potentially supply-chain exposure.

**Recommended fix**

- Enforce max upload bytes at FastAPI/proxy/backend service level.
- Validate ZIP before saving/building:
  - max archive size
  - max uncompressed size
  - max file count
  - max path depth
  - reject symlinks/special files
  - reject absolute paths/path traversal robustly with `relative_to()`
- Add per-user submission quotas.
- Consider disabling Docker build network or restricting to a controlled dependency mirror.
- Add build timeout and Docker builder resource limits where possible.

**Suggested regression tests**

- Oversized upload rejected.
- ZIP bomb rejected.
- Path traversal rejected.
- Symlink/special file rejected.
- Excessive file count rejected.
- Guest cannot upload.

---

## Medium

### M-1 — Agent update appears to allow user-controlled stat manipulation

**Affected files**

- `backend/app/api/routes/agents.py:85-98`
- `backend/app/api/services/agent.py:103-113`
- `backend/app/schemas/agent.py` should be verified.

**Evidence**

`AgentService.update_agent()` applies these fields if present:

- `wins`
- `losses`
- `draws`
- `matches_played`
- `elo`

Route allows any owner or admin to call update.

**Exploit scenario**

If `AgentUpdate` exposes stat fields, a user can edit their own leaderboard stats and Elo.

**Impact**

Competition integrity compromise.

**Recommended fix**

- Remove stat fields from user-facing `AgentUpdate`.
- Create separate internal/admin/stat update method for match result processing.
- Only match completion service should update stats.

**Suggested regression tests**

- User cannot change Elo/wins/losses/draws/matches_played via API.
- Match completion still updates stats internally.

---

### M-2 — Submission download/delete trust DB-stored filesystem path

**Affected files**

- `backend/app/api/routes/submissions.py:76-84`
- `backend/app/api/services/submission.py:128-130`

**Evidence**

`submission.object_path` is converted directly to `Path` and used for download/delete.

**Exploit scenario**

If DB data is corrupted through another bug/admin misuse/migration issue, download may expose arbitrary local files and delete may remove arbitrary files accessible by the backend process.

**Impact**

Local file disclosure/deletion under compromised DB/admin conditions.

**Recommended fix**

- Store only object keys or relative filenames, not absolute paths.
- Resolve paths under configured `SUBMISSIONS_DIR` and verify containment with `Path.resolve().relative_to(base)`.
- Reject symlinks.

**Suggested regression tests**

- Object path outside upload directory is rejected for download/delete.
- Symlinked submission file is rejected.

---

### M-3 — Worker callback log/result/game-state payloads are unbounded

**Affected files**

- `backend/app/api/services/submission.py:87-108`
- `backend/app/api/services/match.py:72-114`
- `backend/app/api/routes/jobs.py:43-62`
- `backend/app/api/routes/matches.py:117-137`

**Evidence**

`job.logs += logs + "\n"` and `match.logs += logs + "\n"`; `result` and `game_state` are accepted as arbitrary dicts.

**Exploit scenario**

Anonymous attackers today, or compromised workers later, can submit huge logs/game states to fill DB/storage and degrade API responses/SSE streams.

**Impact**

DB bloat, memory pressure, slow clients, and DoS.

**Recommended fix**

- Add max log append size and max total stored log size.
- Add max JSON body size at proxy/app level.
- Validate `result` and `game_state` schemas per game type.
- Truncate logs server-side.

**Suggested regression tests**

- Oversized logs rejected or truncated.
- Oversized game state rejected.

---

### M-4 — Production config validation is incomplete

**Affected files**

- `backend/app/core/config.py:31-108`
- `backend/app/core/config.py:237-257`
- `.env.example`
- `backend/.env.example`
- `docker-compose*.yml`

**Evidence**

Config validates JWT secret length, production HTTPS CORS, SMTP requirements, token expiries, and turn timeouts. Missing or not observed:

- Production rejection of default `WORKER_API_KEY="dev-worker-key-12345"`.
- Required minimum worker API key entropy/length.
- `TRUST_PROXY_HEADERS=false` setting.
- `RATE_LIMIT_BYPASS` setting and production rejection.
- `DISABLE_IP_RATE_LIMITING` setting.
- Configurable per-category rate limits.
- Strong default `TRUSTED_HOSTS` requirement in production.

**Exploit scenario**

A deployment accidentally uses default worker key, bad rate-limit bypass, permissive proxy header trust, or incomplete host restrictions.

**Impact**

Credential compromise, rate-limit bypass, host-header issues, incorrect client IP attribution.

**Recommended fix**

- Add production startup validation for worker key, bypass flags, trusted hosts, and proxy headers.
- Add required settings to `.env.example` and `backend/.env.example`.
- Keep `TRUST_PROXY_HEADERS=false` by default.

**Suggested regression tests**

- Production config fails with default worker key.
- Production config fails with rate-limit bypass.
- Production config fails with insecure CORS/origin/host settings.

---

## Low / Informational

### L-1 — Frontend route guards should not be treated as security controls

**Affected area**

- `frontend/src/App.tsx`
- `frontend/src/context/`
- `frontend/src/pages/`
- `frontend/src/services/`

**Note**

Frontend UX should hide guest/user/admin controls appropriately, but backend enforcement is currently insufficient. Frontend guards should be updated after backend RBAC is corrected.

**Recommended fix**

- Hide mutation controls from guests.
- Hide admin navigation from non-admins.
- Ensure API errors are handled gracefully.

---

# Route Permission Matrix

Legend:

- **Anon** = no authentication
- **Guest+** = logged-in, email-verified guest or higher
- **User+** = approved participant or admin
- **Admin** = JWT admin only
- **WorkerKey** = `x-api-key` only, no JWT fallback

| Method | Path | Current auth | Intended auth | Ownership / notes |
|---|---|---:|---:|---|
| POST | `/auth/register` | Anon | Anon | Auth lifecycle |
| POST | `/auth/login` | Anon | Anon | Auth lifecycle |
| POST | `/auth/request-password-reset` | Anon | Anon | Auth lifecycle |
| POST | `/auth/reset-password` | Anon | Anon | Auth lifecycle |
| POST | `/email/verify-email` | Anon | Anon | Auth lifecycle |
| POST | `/email/resend-verification` | CurrentUser | CurrentUser/unverified allowed | Auth lifecycle exception |
| GET | `/email/verification-status` | CurrentUser | CurrentUser | OK |
| POST | `/email/{user_id}/resend-verification` | CurrentAdmin | Admin | OK, but worker key currently admin via C-2 |
| GET | `/users/roles` | CurrentUser | Guest+ or Admin-only? | If roles are admin resources, make Admin |
| GET | `/users/me` | CurrentUser | Guest+ | OK if login implies verified |
| PATCH | `/users/me` | CurrentUser | Policy decision; guest read-only suggests User+ or auth-lifecycle exception | Mutates profile/email |
| POST | `/users/change-password` | CurrentUser | Policy decision; likely Guest+ auth lifecycle | Mutates password |
| GET | `/users` | CurrentAdmin | Admin | OK except C-2 |
| GET | `/users/{user_id}` | CurrentAdmin | Admin | OK except C-2 |
| PATCH | `/users/{user_id}/role` | CurrentAdmin | Admin | OK except C-2 |
| DELETE | `/users/{user_id}` | CurrentAdmin | Admin | OK except C-2 |
| PATCH | `/users/{user_id}/verify-email` | CurrentAdmin | Admin | OK except C-2 |
| GET | `/agents/leaderboard/{game_type}` | Anon | Guest+ or explicit public landing exception | Public scrape risk |
| GET | `/agents` | CurrentUser | Guest+ read own; Admin all | OK for read |
| GET | `/agents/{agent_id}` | CurrentUser | Guest+/owner/admin depending data policy | Current users only owner/admin |
| POST | `/agents` | CurrentUser | User+ | Guest mutation gap |
| PATCH | `/agents/{agent_id}` | CurrentUser owner/admin | User+ owner/admin | Guest mutation gap; stat manipulation risk |
| DELETE | `/agents/{agent_id}` | CurrentUser owner/admin | User+ owner/admin | Guest mutation gap |
| GET | `/submissions` | CurrentUser | User+ own/admin, or Guest+ if no data | Lists own only |
| GET | `/submissions/{submission_id}` | CurrentUser owner/admin | Owner/admin; maybe User+ | OK except C-2 |
| GET | `/submissions/{submission_id}/download` | CurrentUser owner/admin | Owner/admin; worker should use WorkerKey-specific endpoint | Path containment risk |
| POST | `/submissions` | CurrentUser | User+ | Guest can upload/build |
| DELETE | `/submissions/{submission_id}` | CurrentUser owner/admin | User+ owner/admin | Guest mutation gap |
| GET | `/matches/scheduler/config` | CurrentUser + role check | Admin | OK except C-2 |
| PUT | `/matches/scheduler/config` | CurrentUser + role check | Admin | OK except C-2 |
| POST | `/matches` | CurrentUser | User+ | Guest can create matches; no ownership validation of agent IDs beyond build/game validity |
| GET | `/matches/{match_id}` | Anon | Guest+ or public exception | Anonymous app-data access |
| GET | `/matches` | Anon | Guest+ or public exception | Anonymous app-data access |
| GET | `/matches/{match_id}/stream` | Anon | Guest+ + stream limit, or public exception | Anonymous SSE DoS/scrape |
| PATCH | `/matches/{match_id}` | Anon | WorkerKey | Critical |
| GET | `/jobs/build/{job_id}` | Anon | WorkerKey/Admin or owner-visible limited | Anonymous job enum/data |
| PATCH | `/jobs/build/{job_id}` | Anon | WorkerKey | Critical |
| POST | `/jobs` | Anon | Admin/WorkerKey or remove | Anonymous build job creation |
| GET | `/jobs/match/{job_id}` | Anon | WorkerKey/Admin | Anonymous job enum/data |
| PATCH | `/jobs/match/{job_id}` | Anon | WorkerKey | Critical |
| GET | `/agent_containers` | CurrentUser | Admin all/User own | OK except C-2 |
| POST | `/agent_containers/upsert` | Anon | WorkerKey | Critical |
| PATCH | `/agent_containers/{container_id}` | Anon | WorkerKey/Admin? | Critical |

---

# Rate-Limit Coverage Matrix

| Category | Required default | Current status | Gap |
|---|---:|---|---|
| Login | `10/minute` + `60/hour` | `30/minute;200/day` | Too permissive / wrong window |
| Register | `6/minute` + `40/hour` | `20/hour` | Missing minute burst; wrong default |
| Email verification/password reset | `6/minute` + `20/hour` | Mixed: `10/minute`, `10/hour`, `5/minute`, `10/day` | Inconsistent, not category-configurable |
| Authenticated reads | `600/minute` + `10000/hour` | Mostly absent | Missing agents/submissions/matches/jobs/containers |
| Profile | `120/minute` | `60/minute`, `15/day` | Not aligned; possibly too strict for profile edit but missing config |
| General user mutations | `120/minute` + `2000/hour` | Mostly absent | Missing agent/submission/match mutations |
| Submission upload | `10/minute` + `60/hour` | Absent | High DoS risk |
| Match creation | `20/minute` + `200/hour` | Absent | High DoS risk |
| Match stream attempts | `60/minute` | Absent | SSE DoS risk |
| Worker callbacks | `1200/minute` | Absent | Critical unauth + no limit |
| Admin / API-key | `20000/minute` or exempt | `1000/hour` hard-coded for some admin; worker absent | Not configurable/inconsistent |
| Global toggle | `RATE_LIMITING_ENABLED=false` disables all | Present setting only | Need verify middleware integration |
| Dev/test bypass | `RATE_LIMIT_BYPASS=true` only non-prod | Missing | Add and validate |
| Disable IP limits | `DISABLE_IP_RATE_LIMITING=true` preserves user-id limits | Missing | Add keyed strategy |
| Proxy headers | `TRUST_PROXY_HEADERS=false` default | Missing | Add before trusting client IP |

---

# Orchestration / Container Execution Review

## Positive controls observed

- Runtime container defaults are reasonably hardened in `orchestration/secure_default_settings.yaml`:
  - `cap_drop: ["ALL"]`
  - `security_opt: ["no-new-privileges"]`
  - `read_only: true`
  - `tmpfs` with `noexec,nosuid,nodev`
  - `pids_limit: 256`
  - `mem_limit: 512m`
  - `nano_cpus: 1 CPU`
  - `network_mode: none`
- Runtime log capture in `orchestration/lib/agent_runner.py:15,95-110` limits logs to 5 MiB for `run_agent()`.
- ZIP extraction has path traversal validation in `orchestration/lib/agent_builder.py:25-35`.

## Risks

- Build-time network enabled: `orchestration/lib/agent_builder.py:235`.
- No ZIP bomb/file-count/uncompressed-size controls.
- Syntax-check container after build lacks explicit secure run kwargs in `orchestration/lib/agent_builder.py:238-243`.
- Worker image installs `docker.io` and likely requires Docker socket access in compose; Docker socket exposure is inherently high-risk and should be isolated.
- Build logs and match logs should be bounded server-side, not only runtime-captured client-side.

---

# Production-Hardening Checklist

Recommended startup/config checks:

- [ ] Reject production if `WORKER_API_KEY` equals default or is too short.
- [ ] Reject production if `JWT_SECRET_KEY` is default/weak; length validation already exists.
- [ ] Reject production if `RATE_LIMIT_BYPASS=true`.
- [ ] Add `TRUST_PROXY_HEADERS=false` default and only trust proxy headers when explicitly enabled and deployment is behind trusted proxy.
- [ ] Require `TRUSTED_HOSTS` in production.
- [ ] Keep production CORS HTTPS-only; already partly implemented.
- [ ] Ensure `BYPASS_EMAIL_VERIFICATION=true` has no production effect; current service checks `and not settings.is_production`, but config should also reject it in production for clarity.
- [ ] Add all rate-limit defaults to `.env.example` and `backend/.env.example`.
- [ ] Add upload size/quota settings.
- [ ] Add log/result/game-state max-size settings.
- [ ] Ensure Docker worker socket access is isolated from public-facing backend containers.
- [ ] Run workers on separate hosts or rootless/remote builders where possible.

---

# Missing Security Regression Tests

Add tests for:

1. Anonymous endpoint deny-by-default for every non-auth route.
2. Verified guest read-only policy.
3. User ownership for agents/submissions.
4. User cannot use another user’s submission as active agent submission.
5. User cannot mutate another user’s agent/submission.
6. Admin-only user/role management.
7. Worker callback endpoints require only `x-api-key`.
8. Worker API key cannot access JWT admin routes.
9. Admin JWT cannot call worker callback routes unless explicitly allowed.
10. Rate-limit categories and production bypass rejection.
11. Upload max size and ZIP bomb rejection.
12. ZIP path traversal/symlink/special-file rejection.
13. Submission path containment on download/delete.
14. User cannot edit Elo/wins/losses/draws via agent update.
15. SSE stream attempt rate limiting.

---

# Quick Wins vs Larger Refactors

## Quick wins

1. Add `Depends(require_worker_api_key)` to worker callback routes.
2. Remove worker API-key admin fallback from `get_current_user()`.
3. Add `VerifiedUserOrHigher` dependency and apply to:
   - `POST /agents`
   - `PATCH /agents/{id}`
   - `DELETE /agents/{id}`
   - `POST /submissions`
   - `DELETE /submissions/{id}`
   - `POST /matches`
4. Require auth on anonymous match/job routes unless documented public exceptions.
5. Add upload size validation.
6. Add production validation for default worker key.
7. Add tests for C-1, C-2, and guest read-only behavior first.

## Larger refactors

1. Centralized policy dependency module with named role dependencies.
2. Centralized configurable rate limiter with user-id/IP/API-key key functions.
3. Separate worker router/API namespace.
4. Object storage abstraction for submissions instead of absolute local paths.
5. Hardened build sandbox with controlled network/mirror, build timeouts, and resource limits.
6. Structured match result/game-state validation per game type.
7. Full endpoint inventory test that fails if a route lacks auth/rate-limit classification.

---

## Recommended Implementation Order

1. **Fix worker auth separation first** — this closes the most critical unauthenticated integrity bugs.
2. **Enforce guest read-only / User+ mutation policy.**
3. **Lock down anonymous route surface.**
4. **Add security regression tests for the above.**
5. **Implement centralized rate-limit settings and coverage.**
6. **Harden upload/ZIP/build pipeline.**
7. **Add production startup validation and update env examples.**

No code was changed in this pass.