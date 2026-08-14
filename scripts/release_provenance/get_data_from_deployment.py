#!/usr/bin/env spack-python
import sys
import argparse
import json
import hashlib
import os
from pathlib import Path
from typing import Any

import spack.environment
import spack.error
import spack.cmd
import spack.config
import spack.spec
import spack.repo
import spack.main


def main():
    args = parse_args(sys.argv[1:])
    packages: list[str] = args.packages.split(",") if args.packages else []
    config_scopes_base_dir: str = args.config_scopes_base_dir
    config_scopes: list[str] = args.config_scopes.split(",") if args.config_scopes else []
    output_path = Path(args.output)

    # Custom scopes added via spack --config-scope for install need to be added back here
    # so we can find those packages!
    if config_scopes_base_dir:
        add_custom_spack_config_scopes(config_scopes_base_dir, config_scopes)

    # Activate the spack environment so we can get relevant specs for this deployment
    spack_env = activate_spack_environment(args.environment)

    # Get paths for all packages in the environment, output as a spack.location file
    all_specs: list[spack.spec.Spec] = spack_env.all_specs()

    with open(output_path / "spack.location", 'w') as f:
        spack.cmd.display_specs(all_specs, paths=True, output=f)

    # Get spack root specs in the environment
    root_specs: list[spack.spec.Spec] = [spec for spec in all_specs if spec.satisfies(args.deployment_name)]

    if len(root_specs) == 0:
        raise RuntimeError("There are no root specs matching the deployment name in the environment")
    else:
        # FIXME: We currently throw an exception, in the unsupported cases there are multiple root specs. See #333
        root_spec = root_specs[0]
        if len(root_specs) > 1:
            raise RuntimeError(f"Multiple root specs ({root_specs}) in one manifest detected. We don't yet support multiple root specs in one deployment.")

    with open(output_path / "root-spec-pkg-hash.txt", 'w') as f:
        f.write(root_spec.format('{hash}'))

    # Generate package metadata for the specified packages
    packages_metadata: list[dict[str, Any]] = generate_packages_metadata(packages, root_spec)

    print(packages_metadata)

    with open(output_path / "build-db-pkgs.json", 'w') as f:
        json.dump(packages_metadata, f)

def add_custom_spack_config_scopes(config_scopes_dir: str, config_scopes: list[str]) -> None:
    """
    Adds paths to custom spack config scopes to the command_line scope so we can find binaries for
    certain environments that use custom installation directories.

    :param config_scopes_dir: Absolute path that contains custom spack configuration scopes given by --custom-scopes
    :type config_scopes_dir: str
    :param config_scopes: Names of custom scopes from spack-configs custom/cd directory.
    :type config_scopes: list[str]
    """
    config_scopes_path = Path(config_scopes_dir)
    config_scope_paths: list[str] = [str(config_scopes_path / s) for s in config_scopes]

    print(f"Attempting to load custom scopes: {config_scope_paths}")

    try:
        spack.main.add_command_line_scopes(spack.config.CONFIG, config_scope_paths)
    except spack.error.ConfigError:
        print(f"Failed to find valid config scope in paths {config_scope_paths}.")
        raise

def activate_spack_environment(spack_env_path: str) -> spack.environment.Environment:
    spack_env = spack.environment.Environment(spack_env_path)

    spack.environment.activate(spack_env)

    if not spack_env.active:
        raise RuntimeError(f"Failed to activate spack environment at {spack_env_path}")

    return spack_env


def generate_packages_metadata(package_names: list[str], root_spec: spack.spec.Spec) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []

    for package_name in package_names:
        try:
            package: spack.spec.Spec = root_spec[package_name]
        except KeyError:
            print(f"{package} is not in the dependency chain of {root_spec}, can't upload to build database. Exiting...")
            raise

        package_hash: str  = package.format('{hash}')
        package_location: str = package.format('{prefix}')
        package_repo_url: str
        package_repo_version: str
        package_repo_url, package_repo_version = _get_package_repo_info(package)

        md5s_of_binaries = generate_md5s_for_package_binaries(package)

        metadata.append({
            "name": package_name,
            "version": package_repo_version,
            "hash": package_hash,
            "location": package_location,
            "url": package_repo_url,
            "md5s": md5s_of_binaries
        })

    return metadata

def _get_package_repo_info(package: spack.spec.Spec) -> Tuple[str, str]:
    """
    Get package repo information from the package.py file.
    This is different for certain packages like the um, which have variants and structs in the
    package.py file that have that information.
    Returns: A pair composed of a git url and a git ref
    """
    package_name = package.name

    if package.name == "um":
        return _get_package_repo_info_of_um(package)
    else:
        return _get_package_repo_info_of_package(package)

def _get_package_repo_info_of_um(package: spack.spec.Spec) -> Tuple[str, str]:
    um_class = spack.repo.PATH.get_pkg_class(package.name)
    um_git_url = um_class._project_cfg[package.name].get('url')
    um_git_ref = package.variants.get("um_ref")

    if not um_git_url or not um_git_ref:
        raise RuntimeError("The package 'um' needs to have a git url specified in _project_cfg and the um_ref variant for provenance.")

    return (
        um_git_url,
        um_git_ref.value
    )

def _get_package_repo_info_of_package(package: spack.spec.Spec) -> Tuple[str, str]:
    return (
        spack.repo.PATH.get_pkg_class(package.name).git,
        package.format("{version}")
    )

def generate_md5s_for_package_binaries(package: spack.spec.Spec) -> list[dict[str, str]]:
    md5s: list[dict[str, str]] = []

    bin_paths = [
        directory
        for directory in Path(package.prefix).rglob("bin")
        if directory.is_dir()
    ]

    if not bin_paths:
        return md5s

    executables = [
        executable
        for bin_path in bin_paths
        for executable in bin_path.rglob('*')
        if executable.is_file() and os.access(executable, os.X_OK)
    ]

    for executable in executables:
        with open(executable, 'rb') as executable_file, open(executable.with_suffix(executable.suffix + ".md5"), 'w') as md5_file:
            hash = hashlib.md5(executable_file.read()).hexdigest()
            md5_file.write(hash)

        md5s.append({
            "path": str(executable),
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

    parser.add_argument(
        "--config-scopes-base-dir",
        type=str,
        required=False,
        help="Absolute path to a directory that contains custom spack configuration scopes given by --custom-scopes"
    )

    parser.add_argument(
        "--config-scopes",
        type=str,
        required=False,
        help="Comma-separated list of custom spack config scopes defined in spack-configs custom/cd directory"
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
