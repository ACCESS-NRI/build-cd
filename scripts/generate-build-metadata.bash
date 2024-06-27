#!/bin/bash
set -x
set -e

### INPUTS ###
# URL for the associated GitHub Release of $model_name.
release_url=$1
# Timestamp for the creation of the $release_url.
release_time=$2
# Path to the dir containing the spack.{lock,location.json}.
json_dir=$3
# directory that contains the <package>.json files
output_dir=$4
# Name of the model (or root-sbd) (eg. access-om2)
model_name=$5

# the rest of the model components for the given $model_name
# (eg. for access-om2 there would be mom5, cice5, etc...)
shift 5
packages=( "$@" )

### SCRIPT ###
mkdir -p "$output_dir"

spack=$(jq \
  '{
    version: .spack.version,
    commit: .spack.commit
  }' "$json_dir/spack.lock")

model=$(jq \
  --arg model "$model_name" \
  --arg release_url "$release_url" \
  --arg release_time "$release_time" \
  --argjson spack "$spack" \
  '.concrete_specs | to_entries[] | select(.value.name == $model)
  | {
      spack_hash: .key,
      spec: (.value.name + "@" + .value.version),
      created_at: $release_time,
      release_url: $release_url,
      spack_version: $spack
  }' "$json_dir/spack.lock"
)

# construction of the initial build_metadata.json
jq --null-input \
  --argjson model "$model" \
  '{
    model_build: $model,
    component_build: [],
  }' > "$output_dir/build_metadata.json"

for pkg in "${packages[@]}"; do
  pkg_hash=$(jq --raw-output \
    --arg pkg "$pkg" \
    '.concrete_specs | to_entries[] | select(.value.name == $pkg) | .key' \
    "$json_dir/spack.lock"
  )

  echo "Hash of $pkg is $pkg_hash"

  install_path=$(jq --raw-output \
    --arg pkg_hash "$pkg_hash" \
    'to_entries[] | select(.key == $pkg_hash) | .value' \
    "$json_dir/spack.location.json"
  )

  component=$(jq \
    --arg pkg "$pkg" \
    --arg install_path "$install_path" \
    '.concrete_specs | to_entries[] | select(.value.name == $pkg)
    | {
      spack_hash: .key,
      spec: (.value.name + "@" + .value.version),
      install_path: $install_path
    }' "$json_dir/spack.lock"
  )

  # piecewise construction of the entire build_metadata.json for each
  # build_component
  jq \
    --argjson component "$component" \
    '.component_build += [$component]' \
    "$output_dir/build_metadata.json" > "$output_dir/build_metadata.json.tmp"

  mv "$output_dir/build_metadata.json.tmp" "$output_dir/build_metadata.json"

  cat "$output_dir/build_metadata.json"
done
