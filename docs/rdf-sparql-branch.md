# RDF / SPARQL restore

JSON+YAML is the runtime on `json-yaml-runtime` (and intended `main`). Turtle TBox + SPARQL probes are preserved on:

- Branch: `rdf-sparql-runtime`
- Tag: `rdf-sparql-runtime` (same name)

To run the old session-graph stack for a customer that wants RDF+SPARQL:

```bash
git checkout rdf-sparql-runtime
```

That tree keeps `ontology/*.ttl`, `probes/*.rq`, `rdflib` build/validate/route, and session `claim_{id}_graph.ttl`. Do not mix Workflow Data: upload either JSON schema + playbook YAML, or Turtle + `.rq` files, not both as the live router.

MCP, Crew Delegate, and playbook **actions** (`next_step`, `agent_role`) are the same idea on both lines. Only the case document and probe language differ.
