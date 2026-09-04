# build-cd

This repository houses reusable workflows, actions and scripts for the building and deployment of ACCESS-NRI Climate Models to different environments. It is considered an "umbrella repository" for all Model Deployment Repositories.

## Repositories Serviced By `build-cd`

These are the repositories with the `deployment` and `spack` topics, called MDRs (Model Deployment Repositories).

To find the most up to date deployment repositories, use [this search URL](https://github.com/orgs/ACCESS-NRI/repositories?q=topic%3Adeployment+topic%3Aspack+-topic%3Atemplate) or run:

```bash
gh search repos --owner access-nri --json name --jq '[.[].name] | @sh' -- topic:deployment topic:spack -topic:template
```

### Template Repositories

These repositories are templates that MDRs are based on:

* [ACCESS-NRI/model-deployment-template](https://github.com/ACCESS-NRI/model-deployment-template)
* [ACCESS-NRI/software-deployment-template](https://github.com/ACCESS-NRI/software-deployment-template)

## Overview

This repository is broken down into the following top-level folders:

`config` contains CODEOWNER-locked information on the deployment environments that the models can deploy to. This is used by deployment workflows to gather secrets and configuration details from the associated GitHub Environment.

`scripts` contains independently-testable `python` and `bash` scripts used directly by `build-cd` deployment workflows.

`tools` contains `python` and `bash` scripts used for tasks outside the main deployment workflows.

`tests` contains tests for the above scripts.

`.github/workflows` houses validation and reusable deployment workflows that are called by ACCESS-NRI model deployment repositories, or within `build-cd` itself.

`.github/actions` houses custom actions used by deployment workflows. More information on these actions can be found in `.github/actions/*/README.md`.

## Provenance

Provenance for model builds contain the following:

* `spack.yaml`, used in the build to create the environment - the abstract list of requirements and constraints on the build created by users.
* `spack.lock`, generated from Spacks concretization process - a concrete list of the full dependency chain and their associated versions, requirements and constraints. This will be able to recreate a build exactly in `spack`, if it is lost.
* `spack.location`, a list of dependencies and their paths on the HPC.
* `build-db-pkgs.json`, a list of important packages and their provenance information, including MD5sums of their executables, as well as URLs to the exact version built.
* `deploy-MODEL-outputs.HPC`, a json-formatted list of metadata related to the build, including the version of `ACCESS-NRI/spack`, `ACCESS-NRI/upstream-spack-packages` and `ACCESS-NRI/access-spack-packages` used, among other things.

For Releases, MDRs have their provenance assured by both GitHub Releases in the MDR itself, and via our [Release Provenance Database](https://reporting.access-nri-store.cloud.edu.au/release-provenance/releases).

For Prereleases, a subset of this information is available in the workflow run (AKA, the deployment of a particular commit). The run of a particular commit is given by the checkmark next to the commit, click on it and then "Details". Otherwise you can find the run by the link next to the rocket in the PR status down the bottom of the PR. The artifacts (named `deploy-MODEL-[outputs|metadata].HPC`) are in the summary of the entire run, down the bottom, and can be downloaded and inspected. Alternatively, if you have the run number, you can do `gh run download RUN_NUMBER`.

> [!NOTE]
> Prerelease Workflow run artifacts are only available for 90 days since the run, and expire afterwards. One can regenerate them by `!redeploy`ing the build (see [this section](#redeploy))

## Versioning in This Repository

The [entrypoint workflows](#entrypoint-workflows) (and other reusable workflows) are versioned both via major version branches (of the form `vX`) and tags (of the form `vX.Y`).

Major versions are used to denote changes to any of the following:

* `build-cd` entrypoint workflow inputs are created, updated or deleted, requiring an update to model deployment repositories workflows.
* Changes to `build-cd` require new `vars`/`secrets` in model deployment repositories.
* Changes to `build-cd` are significant updates to existing features.

Minor versions are new features, or updates that don't create new `vars`/`secrets`, or updates that don't affect entrypoint workflow inputs.

### Using Workflow Versions

Model Deployment Repositories can use `build-cd` workflows via:

* Branch references (`vX`): These can be used to ensure that existing Model Deployment Repository infrastructure will always work within a major version, without updates. Using this reference means you will still get updates to the workflow that don't modify existing infrastructure.
* Tag references (`vX.Y`) (or commit references): These can be used to have a single version of the infrastructure.

## Entrypoint Workflows

These are called directly by Model Deployment Repositories - `ci.yml`, `ci-comment.yml`, `ci-closed.yml` and `cd.yml`.

### `ci.yml` - PR Prerelease Deployment Entrypoint

This entrypoint is used to deploy (and [`!redeploy`](#redeploy)) Prereleases as part of Pull Requests into `main` or `backport/*.*` branches.

It sets up configuring and parallelizing deployments based on HPC target.

### `ci-comment.yml`- PR `!bump` Comment Command Entrypoint

This entrypoint is used to handle the `!bump` Comment Command, which updates, commits and pushes the version of the model automatically.

### `ci-closed.yml` - PR Deployment Cleanup Entrypoint

This entrypoint handles cleanup of existing Prerelease environments from the referenced PR.

It is responsible for removing all spack environments associated with a closed Pull Request for each HPC target. It removes the spack environments matching the closed PR's version pattern and garbage-collects orphaned packages.

### `cd.yml` - Release Deployment Entrypoint

This entrypoint is used to deploy Releases as part of merged Pull Requests into `main` or `backport/*.*` branches.

Similar to `ci.yml`, it parallelizes deployments based on HPC target.

## `deploy.yml` - Target Deployment Pipeline

This pipeline is responsible for deploying a given model, via [`spack`](https://spack.readthedocs.io/en/latest/), to a single HPC target. This pipeline is deployment-type-independent - it works for both Prereleases and Releases.

This workflow validates environment configuration information from both `build-cd` and the Model Deployment Repository's `config` directory; validates the Model Deployment Repository's `spack.yaml`; deploys the model to the target environment; and uploads deployment metadata/outputs artifacts for the entrypoint workflows (`ci.yml` / `cd.yml`).

## `settings.yml` - `build-cd config` Update Pipeline

This pipeline is responsible for validating and deploying spack changes on HPCs based on protected deployment information in `build-cd`s `config` directory. More information on this folder is found in [`config/README.md`](./config/README.md).

## (Legacy) JSON Validation Workflow - `validate-json.yml`

This workflow is used to validate JSON data against JSON schemas that are housed within this repository (as opposed to workflows housed within `ACCESS-NRI/schema`).

## Comment Commands Handled By `build-cd`

Comment Commands are a ChatOps-style interface to repository functions in Model Deployment Repository Pull Requests.

### `!bump`

```txt
!bump [major|minor]
```

This Comment Command bumps a models release version, so one does not have to edit the `spack.yaml` themselves.

It bumps the `spack.yaml` model version (of the form `YEAR.MONTH.MINOR`, where `YEAR.MONTH` is considered the `MAJOR` portion) and commits the result to the PR branch.

### `!redeploy`

```txt
!redeploy
```

This Comment Command deploys the current `HEAD` of the PR branch again.

This is most useful for models that are using `@git.BRANCH` references for versions of model dependencies.

### `!update-configs`

```txt
!update-configs [profile=PROFILE]
```

This Comment Command creates draft PRs to linked model configuration repositories, allowing quick testing of prerelease builds against different model configurations.

This command is informed by the MDRs `config/auto-configs-pr.json` file, in which users can create *profiles* which contain a configs repository, a HPC target, a workflow manager, and a set of configuration branches to open PRs into.
