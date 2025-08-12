# Splat Streaming Demo (Local + Throttled Server)

This project wraps the SwinGS viewer with a throttled Node server so local `.dat` playback behaves like remote streaming.

References: [SwinGSplat/demo](https://github.com/SwinGSplat/demo)

## Run locally

```bash
# Python venv for converter tools (optional)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start throttled Node server (default ~25 Mbps)
cd server
npm i
THROTTLE_MBPS=25 node server.js
# open http://localhost:8080/demo/
```

- Place your `.dat` under `demo/data/` and ensure `demo/config_local.json` points to it (MODEL_URL).
- To start playing sooner, reduce `TOTAL_CAP` in `demo/config_local.json` (e.g., 50k–100k).

## Deploy (Coolify/GitHub)
- Deploy as a Node app; start command: `node server/server.js`
- Optional env: `THROTTLE_MBPS` to control bandwidth
- Do not commit big `.dat` files; host them separately or mount a volume.
