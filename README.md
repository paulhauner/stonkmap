# Stonkmap

Stonkmap is a self-hosted app for visualising the actual company exposure inside config-defined portfolios.

## Local Run

1. Create a Python environment and install the backend:
   `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
2. Install the frontend:
   `cd frontend && npm install`
3. Edit `config.yaml` and `indexes.yaml` if you want to customise the sample setup.
4. Run the backend:
   `STONKMAP_CONFIG=config.yaml STONKMAP_INDEXES_PATH=indexes.yaml .venv/bin/stonkmap-api`
5. Run the frontend:
   `cd frontend && VITE_API_BASE_URL=http://localhost:18000/api npm run dev`

## Docker Compose

`docker compose up --build`

This serves:

- Backend API at `http://localhost:18000`
- Frontend at `http://localhost:15173`

The compose setup uses the tracked `config.yaml`, `indexes.yaml`, and sample portfolio CSV files by default.

## Tests

- Backend: `.venv/bin/pytest`
- Frontend: `cd frontend && npm test`
