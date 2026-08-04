# Spike S2 — git install via `requirements.txt` — PASS

**Question:** Can Agent Studio install `ins-claims-agent` from `git+https` (subdirectory) listed in the tool’s `requirements.txt`?

**Result (2026-08-04):** PASS in Studio sandbox.

| Field | Value |
|---|---|
| Fingerprint | `INS_CLAIMS_S2_TOOL_PY_V1` |
| Version | `0.1.0` |
| Installed from git | `true` |
| Commit | `8018ae30ed4997b545403add36339e4a33bda49d` (`main`) |
| Subdirectory | `agent_studio` |
| Artifact | `/workspace/spike_s2_git_requirements.json` |

## Working pin

```text
pydantic>=2.0
ins-claims-agent @ git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=agent_studio
```

Prefer a commit SHA instead of `@main` when a demo must be reproducible.

## Re-run (optional)

1. Upload only `tool.py` + `requirements.txt`.
2. user-params `{}`, tool-params `{}` or `{"probe_symbol":"__version__"}`.
3. Confirm `tool_fingerprint: INS_CLAIMS_S2_TOOL_PY_V1` and `pass: true`.
