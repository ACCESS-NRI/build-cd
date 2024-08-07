#!/bin/bash

set -e

# Remember, script is in the form `generate-build-metadata.bash <release url> <release created at> <spack-packages version> <spack-config version> <metadata dir> <output dir> <root sbd> <packages>...`
# Where:
#   release url: is the URL of GitHub release of the entire model,
#   release created at: is the time the above release was created,
#   spack-packages version: is the git tag of ACCESS-NRI/spack-packages used
#   spack-config version: is the git tag of ACCESS-NRI/spack-config used
#   metadata dir: is the path to the directory containing the spack.lock and spack.location.json,
#   output dir: is the path to the directory that will contain the output,
#   root sbd: is the overarching SBD of the model, usually the model name,
#   packages...: are the rest of the arguments, being the packages within the model that we want metada about

if [[ $(basename "$PWD") != "generate-build-metadata" ]]; then
  echo "This test can only be run within the tests/scripts/generate-build-metadata directory"
  exit 1
fi

./../../../scripts/generate-build-metadata.bash http://example.org/releases 2024-03-27T05:29:36Z 2023.11.23 2024.01.01 ./inputs ./outputs access-om2 mom5 cice5

cmp ./outputs/build_metadata.json ./valid/build_metadata.json
