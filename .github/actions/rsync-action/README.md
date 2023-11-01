# Rsync Action

This action transfers files or folders via `rsync`. 

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| host | string | Host name used in ssh call | true | N/A | 'localhost' |
| private-key | string | Raw private key used in ssh call | true | N/A | '---- OPENSSH PRIVATE KEY ---- ...' |
| source | string | Files or folders to send | true | N/A | '~/my/directory' |
| destination | string | File or folder location to receive | true | N/A | 'user@host:~/other/directory' |

## Outputs

There are no outputs to this action. 

## Example usage

```yaml
uses: ./.github/actions/ssh-action
with: 
  host: localhost
  private-key: ${{ secrets.PRIVATE_KEY }}
  source: "~/my/directory"
  destination: "user@localhost:~/other/directory"
```
