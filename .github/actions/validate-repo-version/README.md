# Validate Repo Versions Action

This action checks that the tags specified in a models `config/versions.json` is an actual, valid tag for that repository.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `repo-to-check` | `string` | ACCESS-NRI repository to validate associated version in `config/versions.json` | `true` | N/A | `spack-packages` |
| `pr` | `number` | The pull request number that contains the `config/versions.json` | `true` | N/A | 12 |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `version` | `string` | Version of the repo from the `config/versions.json` | `"2024.03.12"` |

## Example

```yaml
# ...
- id: validate
  uses: access-nri/build-cd/.github/actions/validate-repo-version@vX
  with:
    repo-to-check: spack-packages
    pr: 12

- run: echo "spack-packages has valid version ${{ steps.validate.outputs.version }} in PR#12's `config/versions.json`"

- if: failure() && steps.validate.outcome == 'failure'
  run: echo "The version in spack-packages is not valid."
```
