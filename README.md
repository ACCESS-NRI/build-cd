# build-cd

This repository houses reusable workflows for the building and deployment of ACCESS-NRI models to different environments. 

## Overview

This repository is broken down into two folders: `config` and `.github/workflows`. 

`config` contains information on the deployment environments that the models deploy to, which is currently just the name of the deployment target. This is used by the aforementioned deployment workflows to gather secrets and configuration details from the associated GitHub Environment. 

`.github/workflows` houses validation and reusable deployment workflows that are called by ACCESS-NRI model repositories. Currently, only [ACCESS-NRI/ACCESS-OM2](https://github.com/ACCESS-NRI/access-om2) is supported.

Below is a brief summary of the two pipelines, `deploy-*` and `validate-json`.

### deploy-*

This pipeline is responsible for the gathering of configuration information, building and deployment of whatever model repository calls it. It is split into two workflows, as noted below. 

#### deploy-1-setup.yml

This workflow obtains the relevant spack and GitHub Environment information, and creates parallelized  deployments based on the list of environments. 

#### deploy-2-start.yml

Using the GitHub Environment, it `ssh`s into the deployment environments `spack` instance, and installs the model associated with the repository that called it. It then copies back relevant metadata and creates a versioned GitHub Release in the caller repository. 

### validate-json

This workflow is used to validate the `config` folders `*.json` files based on their associated `*.schema.json`. This is used for PR checks on the `build-cd` repo itself. 

## Usage

For supported `spack`-installable ACCESS-NRI models, simply call the `deploy-1-setup.yml` reusable workflow from the given repositories workflow file, like so:

```yml
deploy:
  uses: access-nri/build-cd/.github/workflows/deploy-1-setup.yml@main
  secrets: inherit
  permissions:
    contents: write
```
