# Copilot Instructions for `build-cd`

`build-cd` is an "umbrella repository" of reusable GitHub Actions workflows,
composite actions, and Python/Bash scripts that build and deploy ACCESS-NRI
Climate Models to HPC targets (e.g. Gadi, Setonix) via [`spack`](https://spack.readthedocs.io/).
It is consumed by "Model Deployment Repositories" (MDRs) — repos tagged with the
`deployment` topic (e.g. `ACCESS-NRI/ACCESS-OM2`, `ACCESS-NRI/ACCESS-ESM1.5`).

## Repository layout

- `.github/workflows/` — reusable + entrypoint workflows called by MDRs or by
  `build-cd` itself.
- `.github/actions/` — composite actions. Each has its own `action.yml` and
  `README.md`.
- `scripts/` — independently-testable Python/Bash used **directly by deployment
  workflows**. Organised as importable packages (`scripts/<pkg>/...`).
- `tools/` — Python/Bash for tasks **outside** the main deployment workflows
  (mass MDR changes, module setup, service-user setup).
- `tests/` — pytest suite mirroring the `scripts/` tree under `tests/scripts/`.
- `config/` — CODEOWNER-locked deployment settings (`settings.json` validated
  against `settings.schema.json`), deployed via `settings.yml`.

## Testing

- Tests use `pytest` and **must be run from the repository root** — `pytest.ini`
  sets `pythonpath = .` so tests import scripts as packages
  (`from scripts.spack_manifest.getter import ...`).
- Run the whole suite: `pytest`
- Run a single file / test:
  `pytest tests/scripts/spack_manifest/test_getter.py`
  `pytest tests/scripts/spack_manifest/test_getter.py::test_name`
- Each script package pins deps in its own `requirements.txt`, with test-only
  deps in `requirements-dev.txt` (which does `-r requirements.txt`). Install the
  relevant one(s), e.g. `pip install -r scripts/spack_manifest/injection/requirements-dev.txt`.

## Python script conventions

- Scripts are runnable as modules from the repo root
  (`PYTHONPATH=. python -m scripts.<pkg>.<module> --arg ...`), which is exactly
  how workflows invoke them. Each CLI module uses `argparse` in a `main()`
  guarded by `if __name__ == "__main__":`.
- Composite actions call scripts by setting `PYTHONPATH` to the `build-cd` repo
  root (resolved from `github.action_path`) and running `shell: python`, then
  importing `from scripts...`. Keep the package-import contract intact when
  moving/renaming modules.
- Workflows install dependencies per-package
  (`pip install -r scripts/<pkg>/requirements.txt`) right before use rather than
  from a single top-level requirements file.
- YAML manipulation of `spack.yaml` uses `ruamel.yaml` (to preserve formatting/
  comments), not `pyyaml`.

## Workflows

- **Entrypoint workflows** are called directly by MDRs: `ci.yml` (PR prerelease
  deploy), `ci-comment.yml` / `ci-command-configs.yml` (`!bump`,
  `!update-configs` comment commands), `ci-closed.yml` (PR cleanup), `cd.yml`
  (release deploy). `deploy.yml` is the shared per-target deployment pipeline.
- Comment Commands are a ChatOps interface used in MDR PRs: `!bump [major|minor]`,
  `!redeploy`, `!update-configs [profile=PROFILE]`.
- Deployments are matrixed/parallelised per HPC target.

## Deployment config model (post `v9`)

As of `build-cd@v9`, deployment config lives **inside each `spack.yaml`**, not in
`config/*.json` (which are retired). Consumers moved `config/versions.json` +
`config/packages.json` into the manifest as reserved `spack.definitions` and a
`spack.repos` entry:

- `_spack-version` (from `versions.json.spack`) — e.g. `["1.1"]` clones
  `releases/v1.1` of `ACCESS-NRI/spack`.
- `_custom-scopes` (optional, only if present) — from `versions.json.custom-scopes`.
- `_provenance` / `_injection` — from `packages.json`.
- `spack.repos.access_spack_packages` — the `access-spack-packages` version
  (`tag`/`branch`/`commit`), from `versions.json.access-spack-packages`, with
  `destination: $env/package-repos/access-spack-packages`.

Related conventions:

- **Schema version:** MDRs use `spack-manifest-schema-version: 3-0-0`; SDRs
  (`system-tools`, `model-tools`, based on `software-deployment-template`) use
  `2-0-0` and a different schema path. SDRs have **multiple** per-tool
  `TOOL/spack.yaml`; the config/repos block is injected into each one.
- **Entrypoint workflows** no longer take `config-versions-schema-version` /
  `config-packages-schema-version` inputs, and drop `config/**` from path
  triggers (keeping `'**/spack.yaml'`).
- **README badges** read from `spack.yaml` via shields.io `dynamic/yaml`
  (`$.spack.repos.access_spack_packages.tag`,
  `$.spack.definitions[*]._spack-version[0]`); the `spack-config` badge key is
  the `spack` release (e.g. `1.1`), not `0.22`.
- Repeatable fleet-wide procedures live in `tools/mdr-change/`. MDRs are
  enumerated via `gh get-deployment-repos`; templates
  (`model-deployment-template`, `software-deployment-template`) must be updated
  alongside the repos they seed.

## Versioning (important for public-facing changes)

Reusable workflows are versioned via major branches (`vX`) and tags (`vX.Y`) —
MDRs pin to these. Treat a change as a **major** version bump if it adds/updates/
removes entrypoint workflow inputs, requires new `vars`/`secrets` in MDRs, or is
a significant change to existing features. Otherwise it is a **minor** change.
Be careful when editing entrypoint workflow `inputs` — it is a breaking change
for every consumer MDR.

## Protected / CODEOWNER-locked areas

- `config/settings.json` is the single source of truth for repo versions used by
  `spack` installs on HPC. **Never** change HPC versions directly — change them
  here via a PR into `main`; `settings.yml` validates and deploys them.
- `config/settings.json` and `.github/CODEOWNERS` are CODEOWNER-locked (see
  `.github/CODEOWNERS`).

## Conventions

- Commit/PR titles often reference the workflow they touch (e.g.
  `deploy.yml: ...`, `c[id].yml: ...`).
- Do **not** commit or push unless explicitly asked.
