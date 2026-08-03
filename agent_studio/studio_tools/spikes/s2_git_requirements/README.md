# Spike S2 — git install via `requirements.txt`

## Setup in Agent Studio

1. Register this folder as a custom tool (`tool.py` + `requirements.txt` only).
2. Ensure Studio can reach `github.com/jvprosser/ins-owl-rdf-atlas` (public) or adjust the git URL/ref for your fork.
3. Run the tool with user-params `{}` and tool-params `{}` (or `{"probe_symbol":"__version__"}`).

## Pass / fail

- **Pass:** `pass: true`, `module_file` set, import of `ins_claims_agent` works.
- **Fail:** read `spike_s2_git_requirements.json` in `/workspace`; next try a wheel on an allowed index.

## requirements.txt line under test

```text
ins-claims-agent @ git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=agent_studio
```
