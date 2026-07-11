# python_debugging_01

A Python web crawler service with several planted bugs. Your job is to make it
correctly handle the workload the validator throws at it, within the resource
envelope the platform provisions — and to watch your fixes land on a red → amber
→ green score.

This is the first course on the [hardmode](https://github.com/h4rdm0d3) platform.
The service ships as an HTTP server; a private validator hits it, scores it
across a few blackbox dimensions, and shows you the result.

---

## How the course works

You don't open a pull request against this repo. The loop is:

1. **Enroll** — `hardmode courses enroll python-debugging-01` forks this repo into
   your account. That fork is your workspace: your edits, your image, your trail.
2. **Iterate locally** — run the service with `uv` (or the compose stack) and fix
   the bugs against the same fixture the grader uses.
3. **Deploy into your vcluster** — install this repo's Helm chart into a real
   Kubernetes vcluster you have admin on, running *your* image.
4. **Submit** — `hardmode session submit <session-id>` grades your running
   deployment and records the best score on your enrollment.

There is no flakiness budget: the fixture is deterministic, so a passing run on
your machine passes on the platform.

---

## Prerequisites

- **kubectl** — talk to your vcluster
- **kubectx** — switch between the session and vcluster contexts without pain
- **helm** — install the vcluster and this course's chart
- **uv** — run/iterate the Python service locally
- a container builder (**docker** or **podman**) + a registry you can push to
  (e.g. your GHCR) — to get your fixed image into the vcluster

---

## Running on the hardmode platform

### 1. Start your session

`hardmode session start python-debugging-01` provisions a Kubernetes **vcluster**
for you and writes a kubeconfig that points straight at it — no manual vcluster
install, no port-forwarding. Grab the kubeconfig path and session id from its
JSON:

```sh
start="$(hardmode session start python-debugging-01 --output-json)"
# printf, not echo — the kubeconfig string contains \n escapes that some
# shells' echo would expand and break the JSON.
export KUBECONFIG="$(printf '%s' "$start" | jq -r .kubeconfig)"
session_id="$(printf '%s' "$start" | jq -r .session.id)"

kubectl get nodes              # cluster-admin on your own vcluster
```

The vcluster is yours for the life of the session; the platform tears it down
when the session ends.

### 2. Deploy the course — and your fix

The chart in `charts/python_debugging_01/` is the deployment: your **crawler**,
the **wikipedia** fixture it depends on, and a **sidecar** that fronts the
crawler and exports the metrics your dashboard reads.

First deploy as-is (the unfixed reference image — it'll score red):

```sh
helm install pd01 ./charts/python_debugging_01
kubectl get pods               # crawler, wikipedia, sidecar
```

Then the iterate loop — build your fixed image, push it, point the chart at it:

```sh
docker build -t ghcr.io/<you>/python_debugging_01:dev .
docker push   ghcr.io/<you>/python_debugging_01:dev

helm upgrade pd01 ./charts/python_debugging_01 \
  --set images.problems.crawler.repository=ghcr.io/<you>/python_debugging_01 \
  --set images.problems.crawler.tag=dev
```

Only `images.problems.crawler` is yours to change — `wikipedia` and `sidecar`
are author-provided and locked. The crawler runs inside the **200m CPU /
256Mi** envelope the grader enforces; tuning your deployment's footprint is part
of the score (see *Resource envelope*).

### 3. Submit for grading

When you want a recorded run:

```sh
hardmode session submit "$session_id"
```

The platform points its validator at your running deployment, scores it, and
records the best result on your enrollment. Re-submitting never lowers your
score.

### 4. Watch your dashboard

`hardmode session status "$session_id"` gives you a Grafana URL scoped to your session
(request rate, latency p50/p95/p99, error rates, request-vs-response gaps). The
dashboards show *symptoms*, never bug names — form your hypotheses from the
curves. The same metrics surface locally via the compose stack (below).

---

## The contract

### `POST /crawl`

Request:
```json
{ "urls": ["http://wikipedia:9090/wiki/Asyncio"], "mode": "batch" }
```

`mode` is optional — `"batch"` (default) returns once every fetch resolves;
`"stream"` returns as soon as the work is dispatched. Both modes must produce
the same eventual result set for the same input.

Response:
```json
{
  "results": [{ "url": "...", "title": "Asyncio", "error": null }],
  "stats": { "instance_seen": ["..."] }
}
```

`stats.instance_seen` reports the URLs handled by the instance that served the
request.

### `GET /healthz`

Returns `{"ok": true}` — used by the grader to know the service is up.

---

## How you're graded

The validator sends one workload inside the constrained envelope and scores it
across independent, binary dimensions:

- **Completeness** — every input URL appears in the response, `error` populated
  when applicable.
- **Dedup** — equivalent URLs collapse to one result; concurrent duplicates
  produce no extras.
- **Isolation** — per-request state doesn't bleed across requests.
- **Performance** — the workload finishes inside the wall-clock bar.
- **Stability** — back-to-back runs don't degrade.

Score = passing dimensions × 20, in `[0, 100]`. Label: **red** (`< 25`),
**amber** (`25 ≤ score < 100`), **green** (`100`). You see `{score, label}`
only — no per-dimension breakdown. The validator deliberately won't tell you
*what* is failing; that's what the dashboards and your own testing are for.

---

## Resource envelope

The platform runs your crawler with **CPU 200m**, **memory 256Mi**, and egress
restricted to the platform's fixture (no internet at grade time). The dimension
bars are calibrated for this envelope: within it, an approximately-correct
service can't meet the performance and stability bars — fixing the bugs is the
only way through.

---

## Local development

Fastest loop — run the service directly:

```sh
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The crawler makes HTTP GETs and treats responses as JSON, so URLs can point at
anything that returns JSON (the fixture, the live Wikipedia REST API, your own
mock).

Full loop with the same observability stack you get on the platform — fixture +
crawler + sidecar + Prometheus + Grafana:

```sh
docker compose up --build
# sidecar (crawler entry) on :8080, Grafana on :3000, Prometheus on :9092
curl -sX POST localhost:8080/crawl -H 'content-type: application/json' \
  -d '{"urls":["http://fixture:9090/wiki/Asyncio"]}' | jq
```

The bugs manifest more visibly under the compose's CPU/memory caps than in an
unconstrained `uv run` loop. Comment out `mem_limit`/`cpus` in `compose.yaml`
for a faster cycle, then restore them before judging your own work — the
validator's bars are calibrated for the constrained envelope.

The happy path works; the defects only manifest under specific conditions.
Debug from outcomes: send workloads, compute what the response should be,
compare to what came back. Good luck.
