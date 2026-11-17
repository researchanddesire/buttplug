"""Freeze the seven exterior mating solids from a reviewed compact first article."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
ROLES = ("RevisedContinuousSkin", "MetalBody", "MotorThermistorCap",
         *(f"Actual_CT{i}_Solid0" for i in range(1, 5)))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def freeze(first_article, fit_report, target):
    info = json.loads(fit_report.read_text())
    source_sha = digest(first_article)
    assert info["assembly_sha256"] == source_sha
    doc = App.newDocument("CompactFirstArticleMatingReference")
    doc.Label = "Compact first article • frozen exterior and contact witnesses"
    with ZipFile(first_article) as archive, TemporaryDirectory() as tmp:
        for name in ROLES:
            member = name + ".Shape.brp"
            path = Path(tmp) / member
            path.write_bytes(archive.read(member))
            shape = Part.read(str(path))
            assert shape.isValid() and len(shape.Solids) == 1, name
            body = doc.addObject("Part::Feature", name)
            body.Shape = shape
    provenance = doc.addObject("App::FeaturePython", "Source")
    for name, value in (("SourceAssemblySHA256", source_sha),
                        ("SourcePCBSHA256", info["pcb_sha256"])):
        provenance.addProperty("App::PropertyString", name, "Frozen first article")
        setattr(provenance, name, value)
        provenance.setEditorMode(name, 1)
    doc.recompute()
    doc.saveAs(str(target))
    source_breps = {}
    with ZipFile(first_article) as archive, ZipFile(target) as reopened:
        for name in ROLES:
            member = name + ".Shape.brp"
            original = archive.read(member)
            assert original == reopened.read(member), name
            source_breps[name] = sha256(original).hexdigest()
    metadata = {
        "file": target.name,
        "sha256": digest(target),
        "source_full_assembly": first_article.name,
        "source_full_assembly_sha256": source_sha,
        "source_full_assembly_pcb_sha256": info["pcb_sha256"],
        "source_fit_report_sha256": digest(fit_report),
        "coordinate_system": "Product exactly as authored in the source document, without placement edits.",
        "scope": "Seven mechanically relevant saved BRep solids from the earlier compact first-article witness. The full trial assembly is external. The active PCB contact interface is checked independently. This does not promote the earlier trial PCB or recheck its interior fit.",
        "solids": list(ROLES),
        "saved_brep_byte_parity": source_breps
    }
    target.with_name("compact-reference.json").write_text(json.dumps(metadata, indent=2) + "\n")
    App.closeDocument(doc.Name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_article", type=Path)
    parser.add_argument("fit_report", type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "CompactFirstArticleMatingReference.FCStd")
    args = parser.parse_args()
    freeze(args.first_article, args.fit_report, args.output)
