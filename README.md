# Splat Streaming Demo

Viewer for streaming compact 36B `.dat` splats (SwinGS viewer vendored in `demo/`).

References: [SwinGSplat/demo](https://github.com/SwinGSplat/demo)

## Local run (simple)

```bash
cd demo
python3 -m http.server 8080
# open http://localhost:8080/
```

- Edit `demo/config_local.json` and set `MODEL_URL` to either:
  - `data/your.dat` (same-origin, no CORS issues), or
  - A remote URL (requires CORS enabled on that host)
- Tuning:
  - `TOTAL_CAP`: 50k–150k for startup speed
  - `SLICE_NUM`: 5–10 for temporal continuity (watch `SLICE_CAP = TOTAL_CAP/SLICE_NUM`)
  - `PREFETCH_SEC`: 0.5–1.5 to reduce stutter
  - `MAX_FRAME`: match your file (e.g., 1800)

## Hosting the `.dat` on Cloudflare R2

- We store the dataset in Cloudflare R2 public bucket (e.g. `https://<pub>.r2.dev/a08_full.dat`).
- Ensure the object is public and CORS allows your app origin(s):
  - Access-Control-Allow-Origin: your site(s) (e.g., `https://your.app`, `http://localhost:8080`)
  - Access-Control-Allow-Methods: GET, HEAD
  - Access-Control-Allow-Headers: *
  - Access-Control-Expose-Headers: Content-Length, Content-Range, Accept-Ranges, ETag
  - Access-Control-Max-Age: 86400
- If CORS is not set, browsers will block cross-origin streaming.

## Deploy on Coolify (Nixpacks)

- Repo contains a `Procfile` and `nixpacks.toml` so Nixpacks knows the start command.
- Start command serves the viewer statically from `demo/`:
  - Procfile: `web: sh -c 'cd demo && python3 -m http.server ${PORT:-8080}'`
- Steps:
  1) Connect the repo in Coolify
  2) App type: Static/Node (Nixpacks will pick Python due to `requirements.txt` but we use the Procfile’s start)
  3) Expose the PORT you configured
  4) Redeploy

## Optional throttled server (dev only)

We include `server/server.js` (Express + compression) to emulate remote bandwidth and avoid local burst artifacts.

```bash
cd server
npm i
THROTTLE_MBPS=25 node server.js
# open http://localhost:8080/demo/
```

Use only if you need to mimic remote streaming locally; otherwise, the simple static server is fine.
