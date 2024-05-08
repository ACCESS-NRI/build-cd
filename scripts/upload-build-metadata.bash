#!/bin/bash
set -x
set -e

# URL for the associated GitHub Release of $model_name.
release_url=$1
# Timestamp for the creation of the $release_url.
release_time=$2
# Path to the dir containing the spack.{lock,location.json}.
json_dir=$3
# Name of the model (or root-sbd) (eg. access-om2)
model_name=$4

# the rest of the model components for the given $model_name
# (eg. for access-om2 there would be mom5, cice5, etc...)
shift 4
packages=( "$@" )

spack=$(jq '.spack | {version: .version, commit: .commit}' "$json_dir/spack.lock")

model=$(jq \
  --arg model "$model_name" \
  --argjson spack "$spack" \
  '.concrete_specs | to_entries[] | select(.value.name == $model)
  | {
      spackhash: .key,
      spec: (.value.name + "@" + .value.version),
      spackversion: $spack
  }' "$json_dir/spack.lock"
)

for pkg in "${packages[@]}"; do
  install_path=$(jq -r \
    --arg pkg "$pkg" \
    'to_entries[] | select(.key | test($pkg)) | .value' \
    "$json_dir/spack.location.json"
  )

  jq \
    --arg pkg "$pkg" \
    --arg release_url "$release_url" \
    --arg release_time "$release_time" \
    --arg install_path "$install_path" \
    --argjson model "$model" \
    '.concrete_specs | to_entries[] | select(.value.name == $pkg)
    | {
      spackhash: .key,
      spec: (.value.name + "@" + .value.version),
      modelbuildhash: $model,
      installpath: $install_path,
      created_at: $release_time,
      release_url: $release_url
    }' "$json_dir/spack.lock" > package.json

  python ./tools/release_provenance/save_release.py package.json
  echo "Uploaded $pkg to build DB"
done
