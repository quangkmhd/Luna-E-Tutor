"""Load a unit manifest and its ordered content."""

from pathlib import Path

import yaml

from luna_tutor.curriculum.models import ContentFragment, UnitCurriculum, UnitManifest


def _read_yaml(path: Path):
    with path.open(encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def load_unit(path: Path) -> UnitCurriculum:
    """Load a unit directory or unit.yaml; validate all cross-file references."""
    manifest_path = path / 'unit.yaml' if path.is_dir() else path
    manifest = UnitManifest.model_validate(_read_yaml(manifest_path))
    root = manifest_path.parent
    fragments = [manifest.opening]
    for name in manifest.content_files:
        content_path = (root / name).resolve()
        if not content_path.is_relative_to(root.resolve()):
            raise ValueError('Content file must be inside the unit directory')
        fragments.append(ContentFragment.model_validate(_read_yaml(content_path)))
    fragments.append(manifest.closing)
    return UnitCurriculum(
        **manifest.model_dump(exclude={'content_files', 'opening', 'closing'}),
        stages=[fragment.stage for fragment in fragments],
        vocabulary=[item for fragment in fragments for item in fragment.vocabulary],
        patterns=[item for fragment in fragments for item in fragment.patterns],
        objectives=[item for fragment in fragments for item in fragment.objectives],
        activities=[item for fragment in fragments for item in fragment.activities],
    )
