# Validate Repo Versions Action

This action checks that the tags specified in a models `config/versions.json` is an actual, valid tag for that repository.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `repos-to-check` | `string` | Space-separated list of ACCESS-NRI repositories to check | `true` | N/A | `spack-packages spack-config` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `spack-packages-version` | `string` | Version of spack-packages from the `config/versions.json` | `"2024.03.12"` |
| `spack-config-version` | `string` | Version of spack-config from the `config/versions.json` | `"2024.12.22"` |

## Example

```yaml
# ...
- id: validate
  uses: access-nri/build-cd/.github/actions/validate-repo-version@main
  with:
    repos-to-check: spack-packages

- run: echo "spack-packages has valid version ${{ steps.validate.outputs.spack-packages-version }} in `config/versions.json`"

- if: failure() && steps.validate.outcome == 'failure'
  run: echo "The version in spack-packages is not valid."
```
