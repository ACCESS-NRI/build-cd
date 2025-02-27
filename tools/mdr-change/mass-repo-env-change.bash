#!/bin/bash
# Script that updates repo variables for a given environment in all deployment repositories

### Variables

environment_target=$1
environment_type=$2
environment_name="${environment_target} ${environment_type}"

var_type=$3
var_name=$4
value=$5

### Input checking
if [ -z "$environment_target" ] || [ -z "$environment_type" ] || [ -z "$var_type" ] || [ -z "$var_name" ] || [ -z "$value" ]; then
    echo "Usage: $0 <env_target> <env_type> <var_type> <var_name> <value>"
    exit 1
fi

deployment_repos=$(gh search repos --owner access-nri \
  --json name \
  --jq '[.[].name] | join(" ")' \
  -- topic:deployment -topic:template
)

for repo in $deployment_repos; do
  if [[ "$var_type" == "secret" ]]; then
    gh secret set "$var_name" --repo "access-nri/$repo" --env "$environment_name" --body "$value"
  elif [[ "$var_type" == "variable" ]]; then
    gh variable set "$var_name" --repo "access-nri/$repo" --env "$environment_name" --body "$value"
  fi
done