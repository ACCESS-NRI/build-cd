#!/usr/bin/env spack-python
import sys
import argparse
import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any

import spack.environment
import spack.error
import spack.cmd
import spack.config
import spack.spec
import spack.main
import spack.util.git

# Matches the ref portion of a spack spec version, eg. `git.2025.01.2=access-esm1.6` -> `2025.01.2`
SPEC_VERSION_REF_REGEX = r'^(?:git\.)?(?P<ref>[^=+~ ]+)'

# Matches the OWNER/REPO portion of a GitHub url
GITHUB_OWNER_REPO_REGEX = r"(?:github\.com)[:/](?P<owner_repo>[^/]+/[^/]+?)(?:\.git)?$"


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
            queried_package: spack.spec.Spec | spack.spec.SpecBuildInterface = root_spec[package_name]
        except KeyError:
            print(f"{package_name} is not in the dependency chain of {root_spec}, can't upload to build database. Exiting...")
            raise

        # Concrete specs might be returned wrapped in a `SpecBuildInterface`, so  we unwrap to get the `Spec` itself
        package: spack.spec.Spec = (
            queried_package.wrapped_obj
            if isinstance(queried_package, spack.spec.SpecBuildInterface)
            else queried_package
        )

        package_hash: str  = package.format('{hash}')
        package_location: str = package.format('{prefix}')
        package_version: str
        package_repository_url: str
        package_version, package_repository_url = _get_package_repo_info(package)

        md5s_of_binaries = generate_md5s_for_package_binaries(package)

        metadata.append({
            "name": package_name,
            "version": package_version,
            "hash": package_hash,
            "location": package_location,
            "repository_url": package_repository_url,
            "md5s": md5s_of_binaries
        })

    return metadata

def _get_package_repo_info(spec: spack.spec.Spec) -> tuple[str, str]:
    """
    Get package repo information from the package.py file.
    This is different for certain packages like the um, which have variants and structs in the
    package.py file that have that information.
    Returns: A pair composed of a human-readable version and a url to the exact commit the
    package was built from.
    """
    if spec.name == "um":
        return _get_package_repo_info_of_um(spec)
    else:
        return _get_package_repo_info_of_package(spec)

def _get_package_repo_info_of_um(spec: spack.spec.Spec) -> tuple[str, str]:
    """
    The 'um' builds its sources as spack resources rather than as a spack version, so there is no
    `commit` variant to read. Instead, the `um_ref` variant holds a branch/tag/commit that we
    resolve against the remote ourselves.
    Returns: A pair composed of a human-readable version and a commit url
    """
    um_git_url = spec.package._project_cfg[spec.name].get('url') # type: ignore (It's not a spack.package_base.PackageBase but a UmBasePackage subclass from ASP)
    um_ref_variant = spec.variants.get("um_ref")

    if not um_git_url or not um_ref_variant:
        raise RuntimeError("The package 'um' needs to have a git url specified in _project_cfg and the um_ref variant for provenance.")

    um_git_url = str(um_git_url)
    um_ref = str(um_ref_variant.value)

    commit_sha = _resolve_ref_to_commit_sha(um_git_url, um_ref)

    return (
        _version_from_spec_version(um_ref),
        _github_commit_url(um_git_url, commit_sha)
    )

def _get_package_repo_info_of_package(spec: spack.spec.Spec) -> tuple[str, str]:
    """
    Get the version of a spec, and a url to the commit that spack resolved that version to
    during concretization.
    Returns: A pair composed of a human-readable version and a commit url
    """
    version = spec.version

    # `version()` directives can override the package-level `git` url (not that we expect that to happen with our packages)
    git_url = spec.package.version_or_package_attr("git", version, None)

    if not git_url:
        raise RuntimeError(
            f"The package '{spec.name}' needs a git url specified on the package or on the "
            f"`version()` directive of version '{version}' for provenance."
        )

    # A concretized spec records the commit sha it resolved the version to in the `commit` variant.
    # Spack only warns when it can't resolve one (but it will pull correctly at install time),
    # so we have to fail here to avoid recording a mutable ref like a branch name.
    commit_variant = spec.variants.get("commit")

    if not commit_variant:
        raise RuntimeError(
            f"The package '{spec.name}' has no `commit` variant even though it has a git repository,"
            f"meaning spack could not resolve version '{version}' to a commit sha during concretization, but it installed correctly."
        )

    git_ref = commit_variant.value

    return (
        _version_from_spec_version(str(version)),
        _github_commit_url(str(git_url), str(git_ref))
    )

def _version_from_spec_version(spec_version: str) -> str:
    """
    Extracts a human-readable version from a spack spec version string, stripping the `git.` prefix
    and any `=version` suffix used by specs that are still pinned to an explicit git ref.
    eg. `git.2025.01.2=access-esm1.6` -> `2025.01.2`, or `CICE6.0-1` -> `CICE6.0-1`
    """
    match = re.search(SPEC_VERSION_REF_REGEX, spec_version)

    if not match:
        raise RuntimeError(f"Invalid spec version: {spec_version}")

    return match.group("ref")

def _github_commit_url(git_url: str, commit_sha: str) -> str:
    """
    Builds a url pointing at an exact commit of a GitHub repository.
    """
    match = re.search(GITHUB_OWNER_REPO_REGEX, git_url)

    if not match:
        raise RuntimeError(f"Invalid GitHub repository url: {git_url}")

    return f"https://github.com/{match.group('owner_repo')}/commit/{commit_sha}"

def _resolve_ref_to_commit_sha(git_url: str, ref: str) -> str:
    """
    Resolves a branch/tag/commit to a full commit sha by querying the remote.
    """
    if spack.util.git.is_git_commit_sha(ref):
        return ref

    sha_of_ref: str | None = spack.util.git.get_commit_sha(git_url, ref)
    if not sha_of_ref:
        raise RuntimeError(
            f"Could not resolve ref '{ref}' of '{git_url}' to a commit sha. A resolved commit sha is required for provenance."
        )
    return sha_of_ref

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
