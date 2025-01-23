# Get Deployment Target Matrix Action

Action that returns a matrix of deployment targets based on the caller's input and the valid targets in the build-cd repository.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `targets` | `string` (space-separated) | A space-separated list of deployment targets for the model deployment repository. | `true` | N/A | `"Gadi Setonix"` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `valid-targets` | `string` | A JSON array of valid deployment targets, suitable for use as a matrix. | `"["Gadi", "Setonix"]"` |

## Example

```yaml
# ...
jobs:
  generate-matrix:
    runs-on: ubuntu-latest
    outputs:
      valid-targets: ${{ steps.generate.outputs.valid-targets }}
    steps:
      - id: generate
        uses: access-nri/build-cd/.github/actions/get-target-matrix@main
        with:
          targets: ${{ vars.MODEL_REPO_TARGETS }}

  matrix:
    runs-on: ubuntu-latest
    needs: [generate-matrix]
    strategy:
      matrix:
        target: ${{ fromJson(needs.generate-matrix.outputs.valid-targets) }}
    steps:
      - run: echo "Wow, this is running in ${{ matrix.target }}!"
```
