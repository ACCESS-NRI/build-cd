# Get Deploy Paths Action

This action constructs paths relevant to a deployment of `spack`.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `spack-installs-root-path` | `string` | Path to a directory within which all versions of spack are installed | `true` | N/A | `"/some/dir/apps/spack"` |
| `spack-version` | `string` | Version of spack deployed. Used to construct a specific spack installation path, in conjunction with `spack-installs-root-path`. | `true` | N/A | `"0.21"` |
| `deployment-environment` | `string` | Name of the GitHub deployment target environment | `true` | N/A | `"Gadi Prerelease"` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `root` | `string` | Path to the root of a specific deployment of `spack`. This path contains `spack-{packages,config}` repositories as well. | `"/some/dir/apps/spack/0.21"` |
| `spack` | `string` | Path to a specific installation of `spack`. | `"/some/dir/apps/spack/0.21/spack"` |
| `spack-config` | `string` | Path to the ACCESS-NRI/spack-config repository associated with the install of spack. | `"/some/dir/apps/spack/0.21/spack-config"` |
| `spack-packages` | `string` | Path to the ACCESS-NRI/spack-packages repository associated with the install of spack. | `"/some/dir/apps/spack/0.21/spack-packages"` |

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

      - run: echo 'Spack is installed in `${{ steps.paths.outputs.spack }}` and spack-packages is installed in `${{ steps.paths.outputs.spack-packages }}`'
```
