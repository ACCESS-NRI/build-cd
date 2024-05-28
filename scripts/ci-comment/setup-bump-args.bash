#!/bin/bash
set -x
set -e

### INPUTS ###
# Comments are made to certain PRs, this variable holds the PR Number
PR_NUMBER=$1
# Comment Body
COMMENT_BODY=$2

# Get the version of ${{ inputs.root-sbd }} from the spack.yaml in the PR the comment was written in
gh pr checkout "$PR_NUMBER"
original_version=$(yq e '$SPACK_YAML_MODEL_YQ | split("@git.") | .[1]' spack.yaml)
echo "original-version=${original_version}" >> "$GITHUB_OUTPUT"

# Validate the comment
if [[ "$COMMENT_BODY" =~ major ]]; then
  # Compare the current date (year-month) with the latest git tag (year-month)
  # to determine the next valid tag. We do this because especially feature-rich
  # months might increment the date part beyond the current date.

  d="$(date +%Y-%m)-01"
  d_s=$(date --date "$d" +%s)

  latest_tag=$(git describe --tags --abbrev=0 | tr '.' '-')
  tag_date=${latest_tag%-*}-01
  tag_date_s=$(date --date "$tag_date" +%s)

  echo "Comparing current date ${d} with ${tag_date} (tag looks like ${latest_tag})"

  if (( d_s <= tag_date_s )); then
    echo "version=${tag_date}" >> "$GITHUB_OUTPUT"
    echo "bump=major" >> "$GITHUB_OUTPUT"
  else
    echo "version=${original_version}" >> "$GITHUB_OUTPUT"
    echo "bump=current" >> "$GITHUB_OUTPUT"
  fi
elif [[ "$COMMENT_BODY" =~ minor ]]; then
  echo "version=${original_version}" >> "$GITHUB_OUTPUT"
  echo "bump=minor" >> "$GITHUB_OUTPUT"
else
  echo "::warning::Usage: '!bump [major|minor]', got '$COMMENT_BODY'"
  exit 1
fi