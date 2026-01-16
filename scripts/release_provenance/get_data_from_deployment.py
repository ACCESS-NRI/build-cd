#!/usr/bin/env spack python
import sys
import argparse
import json
import os.path
import hashlib
from typing import Any

import spack.environment
import spack.cmd
import spack.spec


def main():
    args = parse_args(sys.argv[1:])
    packages: list[str] = args.packages.split(",")

    # Activate the spack environment so we can get relevant specs for this deployment
    spack_env = activate_spack_environment(args.environment)

    # Get paths for all packages in the environment, output as a spack.location file
    all_specs: list[spack.spec.Spec] = spack_env.all_specs()

    with open(os.path.join(args.output, "spack.location"), 'w') as f:
        spack.cmd.display_specs(all_specs, paths=True, output=f)

    # Get spack root specs in the environment
    root_specs: list[spack.spec.Spec] = [spec for spec in all_specs if spec.satisfies(args.deployment_name)]

    if len(root_specs) == 0:
        raise RuntimeError("There are no root specs matching the deployment name in the environment")
    else:
        # FIXME: We currently pick the first root spec, in the unsupported cases there are multiple root specs. See #333
        root_spec = root_specs[0]
        if len(root_specs) > 1:
            print(f"Multiple root specs ({root_specs}) in one manifest detected. Taking the first one as the release database doesn't support multiple.")

    with open(os.path.join(args.output, "root-spec-pkg-hash.txt"), 'w') as f:
        f.write(root_spec.format('{hash}'))

    # Generate package metadata for the specified packages
    packages_metadata: list[dict[str, Any]] = generate_packages_metadata(packages, root_spec)

    print(packages_metadata)

    with open(os.path.join(args.output, "build-db-pkgs.json"), 'w') as f:
        json.dump(packages_metadata, f)

def activate_spack_environment(spack_env_path: str) -> spack.environment.Environment:
    spack_env = spack.environment.Environment(spack_env_path)

    spack.environment.activate(spack_env)

    if not spack_env.active:
        raise RuntimeError(f"Failed to activate spack environment at {spack_env_path}")

    return spack_env


def generate_packages_metadata(package_names: list[str], root_spec: spack.spec.Spec) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []

    for package_name in package_names:
        root_spec_deps: list[spack.spec.Spec] = root_spec.dependencies(name=package_name)

        if len(root_spec_deps) > 1:
            raise RuntimeError(f"Multiple dependencies found for package {package_name} in root spec {root_spec}. Cannot uniquely identify package.")

        package: spack.spec.Spec = root_spec_deps[0]

        package_hash: str  = package.format('{hash}')
        package_version: str = package.format('{version}')
        package_location: str = package.format('{prefix}')
        # TODO: This is unsupported in spack > 1.0 - use spack.repo.PATH.get_pkg_class('$pkg').git)"
        package_repo_url: str = package.package_class.git

        md5s_of_binaries = generate_md5s_for_package_binaries(package)

        metadata.append({
            "name": package_name,
            "version": package_version,
            "hash": package_hash,
            "location": package_location,
            "url": package_repo_url,
            "md5s": md5s_of_binaries
        })

    return metadata


def generate_md5s_for_package_binaries(package: spack.spec.Spec) -> list[dict[str, str]]:
    md5s: list[dict[str, str]] = []

    bin_dir = os.path.join(package.prefix, "bin")

    if not os.path.exists(bin_dir):
        return md5s

    # TODO: Check if this gives the appropriate path
    executables = [
        path
        for path in os.listdir(bin_dir)
        if os.path.isfile(path) and os.access(path, os.X_OK)
    ]

    for executable in executables:
        with open(executable, 'rb') as binary, open(executable + ".md5", 'w') as md5:
            hash = hashlib.file_digest(binary, 'md5').hexdigest()
            md5.write(hash)

        md5s.append({
            "path": executable,
            "md5": hash
        })

    return md5s


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script for generating package build metadata for tracking services release provenance database."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--environment",
        type=str,
        required=True,
        help="Path to the spack environment used for the model deployment",
    )

    parser.add_argument(
        "--deployment-name",
        type=str,
        required=True,
        help="Name of the deployment, which also corresponds to the root specs being deployed"
    )

    parser.add_argument(
        "--packages",
        type=str,
        required=True,
        help="Comma-separated list of packages to extract build metadata for",
    )

    ## Args dealing with outputs
    parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Path to a folder to dump deployment data"
    )

    return parser.parse_args(args)


if __name__ == "__main__":
    main()
