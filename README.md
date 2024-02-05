# build-cd

This repository houses reusable workflows for the building and deployment of ACCESS-NRI models to different environments.

## Overview

This repository is broken down into two folders: `config` and `.github/workflows`.

`config` contains information on the deployment environments that the models deploy to, which is currently just the name of the deployment target. This is used by the aforementioned deployment workflows to gather secrets and configuration details from the associated GitHub Environment.

`.github/workflows` houses validation and reusable deployment workflows that are called by ACCESS-NRI model repositories. Currently, only [ACCESS-NRI/ACCESS-OM2](https://github.com/ACCESS-NRI/access-om2) is supported.

Below is a brief summary of the three pipelines, `deploy-*`, `undeploy-*` and `validate-json`.

### `deploy-*`

#### Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `type` | string | The type of deployment - either 'release' or 'prerelease' | true | `release` | `prerelease` |
| `version` | string | The version of the model being deployed | true | N/A | `2024.01.1` |

#### Explanation

This pipeline is responsible for the gathering of configuration information, building and deployment of whatever model repository calls it. It is split into two workflows.

##### `deploy-1-setup.yml`

This workflow obtains the relevant spack and GitHub Environment information, and creates parallelized deployments based on the list of environments.

##### `deploy-2-start.yml`

Using the GitHub Environment, it `ssh`s into the deployment environments `spack` instance, and installs the model associated with the repository that called it. It then copies back relevant metadata and creates a versioned GitHub Release in the caller repository, if it is not a `prerelease` deployment.

#### Usage

For supported `spack`-installable ACCESS-NRI models, simply call the `deploy-1-setup.yml` reusable workflow from the given repositories workflow file, as shown below. Don't forget to add required inputs!

```yml
deploy:
  uses: access-nri/build-cd/.github/workflows/deploy-1-setup.yml@main
  with:
    version: 1.2.3
  secrets: inherit
  permissions:
    contents: write
```

### `undeploy-*`

For given `spack` environments, we can also remove deployments. For example:

```yml
remove-prereleases:
  uses: access-nri/build-cd/.github/workflows/undeploy-2-setup.yml@main
  with:
    version-pattern: ${{ inputs.model }}-*
  secrets: inherit
```

This will remove every `spack` environment from the deployment target that matches `<model>-*`.


#### Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `version-pattern` | string | A wildcard-supported string for version(s) of the model being removed | true | N/A | `2024.01.1-pre*` |

#### Explanation

This pipeline is responsible for removing deployed models from a deployment environment. Particular use-cases include removing `prerelease` builds from a deployment environment once a PR is merged.

##### `undeploy-1-setup.yml`

This workflow obtains the relevant spack and GitHub Environment information, and creates parallelized jobs removing the given `spack` environments based on the list of deployment environments.

##### `undeploy-2-start.yml`

Using the GitHub Environment, it `ssh`s into the deployment environments `spack` instance, and installs the model associated with the repository that called it. It then copies back relevant metadata and creates a versioned GitHub Release in the caller repository, if it is not a `prerelease` deployment.

#### Usage

For given `spack` environments, we can also remove deployments. For example:

```yml
remove-prereleases:
  uses: access-nri/build-cd/.github/workflows/undeploy-2-setup.yml@main
  with:
    version-pattern: ${{ inputs.model }}-pre*
  secrets: inherit
```

This will remove every `spack` environment from the deployment target that matches `<model>-pre*`.

### `validate-json.yml`

This workflow is used to validate the `config` folders `*.json` files based on their associated `*.schema.json`. This is used for PR checks on the `build-cd` repo itself.

### `create-deployment-spack.yml`

This workflow_dispatch-triggered workflow is used to create a version of `spack` on `Gadi`.

#### Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `spack-version` | string | A version of `spack` | true | N/A | `0.20` |
| `spack-packages-version` | string | A version of ACCESS-NRI/spack-packages to be bundled with the install of `spack` | true | `main` | `2023.11.12` |
| `spack-config-version` | string | A version of ACCESS-NRI/spack-config to be bundled with the install of `spack` | true | `main` | `2024.01.01` |
| `deployment-location` | true | A path in the deployment environment where Spack should be created. For example, if it is `opt/spack`, spack will be installed under `opt/spack/<spack-version>/` | true | N/A | `/opt/spack` |
