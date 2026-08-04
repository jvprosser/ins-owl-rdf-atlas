# Agent Studio spikes (ADR 0001)

| Spike | Folder | Question | Result |
|---|---|---|---|
| S1 | `s1_mcp_from_tool/` | Can `tool.py` call registered MCP? | **FAIL** — no in-process bridge; use Path A |
| S2 | `s2_git_requirements/` | Does `requirements.txt` accept git+https? | **PASS** — pin `ins-claims-agent` from git |

Upload **only** each spike’s `tool.py` + `requirements.txt` to Studio. Artifacts land in `SESSION_DIRECTORY` (`/workspace`).
