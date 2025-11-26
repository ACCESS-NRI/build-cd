# Get Spack Manifest Information

Action that returns information about a Spack manifest file.

## Inputs

> [!NOTE]
> Action assumes that an appropriate repository is checked out prior to invocation

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `spack-manifest-path` | `string` | The path to the spack manifest file | `false` | `"./spack.yaml"` | `"./some/other.spack.yaml"` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `deployment-name` | `string` | The name of the deployment as specified in the reserved definition `_name` | `access-om2` |
| `deployment-version` | `string` | The version of the deployment as specified in the reserved definition `_version` | `2025.11.000` |

## Example

```yaml
# ...
jobs:
  manifest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: spec
        uses: access-nri/build-cd/.github/actions/get-spack-manifest@vX  # for some version `vX`
        with:
          spack-manifest-path: ./spack.yaml

      - run: |
          echo "Deploying ${{ steps.spec.outputs.deployment-name }} at ${{ steps.spec.outputs.deployment-version }}"
```
