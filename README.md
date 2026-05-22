# python_debugging_01

A Python web crawler service with several bugs. Your job is to make it correctly handle the workload the validator throws at it, within the resource envelope the platform provisions.

This is the first course on the [hardmode](https://github.com/h4rdm0d3) platform. The service ships as an HTTP server. A private validator hits it, scores your fixes, and shows you a red → amber → green progression.

## The contract

The service exposes:

### `POST /crawl`

Request:
```json
{ "urls": ["https://example.com/a", "https://example.com/b"], "mode": "batch" }
```

`mode` is optional.

- `"batch"` (the default) — fetches concurrently and returns once every fetch resolves.
- `"stream"` — fetches concurrently and returns as soon as the work is dispatched.

Both modes should produce the same eventual result set for the same input.

Response:
```json
{
  "results": [
    { "url": "https://example.com/a", "title": "A", "error": null },
    { "url": "https://example.com/b", "title": "B", "error": null }
  ],
  "stats": { "instance_seen": ["https://example.com/a", "https://example.com/b"] }
}
```

`stats.instance_seen` reports the URLs handled by the crawler instance that served the request.

### `GET /healthz`

Returns `{"ok": true}`. Used by the grader to know the service is up.

## How you're graded

The validator sends one workload to your service inside a constrained resource envelope and scores it across a handful of blackbox dimensions. Either your service meets the SLA bar or it doesn't — there's no per-bug attribution, no checklist of fixes.

**The dimensions** (each independent, each binary):

- **Completeness** — every input URL appears in the response, with `error` populated when applicable.
- **Dedup** — equivalent URLs collapse to one result; concurrent duplicates produce no extras.
- **Isolation** — per-request state doesn't bleed across requests.
- **Performance** — the workload finishes inside the wall-clock bar; no batch much slower than the baseline.
- **Stability** — re-running the workload back-to-back doesn't degrade.

Score is the count of passing dimensions × 20, in `[0, 100]`. Label:

- **red** — `score < 25`
- **amber** — `25 ≤ score < 100`
- **green** — `score == 100`

You see `{score, label}` only. No per-dimension breakdown, no validator-emitted explanations. The validator deliberately doesn't tell you *what* is failing — that's for you to figure out from your service's own behavior (and from the Grafana dashboards the platform exposes; see "Diagnostic surface" below).

## Resource envelope

The platform runs your service with:

- CPU: 200m
- Memory: 256Mi
- Network: egress restricted to the platform's fixture (no internet at grade time)

The dimension bars are calibrated for this envelope. Within 200m CPU and 256Mi memory, an approximately-correct service can't meet the performance and stability bars — fixing the bugs is the only way through. Local development runs without caps unless you opt in via the compose; do that before deciding your service is "done."

## Diagnostic surface

The platform attaches an HTTP sidecar to your service and ships per-session Prometheus + Grafana. The dashboards surface request rate, latency p50/p95/p99, error rates, status codes, and request-vs-response count gaps. They do not name bugs; they show symptoms. Form your hypotheses from the curves.

The local compose ships the same stack so you can iterate offline against the same dashboards you'll see during grading.

## Running locally

The repo ships a `compose.yaml` that brings up five services on a shared network:

- `fixture` — Wikipedia-shaped JSON fixture (`ghcr.io/ltbringer/python_debugging_01-fixture`).
- `crawler` — your service, built from this repo. Capped at CPU 0.2 / mem 256Mi to match the platform's grade-time envelope.
- `sidecar` — HTTP reverse proxy the platform also runs at grade time; emits Prometheus metrics on every request it forwards. Your crawler doesn't need to implement `/metrics` — the sidecar provides it.
- `prometheus` — scrapes the sidecar every 5s; UI at <http://localhost:9092>.
- `grafana` — `Crawler — traffic shape` dashboard pre-provisioned at <http://localhost:3000>. Anonymous Admin in dev, no login.

```bash
docker compose up --build
```

`localhost:8080` is the sidecar; it forwards to the crawler internally. Open the dashboard before you start sending traffic, then in another shell POST to the crawler (via the sidecar) with URLs pointing at the fixture's compose-network hostname:

```bash
curl -sX POST localhost:8080/crawl \
  -H 'content-type: application/json' \
  -d '{"urls":[
    "http://fixture:9090/wiki/Python_(programming_language)",
    "http://fixture:9090/wiki/Asyncio",
    "http://fixture:9090/wiki/Global_interpreter_lock"
  ]}' | jq
```

`GET http://localhost:9090/catalog` lists the slugs the fixture knows about. `GET /wiki/<slug>` accepts a few query-string overlays for testing specific behaviors — see the fixture's README.

The bugs in this codebase manifest more visibly under the compose's CPU/memory caps than they do in an unconstrained `uv run` loop. If you want a faster iteration cycle, comment out `mem_limit` and `cpus` in `compose.yaml`. Restore them before deciding your service is "done" — the validator's performance bars are calibrated for the constrained envelope.

### Without Docker

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The service listens on `:8080`. The crawler is generic — it makes HTTP GETs and treats responses as JSON, so URLs can point at anything that returns JSON (the fixture above, the live Wikipedia REST API, your own mock).

The happy path works. The defects only manifest under specific conditions. Debug from outcomes: send workloads, compute what the response should be, compare to what came back.

## Forking and submitting

1. Fork this repo.
2. Fix the service.
3. Commit, push, and tag a new semver (`git tag v1.0.1 && git push --tags`). GitHub Actions builds and pushes `ghcr.io/<you>/python_debugging_01:v1.0.1` (public) to GHCR.
4. From the hardmode CLI:
   ```bash
   hardmode session submit
   ```
5. Watch the score climb through red → amber → green.

The validator's fixture is deterministic. A passing run on your machine will pass on the platform. There is no flakiness budget.

Good luck.
