# FinTerra Model API Split

This project supports a split deployment:

- Singapore app server: hosts the Vite/Express app and public pages.
- London model server: keeps `data/`, `.tmp/`, strategy model parameters, and runs backtests/training.

The browser keeps calling the same app-local endpoints, such as `/api/backtest` and `/api/model-overview`. When `FINTERRA_MODEL_API_BASE_URL` is set on the app server, Express proxies model/data requests to the London model server. When it is not set, local development keeps using local `data/` and local model files exactly as before.

## Singapore App Server

Set these environment variables:

```bash
FINTERRA_MODEL_API_BASE_URL=https://your-london-model-api.example.com
FINTERRA_MODEL_API_KEY=replace_with_a_long_random_shared_secret
FINTERRA_MODEL_API_TIMEOUT_MS=120000
```

Do not copy `data/`, `.tmp/`, or generated strategy model JSON files to this server.

## London Model Server

Keep the private assets on this server:

- `data/`
- `.tmp/*model*.json`
- `strategy/**/latest_alpha_model.json`
- `strategy/**/strict_alpha_model_*.json`
- `strategy/model_overview_data.json`
- any binary model weights, such as `.pkl`, `.joblib`, `.pt`, `.pth`, `.onnx`, `.h5`, `.bin`, or `.safetensors`

Set this environment variable:

```bash
FINTERRA_MODEL_API_SERVER_KEY=replace_with_the_same_long_random_shared_secret
```

Do not set `FINTERRA_MODEL_API_BASE_URL` on the London server. If it is empty, the same Express endpoints execute locally against the private data and model parameters.

## Proxied Endpoints

The Singapore app proxies these endpoints when `FINTERRA_MODEL_API_BASE_URL` is configured:

- `GET /api/markets`
- `GET /api/latest-model`
- `GET /api/model-overview`
- `GET /api/selector-experiments`
- `GET /api/time-split-progress`
- `POST /api/backtest`
- `POST /api/train-model`
- `POST /api/run-selector-experiment`

This covers `strategy.html` single-stock backtests and `model.html` stock-level effect drilldowns without uploading private data or model parameters to GitHub or the app server.
