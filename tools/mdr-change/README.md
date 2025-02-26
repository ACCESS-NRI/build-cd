# Model Deployment Repository Change Scripts

This folder contains scripts for mass changes to Model Deployment Repositories (MDRs) - focussed especially around the PR creation process or environment variable updates.

## Scripts

Don't forget to check the inputs, as well as if any of the script needs to be modified before running. This extends to templates used or `.env` files it expects.

> [!NOTE]
> All of these scripts require `admin` permissions, except for `mass-create-pr.bash`, which requires `write`.

### Create New MDR-Style GitHub Environment in a Repository - `create-env.bash`

Creating environments via the web interface is annoying. Especially when you're essentially creating the same thing every time, as is common in MDRs.

This script creates a MDR-style GitHub Environment informed by local, **NOT** version controlled `.env` files. It sets @aidanheerdegen and @CodeGat as Environment Approvers.

> [!NOTE]
> For info on what variables should be in the `.env` files, see [ACCESS-NRI/model-deployment-template](https://github.com/ACCESS-NRI/model-deployment-template).

#### Inputs

```bash
# Usage: ./create-env.bash <repo> <target> <type> <secrets_file> <vars_file> <ssh_key_file>`
# Example:
./create-env.bash access-nri/access-test Gadi Release ../.secrets.env ../.vars.env ~/.ssh/key
```

Where:

- `repo` is a repository in `OWNER/REPO` format.
- `target` is the name of the HPC system, no spaces allowed.
- `type` is the type of environment. Currently one of `Release`/`Prerelease`.
- `secrets_file` is a path to a local `dotenv`-style file that contains all the secret names and values for import, minus the `secrets.SSH_KEY` secret.
- `vars_file` is a path to a local `dotenv`-style file that contains all the variable names and values for import.
- `ssh_key_file` is a file that contains an SSH private key that is used in the `secrets.SSH_KEY` variable.

#### Outputs

A GitHub environment ready to use for deployments, at a given repository.

### Mass-Create Infrastructure-Updating PRs in ALL MDRs - `mass-create-pr.bash`

Pull requests are annoying to create sometimes. But they're even more annoying when you have to do the same PR for every model deployment repository. This script automates PR creation to all model deployment repositories for a given version of `build-cd` infrastructure.

> [!IMPORTANT]
> This is a mass operation. Make sure you've got the inputs and prerequisites right before running this script!

#### Prerequisites

- You have updated the `--title` arg in the script.
- Optionally, you have added other changes to files needed in the script.
- You have updated/created a new PR body based on `templates/general.pull-request.md`.

#### Inputs

```bash
# Usage: ./mass-create-prs.bash <version> '<pr_title>' <pr_body_file> <repos_dir>`
# Example:
./mass-create-prs.bash v5 'Infrastructure Update: v5: New Feature' ./templates/general.pull-request.md ../../..
```

Where:

- `version` is the version of the `build-cd` infrastructure will be used in entrypoint workflows to `build-cd` in MDRs.
- `pr_title` is a string that will be the title for all created PRs.
- `pr_body_file` is a path to a file containing a PR description suitable for use for all MDRs, based on `templates/general.pull-request.md`.
- `repos_dir` is a local directory that is the parent of all model deployment repositories referenced in the script. This is so we can make the changes needed for a PR to be opened.

#### Outputs

Draft pull requests in all MDRs.

### Mass-Create/Update GitHub Environment Variables/Secrets in ALL MDRs - `mass-repo-env-change.bash`

Sometimes `vars/secrets` needs to be updated in a given environment across all MDRs. This can be a bit annoying to do, so there is a script to do it.

Note that this cannot handle multiline values (such as SSH keys).

> [!NOTE]
> For info on what variables should be set, see [ACCESS-NRI/model-deployment-template](https://github.com/ACCESS-NRI/model-deployment-template).

Also,

> [!IMPORTANT]
> This is a mass operation. Make sure you've got the inputs and prerequisites right before running this script!

#### Inputs

```bash
# Usage: ./mass-repo-env-change.bash <env_target> <env_type> <var_type> <var_name> <value>`
# Example:
./mass-repo-env-change.bash Gadi Release variable DEPLOYMENT_TARGET gadi
```

Where:

- `env_target` is the name of the HPC system, no spaces allowed.
- `env_type` is the type of environment. Currently one of `Release`/`Prerelease`.
- `var_type` is the type of data being stored. Either `secret` or `variable`.
- `var_name` is the name of the data stored.
- `value` is the value of the data stored.

#### Outputs

An updated variable/secret in the given environment across all MDRs.

### Mass-Create/Update Repo Variables/Secrets in ALL MDRs - `mass-repo-change.bash`

Sometimes repo-level `vars/secrets` (rather than environment-level, see [this section](#mass-createupdate-github-environment-variablessecrets-in-all-mdrs---mass-repo-env-changebash)) needs to be updated across all MDRs. This can be a bit annoying to do too, so there is a script to do it.

Note that this cannot handle multiline values (such as SSH keys).

> [!NOTE]
> For info on what variables should be set, see [ACCESS-NRI/model-deployment-template](https://github.com/ACCESS-NRI/model-deployment-template).

Also,

> [!IMPORTANT]
> This is a mass operation. Make sure you've got the inputs and prerequisites right before running this script!

#### Inputs

```bash
# Usage: ./mass-repo-env-change.bash <var_type> <var_name> <value>`
# Example:
./mass-repo-env-change.bash variable SPACK_YAML_SCHEMA_VERSION 1-0-4
```

Where:

- `var_type` is the type of data being stored. Either `secret` or `variable`.
- `var_name` is the name of the data stored.
- `value` is the value of the data stored.

#### Outputs

An updated repo-level variable/secret across all MDRs.
