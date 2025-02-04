#!/bin/bash
# Script that updates repo variables in all deployment repositories

### Variables
var_type=$1
var_name=$2
value=$3

### Input checking
if [ -z "$var_type" ] || [ -z "$var_name" ] || [ -z "$value" ]; then
    echo "Usage: $0 <var_type> <var_name> <value>"
    exit 1
fi

deployment_repos=$(gh search repos --owner access-nri \
  --json name \
  --jq '[.[].name] | join(" ")' \
  -- topic:deployment -topic:template
)

for repo in $deployment_repos; do
  if [[ "$var_type" == "secret" ]]; then
    gh secret set "$var_name" --repo "access-nri/$repo" --body "$value"
  elif [[ "$var_type" == "variable" ]]; then
    gh variable set "$var_name" --repo "access-nri/$repo" --body "$value"
  fi
done