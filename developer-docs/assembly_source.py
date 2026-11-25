"""Render the maintained assembly guide and share its images with the developer site."""
from pathlib import Path

from mkdocs.structure.files import File


def _assembly_dir(config):
    return Path(config.config_file_path).resolve().parents[1] / "assembly-docs"


def on_files(files, config):
    source = _assembly_dir(config)
    markdown = (source / "assembly-guide.md").read_text(encoding="utf-8")
    markdown = markdown.replace("../developer-docs/docs/", "")
    files.append(File.generated(config, "assembly-guide.md", content=markdown))
    for image_dir in ("assets/assembly", "assets/pcb"):
        for path in sorted((source / image_dir).glob("*.jpg")):
            files.append(
                File.generated(config, path.relative_to(source).as_posix(), abs_src_path=str(path))
            )
    return files


def on_serve(server, config, builder):
    source = _assembly_dir(config)
    server.watch(str(source / "assembly-guide.md"))
    server.watch(str(source / "assets"))
    return server
