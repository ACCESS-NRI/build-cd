## Build, test, and validation commands

This repository does not have a single top-level build script. Most local work is in the Python utilities under `scripts/`, and dependencies are managed per script area rather than from one root requirements file.

Create a virtualenv and install the requirements for the area you are touching:

```bash
python3 -m venv venv
venv/bin/pip install -r scripts/jinja_template/requirements-dev.txt
venv/bin/pip install -r scripts/spack_manifest/injection/requirements-dev.txt
venv/bin/pip install -r scripts/release_provenance/requirements-dev.txt
venv/bin/pip install -r scripts/model_config_manifest/requirements.txt
```

Run the full Python test suite from the repository root:

```bash
venv/bin/pytest -q
```

Run one test file:

```bash
venv/bin/pytest tests/scripts/jinja_template/test_render_deployment_info.py -q
```

Run one test by node id:

```bash
venv/bin/pytest tests/scripts/jinja_template/test_render_deployment_info.py::test_build_deployment_context__valid_envs -q
```

Local validation used by the settings workflow:

```bash
venv/bin/jsonschema --instance config/settings.json config/settings.schema.json
```

## High-level architecture

This repository is the shared deployment engine for ACCESS-NRI model deployment repositories. The caller repositories provide model-specific `spack.yaml` and `config/*.json` inputs; `build-cd` provides reusable workflows, composite actions, validation, manifest rewriting, and deployment orchestration.

The top-level flow is:

1. `.github/workflows/ci.yml` handles prerelease PR deployments and `!redeploy`. It computes PR metadata, derives the prerelease version (`pr<PR>-<deployment_number>`), resolves the target matrix, and fans out to `deploy-1-setup.yml`.
2. `.github/workflows/cd.yml` handles release deployments. It resolves the deployment targets, verifies target settings, optionally tags the deployment, and then fans out to `deploy-1-setup.yml`.
3. `.github/workflows/deploy-1-setup.yml` is the validation and resolution stage. It validates the caller repository's `config/versions.json`, `config/packages.json`, and manifest schema, combines those inputs with `build-cd`'s own settings, resolves the exact refs/SHAs for `spack`, `spack-config`, and package repositories, and prepares artifacts/outputs for the actual deployment stage.
4. `.github/workflows/deploy-2-start.yml` performs the target-specific deployment over SSH. It rewrites the manifest for module/projection/prerelease needs, copies the manifest to the HPC environment, activates the target Spack installation, installs the environment, refreshes modules, and gathers release provenance metadata.
5. `.github/workflows/settings-1-update.yml` and `settings-2-deploy.yml` are a separate pipeline for changes to `config/settings.json`. They validate the central deployment settings and, on merge to the default branch, update remote HPC `spack` and `spack-config` checkouts to the refs declared in that file.

`.github/actions/*` are small reusable helpers that sit between the workflows and the Python/bash logic: target matrix generation, manifest metadata extraction, deployment path calculation, settings validation, and PR deployment lookup.

## Key conventions

- `config/settings.json` is the central source of truth for target-specific deployment refs. Workflows and actions read from it to decide which `spack` and `spack-config` revisions exist for each HPC target and deployment type.
- Python utilities are run from the repository root as modules, for example `python -m scripts.spack_manifest.injection.modules`. Tests mirror that layout under `tests/scripts/...`.
- There is no single repository-wide Python package or requirements file. Each script area owns its own requirements, and the test suite exercises those modules together from the repo root.
- Spack manifest helpers in `scripts/spack_manifest/getter.py` are written to support both single-target manifests (`spack.specs`) and multi-target manifests that encode `ROOT_PACKAGE` in `spack.definitions`. Reuse those helpers instead of reparsing manifests ad hoc.
- Manifest-rewriting scripts try to preserve Spack-compatible YAML formatting rather than round-tripping with generic defaults. `scripts/spack_manifest/injection/*.py` uses custom YAML representers to keep flow-style reserved definitions and explicit quoting where Spack is sensitive; `scripts/model_config_manifest/prerelease_update.py` uses `ruamel.yaml` with preserved quotes and wide line wrapping to minimize noisy diffs in model config manifests.
- Deployment target fan-out is always constrained by the intersection of caller-supplied targets and the targets defined in `config/settings.json`, via `.github/actions/get-target-matrix`.
