"""Load and locate subject data (data/subjects/<subject_id>/concepts.yaml)."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.graph.models import ConceptFile

# apps/api/app/graph/loader.py -> repository root is four parents up from this file's directory.
REPO_ROOT = Path(__file__).resolve().parents[4]
SUBJECTS_DIR = REPO_ROOT / "data" / "subjects"


def subject_dir(subject_id: str) -> Path:
    """`data/subjects/<id>/`, or `data/subjects/_<id>/` for a demo pack (a leading underscore marks
    a dev-only subject: seed scripts refuse to send it to a remote database and the API image
    leaves it out; see docs/ADDING_A_SUBJECT.md)."""
    real = SUBJECTS_DIR / subject_id
    demo = SUBJECTS_DIR / f"_{subject_id}"
    return demo if not real.exists() and demo.exists() else real


def is_demo_subject(subject_id: str) -> bool:
    return subject_dir(subject_id).name.startswith("_")


def concepts_path(subject_id: str) -> Path:
    return subject_dir(subject_id) / "concepts.yaml"


def load_concept_file(path: Path) -> ConceptFile:
    """Parse and schema-validate a concepts.yaml file. Raises on malformed input."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return ConceptFile.model_validate(raw)


def load_subject(subject_id: str) -> ConceptFile:
    return load_concept_file(concepts_path(subject_id))
