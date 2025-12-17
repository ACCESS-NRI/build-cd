# Get PR Deployments

Action that returns the number of deployments on a given PR branch.

## Inputs

inputs:
  pr:
    required: true
    description: The pull request number to check for deployments of all kinds
  repository:
    required: false
    default: ${{ github.repository }}
    description: The repository to check for deployments
  token:
    required: false
    default: ${{ github.token }}
    description: The GitHub token to use for API requests
outputs:
  deployments:
    description: The total number of deployments for the given PR (from commits and !redeploys)
    value: ${{ steps.total.outputs.number }}

| Name | Description | Required | Default | Example |
| ---- | ----------- | -------- | ------- | ------- |
| `pr` | The pull request number to check for deployments of all kinds | `true` | N/A | `21` |
| `repository` | The repository to check for deployments | `false` | Value of `github.repository` | `"ACCESS-NRI/ACCESS-OM2"` |
| `token` | The GitHub token to use for API requests | `false` | Value of `github.token` | `"ghp_XXXX"` |

## Outputs

| Name | Description | Example |
| ---- | ----------- | ------- |
| `deployments` | The total number of deployments for the given PR (from commits and `!redeploy`s) | `24` |

## Example

```yaml
# ...
jobs:
  deployments:
    runs-on: ubuntu-latest
    steps:
      - id: pr-deploys
        uses: access-nri/build-cd/.github/actions/get-pr-deployments@v6
        with:
          pr: 12

      - run: echo "There have been ${{ steps.pr-deploys.outputs.deployments }} total deployments in this PR, including both regular commit deployments and redeployments"
```
