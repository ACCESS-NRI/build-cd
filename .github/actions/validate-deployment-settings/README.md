# Validate Environment Deployment Settings Action

This action validates various `ACCESS-NRI/build-cd` deployment settings.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `settings-path` | `string` | Path to the build-cd settings.json file to validate | `true` | N/A | `'/some/dir/to/settings.json'` |
| `target` | `string` | Which Deployment Target to check settings. Similar to `vars.DEPLOYMENT_TARGET` in a given Environment | `true` | N/A | `'SUPERCOMPUTER'` |
| `error-level` | `string` | Whether failed validation checks should be a GitHub `notice`, `warning` or `error`. `error` will fail the action. | `false` | `'warning'` | `'error'` or `'notice'` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `failures` | Comma-delimited `string` | Comma-delimited string of failures encountered during validation, useful for piping to a PR comment | `"Spack version [0.20] doesn't exist in Release,Spack version [0.21] doesn't exist in Prerelease"` |

## Example

```yaml
# ...
- name: Validate settings
  id: settings
  uses: access-nri/build-cd/.github/actions/validate-deployment-settings@main
  with:
    settings-path: ./some/settings.json
    target: Supercomputer
    error-level: warning

- name: Comment settings warnings
  if: steps.settings.outputs.failures != ''
  uses: access-nri/actions/.github/actions/pr-comment@main
  with:
    comment: |
        The validation failed with the following errors:  ${{ steps.settings.outputs.failures }}
```
