# Get Deploy Paths Action

This action constructs paths relevant to a deployment of `spack`.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `spack-installs-root-path` | `string` | Path to a directory within which all versions of spack are installed | `true` | N/A | `"/some/dir/apps/spack"` |
| `spack-version` | `string` | Version of spack deployed. Used to construct a specific spack installation path, in conjunction with `spack-installs-root-path`. | `true` | N/A | `"0.21"` |
| `deployment-environment` | `string` | Name of the GitHub deployment target environment | `true` | N/A | `"Gadi Prerelease"` |
| `spack-environment` | `string` | Spack environment name that is used for this deployment. Used to construct Prerelease spack-packages path, which is demarcated by the environment name | `true` | N/A | `"access-om2-pr12-12"` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `root` | `string` | Path to the root of a specific deployment of `spack`. This path contains `spack-{packages,config}` repositories as well. | `"/some/dir/apps/spack/0.21"` |
| `spack` | `string` | Path to a specific installation of `spack`. | `"/some/dir/apps/spack/0.21/spack"` |
| `spack-config` | `string` | Path to the ACCESS-NRI/spack-config repository associated with the install of spack. | `"/some/dir/apps/spack/0.21/spack-config"` |
| `spack-packages-root` | `string` | Path to the folder containing all ACCESS-NRI/spack-packages repositories used in the install of spack | `"/some/dir/apps/spack/0.21/spack-packages"` |
| `spack-packages` | `string` | Path to the ACCESS-NRI/spack-packages repository associated with the environment created in the install of spack. | For Release: `"/some/dir/apps/spack/0.21/spack-packages"`, for Prerelease: `"/some/dir/apps/spack/0.21/spack-packages/access-om2-pr12-12/spack-packages"` |

## Example

```yaml
# ...
jobs:
  get-paths:
    runs-on: ubuntu-latest
    environment: ${{ inputs.deployment-environment }}
    steps:
      - name: Get Deployment Paths
        id: paths
        uses: access-nri/build-cd/.github/actions/get-deploy-paths@vX
        with:
          spack-installs-root-path: ${{ vars.SPACK_INSTALLS_ROOT_PATH }}
          spack-version: "0.21"
          deployment-environment: ${{ inputs.deployment-environment }}
          spack-environment: ${{ inputs.env-name }}

      - run: echo 'Spack is installed in `${{ steps.paths.outputs.spack }}` and spack-packages is installed in `${{ steps.paths.outputs.spack-packages }}`'
```
