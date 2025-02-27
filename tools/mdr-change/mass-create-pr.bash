#!/bin/bash

### Variables
version=$1
pr_title=$2
pr_body_file=$3
repos_dir=$4

if [ -z "$version" ] || [ -z "$pr_title" ] || [ -z "$pr_body_file" ] || [ -z "$repos_dir" ]; then
    echo "Usage: $0 <version> '<title>' <pr_body_file> <repos_dir>"
    exit 1
fi

### Creation of changes and PR

deployment_repos=$(gh search repos --owner access-nri \
  --json name \
  --jq '[.[].name] | join(" ")' \
  -- topic:deployment -topic:template
)
branch="infra-update-$version"

echo "MAKE SURE YOU HAVE UPDATED THE BODY FILE + PR TITLE IN SCRIPT"
echo "Going to change the following repos in 10s: $deployment_repos"
sleep 10

for repo in $deployment_repos; do
  cd "$repos_dir/$repo" || exit

  # Check if there are uncommitted changes and exit if so - we don't want to commit something automatically
  uncommitted_changes=$(git ls-files --others --directory --deleted --modified --exclude-standard)
  if [ -n "$uncommitted_changes" ]; then
    echo "Uncommitted changes in $repo: $uncommitted_changes. Exiting..."
    exit 1
  fi

  # Getting repos in a state to create PR
  git checkout main
  git pull
  git checkout -b "$branch"

  # Editing of files - be careful!
  # Basic update of entrypoints to $version
  sed -i -E "s|(access-nri/build-cd/.+)@v.+|\1@$version|g" .github/workflows/c*.yml
  # Other changes here...

  # git operations
  git add .
  git commit -m "infra: Update to $version"
  git push

  # PR creation
  cd - || exit
  gh pr create \
    --repo "access-nri/$repo" \
    --assignee @me \
    --title "$pr_title" \
    --body-file "$pr_body_file" \
    --base main \
    --head "$branch" \
    --label type:infra \
    --draft

  sleep 3
done