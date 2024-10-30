#!/bin/bash

set -e

if [[ $(basename "$PWD") != "projection-check" ]]; then
  echo "This test can only be run within the tests/scripts/ci/projection-check directory"
  exit 1
fi

echo "Attempting to parse valid spack.yaml..."
if ! ./../../../../scripts/ci/projection-check.bash "./inputs/valid.spack.yaml" "access-esm1p5"; then
  echo "!!! Attempting to parse a valid spack.yaml failed."
  echo "!!! This means that there is an error with the script."
fi

echo "Attempting to parse invalid spack.yaml (error output is expected)..."
if ./../../../../scripts/ci/projection-check.bash "./inputs/invalid.spack.yaml" "access-esm1p5"; then
  echo "!!! Failing to parse an invalid spack.yaml failed."
  echo "!!! This means that there is an error with the script."
fi
