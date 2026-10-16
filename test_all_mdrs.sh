#!/bin/bash

# This script tests yamllint on all ACCESS-NRI's MDRs repos.

yamllint_config=.github/actions/get-spack-manifest/yamllint_config.yml

model_tools=(babeltrace2 esmf fre-nctools mppcombine-fast)
system_tools=(gh ncdu openssh pinentry yq)

if [[ -z $(command -v yamllint) ]] || [[ $(yamllint --version) != "yamllint 1.38.0" ]]; then
    echo "yamllint version 1.38.0 not found. Installing it in a temporary virtual environment..."
    tmpdir=$(mktemp -d)

    # Cleanup
    trap 'rm -rf "$tmpdir" && echo "Temporary virtual environment cleaned up"' EXIT

    # Install yamllint version 1.38.0 (same as the ubuntu-latest GitHub runner)
    python3 -m venv "$tmpdir/yamllint-env"
    source "$tmpdir/yamllint-env/bin/activate"
    python3 -m pip install yamllint==1.38.0
fi

# Search for all ACCESS-NRI's MDRs `main` branches and for each of them:
# 1. Get content of the spack.yaml file
# 2. Run yamllint on the repository using the specified configuration file
for repo in $(
    gh search repos \
      --owner access-nri \
      --archived=false \
      --json name \
      --jq "[.[].name] | join(\" \")" \
      -- topic:deployment topic:spack -topic:template.
)
do
    if [ "$repo" == "system-tools" ]; then
        for tool in "${system_tools[@]}"; do
            echo "Linting $repo/$tool/spack.yaml"
            curl -L -s https://raw.githubusercontent.com/access-nri/$repo/refs/heads/main/$tool/spack.yaml | \
              yamllint -c "$yamllint_config" -
        done
    elif [ "$repo" == "model-tools" ]; then
        for tool in "${model_tools[@]}"; do
            echo "Linting $repo/$tool/spack.yaml"
            curl -L -s https://raw.githubusercontent.com/access-nri/$repo/refs/heads/main/$tool/spack.yaml | \
              yamllint -c "$yamllint_config" -
        done
    else
        echo "Linting $repo/spack.yaml"
        curl -L -s https://raw.githubusercontent.com/access-nri/$repo/refs/heads/main/spack.yaml | \
          yamllint -c "$yamllint_config" -
    fi
done