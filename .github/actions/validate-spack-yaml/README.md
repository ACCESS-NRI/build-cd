# Validate spack.yaml Action

This action validates a `spack.yaml` file against ACCESS-NRIs restricted `spack.yaml` schema

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `schema-version` | `string` | Version of the schema required in SchemaVer | `true` | N/A | `'1-0-0'`, `"2-0-1"` |
| `schema-repo` | `string` | OWNER/REPO format for the repository containing the schema | `false` | `'access-nri/schema'` | `'my-org/schemas'` |
| `schema-location` | `string` | Directory within the schema-repo that contains the schema | `false` | `'au.org.access-nri/model/spack/environment/deployment'` | `'some/other/path/to/directory'` |
| `spack-yaml-location` | `string` | Path to the `spack.yaml` in the callers repository | `false` | `'spack.yaml'` | `'some/other/spack.yaml'` |

## Outputs

This action creates no outputs, but the failure of the action denotes the failure of validation

## Example

```yaml
# ...
- uses: access-nri/build-cd/.github/actions/validate-spack-yaml@main
  with:
    schema-version: 1-0-0
```
