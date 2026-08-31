#!/usr/bin/env spack-python
import sys
import argparse
import json
import hashlib
import os
from pathlib import Path
from typing import Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

import spack.environment
import spack.error
import spack.cmd
import spack.config
import spack.spec
import spack.main
import spack.variant
import spack.version
import spack.util.git



@dataclass(frozen=True)
class SpecProvenance():
    """
    We require git provenance of our spack specs, so we need to know the version, commit hash,
    and a web-browsable url for the ref.
    """
    version: str
    commit_hash: str
    ref_url: str

class SpecInfo(ABC):
    def __init__(self, spec: spack.spec.Spec):
        self.spec = spec

    def to_metadata(self) -> dict[str, Any]:
        try:
            provenance: SpecProvenance = self._resolve_provenance()
        except RuntimeError as e:
            print(f"::warning::{e}")
            return {"name": self.spec.name, "error": str(e)}

        return {
            "name": self.spec.name,
            "version": provenance.version,
            "commit": provenance.commit_hash,
            "hash": self.spec.dag_hash(),
            "location": str(self.spec.prefix),
            "url": provenance.ref_url,
            "md5s": self.generate_md5s_for_package_binaries()
        }

    # We have this abstract method because getting provenance is very
    # different for UM vs non-UM packages.
    @abstractmethod
    def _resolve_provenance(self) -> SpecProvenance:
        pass

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

    def _get_ref_type(self, url: str, ref: str) -> str:
        """
        Determines the type of a git ref (branch, tag, or commit) for a given url and ref.

        Uses `git ls-remote` so the repository does not need to be cloned. If the ref matches
        a full-length commit, this is returned, otherwise we check for the ref under
        refs/tags and refs/heads for tags and braches respectively.

        :param url: Git url of the repository
        :type url: str
        :param ref: Branch name, tag name or commit sha
        :type ref: str
        """
        if spack.util.git.is_git_commit_sha(ref):
            return "commit"

        git_exe = spack.util.git.git(required=True)

        # A branch maps to refs/heads/ and a tag maps to refs/tags/.
        for ref_type, namespace in (("tag", "tags"), ("branch", "heads")):
            git_exe(
                "ls-remote",
                "--exit-code",
                f"--{namespace}",
                url,
                f"refs/{namespace}/{ref}",
                output=os.devnull,
                error=os.devnull,
                fail_on_error=False,
            )

            if git_exe.returncode == 0:
                return ref_type

        return "unknown"

    def _build_ref_url(self, url: str, ref: str, ref_type: str) -> str:
        """
        Builds a web-browsable url for a ref, based on the type of that ref.
        """
        base_url = url.rstrip('/').removesuffix('.git')

        match ref_type:
            case "tag":
                return f"{base_url}/releases/tag/{ref}"
            case "branch":
                return f"{base_url}/tree/{ref}"
            case "commit":
                return f"{base_url}/commit/{ref}"
            case _:
                raise RuntimeError(f"Unknown git ref type '{ref_type}' for ref '{ref}' of {url}.")


class UmSpecInfo(SpecInfo):
    def __init__(self, spec: spack.spec.Spec):
        super().__init__(spec)

    def _resolve_provenance(self) -> SpecProvenance:
        version = self.get_package_version()
        git_url = self.get_git_url()
        ref_url = self.get_ref_url(git_url, version)
        commit_hash = self.get_commit_hash(version, git_url)

        return SpecProvenance(
            version=version,
            commit_hash=commit_hash,
            ref_url=ref_url,
        )

    def get_package_version(self) -> str:
        um_ref_variant: spack.variant.VariantValue | None = self.spec.variants.get("um_ref")

        if not um_ref_variant:
            raise RuntimeError(f"The package 'um' needs a um_ref defined in the environment for provenance.")

        um_ref: str = str(um_ref_variant.value)

        return um_ref

    def get_git_url(self) -> str:
        um_git_url = self.spec.package._project_cfg[self.spec.name].get('url') # type: ignore (because we are using access-spack-packages UmBasePackage not BasePackage)

        if not um_git_url:
            raise RuntimeError("The package 'um' needs to have a git url specified in _project_cfg for provenance.")

        return um_git_url

    def get_ref_url(self, git_url: str, version: str) -> str:
        ref_type = self._get_ref_type(git_url, version)
        um_git_ref_url = self._build_ref_url(git_url, version, ref_type)

        return um_git_ref_url

    def get_commit_hash(self, version: str, url: str) -> str:
        um_sha = spack.util.git.get_commit_sha(url, version)

        if not um_sha:
            raise RuntimeError(f"Unable to get SHA from ref {version} at {url} for {self.spec.name}")

        return um_sha

class PackageSpecInfo(SpecInfo):
    def __init__(self, spec: spack.spec.Spec):
        super().__init__(spec)

    def _resolve_provenance(self) -> SpecProvenance:
        version = self.get_package_version()
        ref_url = self.get_ref_url()
        commit_hash = self.get_commit_hash()

        return SpecProvenance(
            version=version,
            commit_hash=commit_hash,
            ref_url=ref_url,
        )

    def get_package_version(self) -> str:
        return str(self.spec.version)

    def get_commit_hash(self) -> str:
        commit_variant: spack.variant.VariantValue | None = self.spec.variants.get("commit")
        if not commit_variant:
            raise RuntimeError(f"The package '{self.spec.name}' needs to have a reserved commit variant for provenance.")

        return str(commit_variant.value)

    def get_ref_url(self) -> str:
        git_url = str(self.spec.package.version_or_package_attr("git", self.spec.version))

        resolved_ref = self._resolve_spack_ref(git_url)
        ref_type: str = self._get_ref_type(git_url, resolved_ref)

        url: str = self._build_ref_url(git_url, resolved_ref, ref_type)

        return url

    def _resolve_spack_ref(self, url: str) -> str:
        # ConcreteVersion superclasses StandardVersion (@2025.01.001) and GitVersion (@git.REF) - we need to handle either case
        version: spack.version.ConcreteVersion = self.spec.version

        if isinstance(version, spack.version.StandardVersion):
            # Fetch the version info from the version() function in the package.py
            pkg_version = self.spec.package.versions.get(version)
            if pkg_version is None:
                raise RuntimeError(f"Package {self.spec.name} is missing a version() for {version}, despite installing successfully")

            resolved_ref = pkg_version.get("tag") or pkg_version.get("branch") or pkg_version.get("commit")

            if resolved_ref:
                return resolved_ref
            else:
                raise RuntimeError(f"Unknown standard version format for {self.spec.name} version {version}")

        elif isinstance(version, spack.version.GitVersion) and version.ref:
            return version.ref
        else:
            raise NotImplementedError(f"Haven't yet handled a non-GitVersion/StandardVersion for {self.spec.name} version {version}")

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

        metadata.append(spec.to_metadata())

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
