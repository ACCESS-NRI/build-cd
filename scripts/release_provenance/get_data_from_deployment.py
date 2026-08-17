#!/usr/bin/env spack-python
import sys
import argparse
import json
import hashlib
import os
from pathlib import Path
from typing import Any
from abc import ABC, abstractmethod

import spack.environment
import spack.error
import spack.cmd
import spack.config
import spack.spec
import spack.main
import spack.variant
import spack.util.git

class SpecInfo(ABC):
    def __init__(self, spec: spack.spec.Spec):
        self.spec = spec

    # We have the below two abstract methods because getting package versions and commit URLs are very
    # different for UM vs non-UM packages.
    @abstractmethod
    def get_package_version(self) -> str:
        pass

    @abstractmethod
    def get_commit_url(self) -> str:
        pass

    def get_prefix(self) -> str:
        return self.spec.prefix

    def get_hash(self) -> str:
        return self.spec.dag_hash()

    def _build_commit_url(self, url: str, commit: str) -> str:
        """
        Builds a web-browsable commit url from a git url.

        Git urls are commonly suffixed with '.git', which is valid for cloning but 404s when
        used to build a '/commit/<sha>' url, so it is stripped here.

        :param url: Git url of the repository
        :type url: str
        :param commit: Full commit sha
        :type commit: str
        """
        return f"{url.rstrip('/').removesuffix('.git')}/commit/{commit}"

    def generate_md5s_for_package_binaries(self) -> list[dict[str, str]]:
        md5s: list[dict[str, str]] = []

        bin_paths = [
            directory
            for directory in Path(self.spec.prefix).rglob("bin")
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


class UmSpecInfo(SpecInfo):
    def __init__(self, spec: spack.spec.Spec):
        super().__init__(spec)

    def get_package_version(self) -> str:
        um_ref_variant: spack.variant.VariantValue | None = self.spec.variants.get("um_ref")

        if not um_ref_variant:
            raise RuntimeError(f"The package 'um' needs a um_ref defined in the environment for provenance.")

        um_ref: str = str(um_ref_variant.value)

        return um_ref

    def get_commit_url(self) -> str:
        um_ref = self.get_package_version()

        um_git_url = self.spec.package._project_cfg[self.spec.name].get('url') # type: ignore (because we are using access-spack-packages UmBasePackage not BasePackage)

        if not um_git_url:
            raise RuntimeError("The package 'um' needs to have a git url specified in _project_cfg for provenance.")

        um_commit = self._get_commit_from(um_git_url, um_ref)
        um_git_commit_url = self._build_commit_url(um_git_url, um_commit)

        return um_git_commit_url

    def _get_commit_from(self, url: str, ref: str) -> str:
        """
        Resolves a git ref (branch, tag or commit) to a full commit sha by querying the remote.

        :param url: Git url of the repository to query
        :type url: str
        :param ref: Branch, tag or commit sha to resolve
        :type ref: str
        """
        if spack.util.git.is_git_commit_sha(ref):
            return ref

        commit_sha: str | None = spack.util.git.get_commit_sha(url, ref)

        if not commit_sha:
            raise RuntimeError(f"Failed to resolve the ref '{ref}' against '{url}', can't determine commit for provenance.")

        return commit_sha


class PackageSpecInfo(SpecInfo):
    def __init__(self, spec: spack.spec.Spec):
        super().__init__(spec)

    def get_package_version(self) -> str:
        return str(self.spec.version)

    def get_commit_url(self) -> str:
        git_url = self.spec.package.version_or_package_attr("git", self.spec.version, None)
        if not git_url:
            raise RuntimeError(f"The package '{self.spec.name}' needs to have a git url as part of the version or the git attribute for provenance.")

        commit_variant: spack.variant.VariantValue | None = self.spec.variants.get("commit")
        if not commit_variant:
            raise RuntimeError(f"The package '{self.spec.name}' needs to have a reserved commit variant for provenance.")

        commit = str(commit_variant.value)

        commit_url: str = self._build_commit_url(str(git_url), commit)

        return commit_url

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

def _generate_error_info_for_metadata(name: str, error: str) -> dict[str, str]:
    return {"name": name, "error": error}

def generate_packages_metadata(package_names: list[str], root_spec: spack.spec.Spec) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []

    for package_name in package_names:
        try:
            spec_wrapper: spack.spec.Spec | spack.spec.SpecBuildInterface = root_spec[package_name]
        except KeyError:
            error_msg=f"{package_name} is not in the dependency chain of {root_spec}, can't upload to build database."
            print(f"::warning::{error_msg}")
            metadata.append(_generate_error_info_for_metadata(package_name, error_msg))
            continue

        concrete_spec: spack.spec.Spec = spec_wrapper.wrapped_obj if isinstance(spec_wrapper, spack.spec.SpecBuildInterface) else spec_wrapper

        spec: SpecInfo = UmSpecInfo(concrete_spec) if concrete_spec.name == "um" else PackageSpecInfo(concrete_spec)

        package_hash: str  = spec.get_hash()
        package_location: str = spec.get_prefix()

        # Try and get the package version of a given package
        try:
            package_repo_version: str = spec.get_package_version()
        except RuntimeError as e:
            print(f"::warning::{e}")
            metadata.append(_generate_error_info_for_metadata(package_name, str(e)))
            continue

        # Try and get the commit URL of a given package
        try:
            package_commit_url: str = spec.get_commit_url()
        except RuntimeError as e:
            print(f"::warning::{e}")
            metadata.append(_generate_error_info_for_metadata(package_name, str(e)))
            continue

        md5s_of_binaries = spec.generate_md5s_for_package_binaries()

        metadata.append({
            "name": package_name,
            "version": package_repo_version,
            "hash": package_hash,
            "location": package_location,
            "url": package_commit_url,
            "md5s": md5s_of_binaries
        })

    return metadata

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
