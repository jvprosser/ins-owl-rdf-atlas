# Adjuster BPMN GUI

One adjuster's canvas: a BPMN file, a list of demo claims, and a chat that sends
`process claim {id}` to an Agent Studio workflow. The reply's `Next step:` line
highlights that box.

## Cloudera AI Application

Same packaging as the Process Mapper. One process serves the built UI and the API.

1. Push this repo into a Cloudera AI project.
2. In a Session:
   ```bash
   bash adjuster_gui/scripts/cml_build.sh
   ```
   That installs Node under `$HOME` (no root), builds `adjuster_gui/frontend/dist`,
   and installs the Python dependencies.
3. Create an Application:
   - **Command:** `python adjuster_gui/backend/main.py`
   - If the project root is `adjuster_gui` itself: `python backend/main.py`
4. The process binds `CDSW_APP_PORT` on `0.0.0.0`. Health check path: `/health`.
   In a Session, Jupyter already owns `CDSW_APP_PORT`, so the GUI binds
   `CDSW_READONLY_PORT` instead (`https://read-only-<engine>.<domain>`).
   An Application engine does not run that editor, so it keeps `CDSW_APP_PORT`.

Open the gear and set the workflow base URL and bearer token. Those stay in the
browser; they are not stored in the project.

## Local

```bash
python3 -m venv adjuster_gui/.venv
adjuster_gui/.venv/bin/pip install -r adjuster_gui/backend/requirements.txt
(cd adjuster_gui/frontend && npm install && npm run build)
cd adjuster_gui/backend && ../.venv/bin/python main.py
# http://localhost:8010
```

`CDSW_APP_PORT` wins when set. Otherwise `ADJUSTER_GUI_PORT`, otherwise `8010`.
