#!/bin/bash
set -x
set -e

### INPUTS ###
# Root Spack Bundle Definition name for the given model. Usually the name of the model (e.g. access-om2)
ROOT_SBD=$1

FAILED='false'
DEPS=$(yq ".spack.modules.default.tcl.include | join(\" \")" spack.yaml)

# for each of the modules
for DEP in $DEPS; do
  DEP_VER=''
  if [[ "$DEP" == "$ROOT_SBD" ]]; then
    DEP_VER=$(yq '.spack.specs[0] | split("@git.") | .[1]' spack.yaml)
  else
    # Capture the section after '@git.' or '@' (if it's not a git-attributed version) and before a possible '=' for a given dependency.
    # Ex. '@git.2024.02.11' -> '2024.02.11', '@access-esm1.5' -> 'access-esm1.5', '@git.2024.05.21=access-esm1.5' -> '2024.05.21'
    DEP_VER=$(yq ".spack.packages.\"$DEP\".require[0] | match(\"^@(?:git.)?([^=]*)\").captures[0].string" spack.yaml)
  fi

  MODULE_NAME=$(yq ".spack.modules.default.tcl.projections.\"$DEP\"" spack.yaml)
  MODULE_VER="${MODULE_NAME#*/}"  # Get 'version' from 'name/version' module, even if version contains '/'

  if [[ "$DEP_VER" != "$MODULE_VER" ]]; then
    echo "::error::$DEP: Version of dependency and projection do not match ($DEP_VER != $MODULE_VER)"
    FAILED='true'
  fi
done
if [[ "$FAILED" == "true" ]]; then
  exit 1
fi