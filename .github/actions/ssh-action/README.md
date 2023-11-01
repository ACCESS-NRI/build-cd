# SSH Action

This action connects to a host using `ssh`, and runs a list of commands. 

## Inputs

| Name | Type | Description | Required | Default | Example |
| ---- | ---- | ----------- | -------- | ------- | ------- |
| host | string | Host name used in ssh call | true | N/A | 'localhost' |
| user | string | User name used in ssh call | true | N/A | 'user' |
| private-key | string | Raw private key used in ssh call | true | N/A | '---- OPENSSH PRIVATE KEY ---- ...' |
| script | string | List of commands to run in the ssh call | true | N/A | 'pwd' |

## Outputs

There are no outputs to this action. 

## Example usage

```yaml
uses: ./.github/actions/ssh-action
with: 
  host: localhost
  user: user
  private-key: ${{ secrets.PRIVATE_KEY }}
  script: |
    cd ~
    pwd
```
