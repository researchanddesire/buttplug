# Developer site

From the repository root, install the pinned site dependencies in a virtual
environment, then build or preview the current documentation:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r developer-docs/requirements.txt
.venv/bin/mkdocs build --strict -f developer-docs/mkdocs.yml
.venv/bin/mkdocs serve -f developer-docs/mkdocs.yml --dev-addr 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/>. The preview reloads when documentation changes.
Generated output goes to the ignored `developer-docs/site/` directory; do not
commit it.

Navigation is defined in `docs/.pages`; current pages and the archive index
are listed explicitly. Update those current pages in place. Archived studies remain available
for targeted lookup and are excluded from normal search. Figures under
`docs/assets/` are copied into the rendered site. `assembly_source.py` renders
`assembly-docs/assembly-guide.md` as the site’s assembly guide and watches its
source during preview; edit that source rather than maintaining a duplicate.

The [published docs](https://researchanddesire.github.io/buttplug/) rebuild when
changes to the developer docs, assembly guide or shared figures land on `main`.
The [Pages workflow](../.github/workflows/publish-pages.yml) checks pull requests
and deploys the strict build from `main`. Its `build-info.json` records the
deployed commit.

When a design change affects the build, update the relevant docs and regenerate
affected figures in the same change. Update the assembly guide at
`assembly-docs/assembly-guide.md` and record open work in `docs/status.md`.

Images and drawings are generated from the CAD by `tools/figures/`; see its
README to regenerate them after a design change.
