# Security fix pass 1 — access-control cluster (state as of 2026-06-10)

Scope: user-roles / permissions / access-control findings from `SECURITY.md`
(C-1, C-2, H-1, H-2, H-5, M-1, plus the C-1 corollaries). Branch: `fix/security`.
Backend code changes are committed in `5c1ba28`; test changes are in the working
tree (not yet committed).

## Policy decisions (confirmed with project owner)

1. **`PATCH /users/me` + `POST /users/change-password` → Guest+.**
   Account-lifecycle exception: any logged-in, email-verified account (including
   guests) may manage its OWN profile and password. Guests remain read-only for
   all app data.
2. **Spectating/leaderboard → Guest+ (no anonymous access).**
   Leaderboard, match list/get, and the SSE stream all require a verified login.
   Consequence: the frontend `useMatchStream` hook must switch from `EventSource`
   (cannot send Authorization headers) to fetch-based SSE — pending, see TODO.
3. **M-1 ownership policy:** non-admin callers of `POST /matches` must own at
   least one participating agent (403 otherwise). Admins and the internal match
   scheduler are exempt. The only UI that creates matches is the admin page, so
   no user flow breaks.

## Implemented (committed in `5c1ba28`)

### C-2 — worker key no longer becomes a synthetic ADMIN
- `backend/app/api/deps/auth.py`: removed the `is_worker` fallback in
  `get_current_user`; JWT auth and worker-key auth are fully separate.
- `backend/app/api/deps/permissions.py`: new named dependencies:
  - `VerifiedGuestOrHigher` — JWT + email verified (read tier)
  - `VerifiedUserOrHigher` — JWT + verified + role ≥ USER (mutation tier)
  - `AdminOnly` — alias of `CurrentAdmin`
  - `WorkerOrVerifiedUser` (`RequestActor`) — valid `x-api-key` OR verified JWT
    user; used ONLY on the four worker-read endpoints. Worker gets no User
    identity; ownership checks for JWT users stay in the route.

### C-1 — worker callbacks require `x-api-key` (also closes L-2 dup, L-3 dup)
`Depends(require_worker_api_key)` (403 without valid key, JWT is NOT accepted) on:
- `PATCH /jobs/build/{id}`, `PATCH /jobs/match/{id}`, `POST /jobs`
- `PATCH /matches/{id}` (the "no authentication" comment is removed)
- `POST /agent_containers/upsert`, `PATCH /agent_containers/{id}`

### C-2 migration — worker reads kept working
`WorkerOrVerifiedUser` on:
- `GET /submissions/{id}`, `GET /submissions/{id}/download` (owner/admin if JWT)
- `GET /agents/{id}` (owner/admin if JWT)
- `GET /matches/{id}` — **fourth worker read not listed in the original brief**:
  the match worker calls it at run time (`orchestration/lib/match_manager.py:212`).

### H-1 — guests are read-only
`VerifiedUserOrHigher` on: `POST/PATCH/DELETE /agents`, `POST/DELETE /submissions`,
`POST /matches`. `VerifiedGuestOrHigher` on list/read routes. `PATCH /users/me`
and `POST /users/change-password` stay Guest+ per decision 1 (now also require
email verification; previously bare JWT).

### H-2 — anonymous reads removed
`VerifiedGuestOrHigher` on: `GET /agents/leaderboard/{game}`, `GET /matches`,
`GET /matches/{id}/stream`, `GET /agent_containers`. `GET /jobs/build/{id}` is
worker-or-(submission-owner/admin); `GET /jobs/match/{id}` is worker-or-Guest+.
Scheduler config GET/PUT switched from inline role checks to `CurrentAdmin`.

### H-5 — agent stats not user-writable
- `AgentUpdate` reduced to `name` + `active_submission_id`, `extra="forbid"`
  → PATCH with `elo`/`wins`/… returns **422**.
- Stat-write block removed from `AgentService.update_agent`; stats flow only
  through `MatchService._update_agent_stats` (match completion).
- Note: admins also lose API-level stat editing (accepted).

### M-1 — match-creation ownership
- `MatchService.create_match(..., owner_user_id=...)`; when set, at least one
  agent must belong to that user, else `MatchPermissionError` → **403**.
- Route passes `None` for admins; scheduler (direct service call) unaffected.

## Tests (working tree, not yet committed)

New `backend/tests/api/test_permissions.py` (~51 tests):
1. Anonymous deny-by-default across 38 non-lifecycle routes (param. matrix).
2. Verified guest: can read app data; 403 on every create/update/delete even
   for resources it owns; can still edit own profile (Guest+ lifecycle).
3. Cross-user ownership: non-owner USER gets 403 on agent/submission
   get/patch/delete/download.
4. USER role cannot reach user-management/scheduler admin routes.
5. Worker callbacks: anon + guest/user/admin JWT + bad key → 403; valid key → 200.
6. Worker key cannot reach any JWT route (users, scheduler config, agents,
   matches, submissions lists, /users/me, mutations) → 401/403.
7. Worker key CAN still read/download submissions, read agents, read matches.
8. H-5: stat-field PATCH → 422 and DB values unchanged; match completion via
   worker `PATCH /matches/{id}` still updates wins/losses/elo.
9. M-1: USER creating match with only others' agents → 403; with own agent → 201;
   admin with arbitrary agents → 201.

Updated existing tests:
- `test_users.py`: added `_set_user_role` + `_create_member_and_token` (USER-role
  helper); `_create_admin_and_token` refactored onto `_set_user_role`.
- `test_jobs.py`: worker endpoints now called with `x-api-key` header.
- `test_submissions_and_agents.py`: uses `_create_member_and_token` (mutations
  need USER role now); empty-agents assertion scoped to the test's own user.
- `tests/conftest.py`: new autouse fixture closing the global
  `match_event_publisher` Redis connection between tests (mirrors
  `reset_job_queue`; fixes cross-test event-loop reuse).

### Local test status
Run against `backend/docker-compose.test.yml` (Postgres :5433, Redis :6380) with
`TEST_DATABASE_URL/DATABASE_URL/REDIS_URL` overridden and
`BYPASS_EMAIL_VERIFICATION=false` (root `.env` enables the dev bypass, which
breaks the email-verification helpers):
- Last full run: **83 passed, 1 failed** — the failure
  (`test_submission_upload_does_not_create_agent`) was test pollution (global
  "agents table empty" assertion vs. session-scoped schema); fixed by scoping
  the assertion to the test's user. Full-suite re-run pending.

## TODO (remaining)

1. Re-run full backend suite (expect green) and commit test changes.
2. Frontend:
   - L-1: role-aware `ProtectedRoute` (admin pages `users`, `containers`,
     `matches-admin` gated by role; backend remains source of truth).
   - Rewrite `useMatchStream.ts` from `EventSource` to fetch-based SSE so the
     Authorization header reaches the now-protected stream endpoint.
3. `SECURITY.md`: flip statuses for C-1, C-2, H-1, H-2, H-5, M-1 (+ L-2/L-3
   dups), correct the route-matrix "Current auth" column, document the two
   policy decisions above.
