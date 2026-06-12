# Get Remote Git Ref Info

Action that returns information about a git ref without checking out the target repository.

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| `repository` | `string` | Repository to query, in the form `owner/repo` | `true` | N/A | `"ACCESS-NRI/spack"` |
| `ref` | `string` | Branch, tag, or commit SHA to resolve | `true` | N/A | `"releases/v0.22"` |
| `token` | `string` | GitHub token used for API access | `false` | `github.token` | `"${{ github.token }}"` |

## Outputs

| Name | Type | Description | Example |
| ---- | ---- | ----------- | ------- |
| `ref-type` | `string` | The detected ref type | `"branch"` |
| `sha` | `string` | The commit SHA the ref resolves to | `"0123456789abcdef0123456789abcdef01234567"` |

## Example

```yaml
- name: Resolve ref
  id: ref
  uses: access-nri/build-cd/.github/actions/get-remote-git-ref-info@vX
  with:
    repository: ACCESS-NRI/spack
    ref: releases/v0.22

- run: |
    echo "${{ steps.ref.outputs.ref-type }} -> ${{ steps.ref.outputs.sha }}"
```
