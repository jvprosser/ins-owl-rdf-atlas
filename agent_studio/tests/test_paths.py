from ins_claims_agent.paths import (
    default_ontology_path,
    default_playbook_path,
    default_probes_dir,
)


def test_repo_assets_exist():
    assert default_ontology_path().is_file()
    assert default_playbook_path().is_file()
    assert default_probes_dir().is_dir()
    assert (default_probes_dir() / "R4_1_subrogation_gap.rq").is_file()
