#!/bin/bash
# Script that creates an environment for a given repository

### Variables

repo=$1

environment_target=$2
environment_type=$3
environment_name="${environment_target} ${environment_type}"


secrets_env_file=$4
vars_env_file=$5

ssh_key_file=$6

### Input checking
if [ -z "$repo" ] || [ -z "$environment_target" ] || [ -z "$environment_type" ] || [ -z "$secrets_env_file" ] || [ -z "$vars_env_file" ] || [ -z "$ssh_key_file" ]; then
    echo "Usage: $0 <repo> <target> <type> <secrets_file> <vars_file> <ssh_key_file>"
    exit 1
fi

if [ ! -f "$secrets_env_file" ]; then
    echo "Secrets Environment file not found: $secrets_env_file"
    exit 1
fi
if [ ! -f "$vars_env_file" ]; then
    echo "Variable Environment file not found: $vars_env_file"
    exit 1
fi
if [ ! -f "$ssh_key_file" ]; then
    echo "SSH Key file not found: $ssh_key_file"
    exit 1
fi


### Environment
# Create environment
# Reviewers are CodeGat and aidanheerdegen
if [[ "$environment_type" == "Release" ]]; then
  # Set branch protections
  gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$repo/environments/$environment_name" \
    -F "prevent_self_review=false" \
    -F "reviewers[][type]=User" \
    -F "reviewers[][id]=45781416" \
    -F "reviewers[][type]=User" \
    -F "reviewers[][id]=6063709" \
    -F "deployment_branch_policy[protected_branches]=false" \
    -F "deployment_branch_policy[custom_branch_policies]=true"

  # Set custom branch policies
  gh api \
    --method POST \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$repo/environments/$environment_name/deployment-branch-policies" \
    -f "name=main" -f "type=branch"

  gh api \
    --method POST \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$repo/environments/$environment_name/deployment-branch-policies" \
    -f "name=backport/*.*" -f "type=branch"

else
  gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$repo/environments/$environment_name"
fi

# Set secrets/vars via env files
gh secret set --repo "$repo" --env "$environment_name" -f "$secrets_env_file"
gh variable set --repo "$repo" --env "$environment_name" -f "$vars_env_file"