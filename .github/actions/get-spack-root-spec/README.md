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
| `root-spec` | `string` | The entirety of the root spec in the spack manifest file | `"access-om2@git.2025.01.01=release ~deterministic"` |
| `root-spec-name` | `string` | The name of the root spec in the spack manifest file | `"access-om2"` |
| `root-spec-ref` | `string` | The git ref from the root spec in the spack manifest file | `"2025.01.01"` |
| `root-spec-version` | `string` | The spack version from the root spec in the spack manifest file | `"release"` |
| `root-spec-yq` | `string` (`yq` filter) | The yq filter for the root spec of the spack manifest file | `(.spack.definitions[] \| select(."ROOT_PACKAGE") \| .[][]) // .spack.specs[0]` |

## Example

```yaml
# ...
jobs:
  manifest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: spec
        uses: access-nri/build-cd/.github/actions/get-spack-root-spec@vX  # for some version `vX`
        with:
          spack-manifest-path: ./spack.yaml

      - run: |
          echo "Deploying ${{ steps.spec.outputs.root-spec-name }} at ${{ steps.spec.outputs.root-spec-version }}"

          # You can tack on more filters on top of the `root-spec` one
          variants=$(yq '${{ steps.spec.outputs.yq-root-spec }} | capture("[^~+- ]+(.+)") | .[0]' ./spack.yaml)
          echo "Variants are $variants"
```
