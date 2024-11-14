SPACK_YAML_PATH="$1"
ROOT_SBD="$2"

FAILED="false"

# Get all the defined projections (minus 'all') and make them suitable for a bash for loop
DEPS=$(yq '.spack.modules.default.tcl.projections | del(.all) | keys | join(" ")' "$SPACK_YAML_PATH")

# for each of the modules
for DEP in $DEPS; do
  DEP_VER=''
  if [[ "$DEP" == "$ROOT_SBD" ]]; then
    DEP_VER=$(yq '.spack.specs[0] | split("@git.") | .[1]' "$SPACK_YAML_PATH")
  else
    # Capture the section after '@git.' or '@' (if it's not a git-attributed version) and before a possible '=' for a given dependency.
    # Ex. '@git.2024.02.11' -> '2024.02.11', '@access-esm1.5' -> 'access-esm1.5', '@git.2024.05.21=access-esm1.5' -> '2024.05.21'
    DEP_VER=$(yq ".spack.packages.\"$DEP\".require[0] | match(\"^@(?:git.)?([^=]*)\").captures[0].string" "$SPACK_YAML_PATH")
  fi

  # Get the version from the module projection, for comparison with DEP_VER
  # Projections are of the form '{name}/VERSION[-{hash:7}]', in which we only care about VERSION. For example, '{name}/2024.11.11', or '{name}/2024.11.11-{hash:7}'
  MODULE_NAME=$(yq ".spack.modules.default.tcl.projections.\"$DEP\"" "$SPACK_YAML_PATH")
  MODULE_VER="${MODULE_NAME#*/}"  # Strip '{name}/' from '{name}/VERSION' module, even if VERSION contains '/'
  MODULE_VER="${MODULE_VER%%-\{hash:7\}}"  # Strip a potential '-{hash:7}' appendix from the VERSION, since we won't have that in the DEP_VER

  if [[ "$DEP_VER" != "$MODULE_VER" ]]; then
    echo "::error::$DEP: Version of dependency and projection do not match ($DEP_VER != $MODULE_VER)"
    FAILED='true'
  fi
done
if [[ "$FAILED" == "true" ]]; then
  exit 1
fi