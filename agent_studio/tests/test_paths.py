from ins_claims_agent.paths import (
    default_ontology_path,
    default_playbook_path,
)


def test_repo_assets_exist():
    assert default_ontology_path().is_file()
    assert default_ontology_path().name == "claims.json"
    assert default_playbook_path().is_file()
