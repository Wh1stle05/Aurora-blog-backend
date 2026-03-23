from pathlib import Path
import ast


def test_start_script_uses_non_interactive_certbot_flags():
    script = Path("scripts/start.sh").read_text()

    assert "--non-interactive" in script
    assert "--keep-until-expiring" in script


def test_alembic_release_branch_has_single_head():
    versions_dir = Path("alembic/versions")
    revisions = {}
    down_revisions = {}

    for path in versions_dir.glob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        revision = None
        down_revision = None
        for node in tree.body:
            targets = []
            value = None
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
                value = node.value
            else:
                continue

            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "revision" and isinstance(value, ast.Constant):
                    revision = value.value
                if target.id == "down_revision":
                    if isinstance(value, ast.Constant):
                        down_revision = value.value
                    elif isinstance(value, ast.Tuple):
                        down_revision = tuple(
                            elt.value for elt in value.elts if isinstance(elt, ast.Constant)
                        )
        if revision is None:
            continue
        revisions[revision] = path.name
        down_revisions[revision] = down_revision

    child_counts = {revision: 0 for revision in revisions}
    for down_revision in down_revisions.values():
        if isinstance(down_revision, tuple):
            for item in down_revision:
                if item in child_counts:
                    child_counts[item] += 1
        elif down_revision in child_counts:
            child_counts[down_revision] += 1

    heads = [revision for revision, count in child_counts.items() if count == 0]
    assert len(heads) == 1, heads
