# build-cd

This repository houses reusable workflows, actions and scripts for the building and deployment of ACCESS-NRI Climate Models to different environments. It is considered an "umbrella repository" for all Model Deployment Repositories.

## Repositories Serviced By `build-cd`

These are the repositories with the `deployment` topic.

To find the most up to date deployment repositories, use [this search URL](https://github.com/orgs/ACCESS-NRI/repositories?q=topic%3Adeployment+-topic%3Atemplate) or run:

```bash
gh search repos --owner access-nri --json name --jq '[.[].name] | @sh' -- topic:deployment -topic:template
```

### Model Deployment Repositories

* [ACCESS-NRI/ACCESS-OM2](https://github.com/ACCESS-NRI/ACCESS-OM2)
* [ACCESS-NRI/ACCESS-OM2-BGC](https://github.com/ACCESS-NRI/ACCESS-OM2-BGC)
* [ACCESS-NRI/ACCESS-OM3](https://github.com/ACCESS-NRI/ACCESS-OM3)
* [ACCESS-NRI/ACCESS-ESM1.5](https://github.com/ACCESS-NRI/ACCESS-ESM1.5)
* [ACCESS-NRI/ACCESS-ESM1.6](https://github.com/ACCESS-NRI/ACCESS-ESM1.6)
* [ACCESS-NRI/CABLE-standalone](https://github.com/ACCESS-NRI/CABLE-standalone)

### Testing and Template Repositories

* [ACCESS-NRI/ACCESS-TEST](https://github.com/ACCESS-NRI/ACCESS-TEST)
* [ACCESS-NRI/model-deployment-template](https://github.com/ACCESS-NRI/model-deployment-template)

## Overview

This repository is broken down into the following top-level folders:

`config` contains CODEOWNER-locked information on the deployment environments that the models can deploy to. This is used by deployment workflows to gather secrets and configuration details from the associated GitHub Environment.

`scripts` contains independently-testable `python` and `bash` scripts used directly by `build-cd` deployment workflows.

`tools` contains `python` and `bash` scripts used for tasks outside the main deployment workflows.

`tests` contains tests for the above scripts.

`.github/workflows` houses validation and reusable deployment workflows that are called by ACCESS-NRI model deployment repositories, or within `build-cd` itself.

`.github/actions` houses custom actions used by deployment workflows. More information on these actions can be found in `.github/actions/*/README.md`.

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

Similar to `ci.yml`, it parallelizes cleanups based on HPC target.

### `cd.yml` - Release Deployment Entrypoint

This entrypoint is used to deploy Releases as part of merged Pull Requests into `main` or `backport/*.*` branches.

Similar to `ci.yml`, it parallelizes deployments based on HPC target.

## `deploy-*.yml` - Target Deployment Pipeline

This pipeline is responsible for deploying a given model, via [`spack`](https://spack.readthedocs.io/en/latest/), to a single HPC target. This pipeline is deployment-type-independent - it works for both Prereleases and Releases.

### `deploy-1-setup.yml` - Checks and Configuration

This workflow validates environment configuration information from both `build-cd` and the Model Deployment Repository's `config` directory; and also validates the Model Deployment Repository's `spack.yaml`. It then passes this validated information to the [next workflow](#deploy-2-startyml---deployment-and-metadata-retrieval) returning deployment information to [the caller](#deploy-yml---target-deployment-pipeline) via a target-specific file artifact.

### `deploy-2-start.yml` - Deployment and Metadata Retrieval

This workflow deploys the climate model via spack to the given deployment target. It also collects metadata relating to the spack install and returns it to [the previous workflow](#deploy-1-setupyml---checks-and-configuration).

## `undeploy-*.yml` - Target Deployment Removal Pipeline

This pipeline is responsible for removing all spack environments associated with a closed Pull Request for a single HPC target.

### `undeploy-1-start.yml` - Remove Prereleases from Target

This workflow, currently being the single part of the pipeline, removes the spack environments given as a glob pattern, installed in a particular spack instance, on a particular HPC target.

## `settings-*.yml` - `build-cd config` Update Pipeline

This pipeline is responsible for validating and deploying changes based on protected deployment information in `build-cd`s `config` directory. More information on this folder is found in [`config/README.md`](./config/README.md).

### `settings-1-update.yml` - Validate Updated Settings

This workflow is responsible for validating modifications made to `config/settings.json` on Pull Request or push to `build-cd`. Additionally, it will setup matrixing [the deployment workflow](#settings-2-deployyml---deploy-updated-settings) if the workflow trigger is `on.push`.

### `settings-2-deploy.yml` - Deploy Updated Settings

This workflow will update the repositories referenced in `config/settings.json` to the refs in the file for a HPC target.

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
