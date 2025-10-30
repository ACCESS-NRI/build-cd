# Deployment Configuration Information

This folder contains configuration information relevant to the orchestration of deployments across Model Deployment Repositories.

Modifications to settings in this folder are deployed and validated via the `.github/workflows/settings-*.yml` pipeline.

## `settings.json`

This information is used as a single point of truth for the versions of repositories used for `spack` installs, across all valid HPC targets.

Modifications to this file (when merged) update the versions of the repositories referenced on the HPC.

This means that one should not modify the repositories versions on the HPC targets directly - open a PR in this repository into `main` with the changes required.

## `settings.schema.json`

This schema enforces the structure shown in `settings.json`.

Note:

- For deployments using spack version keys >= `1.0` (for example `"1.0"`, `"1.1"`, `"2.0"`), each versioned entry under `deployment/<TARGET>/<Release|Prerelease>/<VERSION>` must include the field `builtin-spack-packages` in addition to `spack` and `spack-config`.
- For version keys < `1.0` (for example `"0.22"`), only `spack` and `spack-config` are required. This is because historically `spack`s builtin `spack-packages` repository was versioned as part of the `spack` repository version.
