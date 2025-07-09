import argparse
import yaml
import re

from typing import Any

def inject_prerelease_information(
    manifest_path: str, root_spec_name: str, root_spec_version: str, spack_packages_path: str | None = None
) -> str:
    # In comparison to the projections script, this returns a string rather than a dict because we need to
    # add spack-specific, non-standard 'repo::' sections, which the yaml dumper does not support.
    with open(manifest_path, "r") as manifest_file:
        manifest: dict[str, Any] = yaml.safe_load(manifest_file)

    # Remove @git.VERSION information from the root spec, since it will be a tag that does not yet exist for prereleases
    # This does not include versions of the form @VERSION, which are the hallmark of software deployment repositories.
    updated_manifest: dict[str, Any] = remove_potential_root_spec_git_version(
        manifest, root_spec_name
    )

    updated_manifest = update_root_spec_projection_version(updated_manifest, root_spec_name, root_spec_version)

    # Dump the current dict, and add the non-standard 'repo::' section
    manifest_str: str = yaml.dump(
        updated_manifest, default_flow_style=False, sort_keys=False
    )

    if spack_packages_path:
        # Add the 'repo::' section for prerelease spack packages if provided
        manifest_str = add_prerelease_repos_section(manifest_str, spack_packages_path)

    return manifest_str


def remove_potential_root_spec_git_version(manifest: dict[str, Any], root_spec_name: str) -> dict[str, Any]:
    """
    Remove the version information from the root spec in the manifest.
    This is necessary for prerelease deployments where the version may not yet exist.
    """
    root_spec: str = manifest["spack"]["specs"][0]

    # Use a regex to match the root spec and any later constraints, minus the @git version
    # This specifically excludes @VERSIONs, which are used for software deployment repositories.
    spec_regex = re.compile(fr"({root_spec_name})@git\.[^~+% ]+(.*)")

    component_match = re.match(spec_regex, root_spec)

    if component_match:
        # Remove the @git version and then add later contraints back
        spec_without_version = " ".join(m.lstrip() for m in component_match.groups())
        manifest["spack"]["specs"][0] = spec_without_version.strip()
    else:
        raise ValueError(
            f"Root spec '{root_spec}' not found in the manifest or does not match expected format."
        )

    return manifest

def update_root_spec_projection_version(
    manifest: dict[str, Any], root_spec_name: str, root_spec_version: str
) -> dict[str, Any]:
    updated_version: str = f"{{name}}/{root_spec_version}"

    manifest.setdefault("spack", {}).setdefault("modules", {}).setdefault("default", {}).setdefault("tcl", {}).setdefault("projections", {})

    manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_name] = updated_version

    return manifest

def add_prerelease_repos_section(
    manifest_str: str, spack_packages_path: str
) -> str:
        manifest_str += (
            f"  repos::\n"
            f"  - {spack_packages_path}\n"
            f"  - $spack/var/spack/repos/builtin\n"
        )

        return manifest_str

def parse_args():
    parser = argparse.ArgumentParser(
        description="Script for injecting prerelease information into spack manifest files."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Path to the spack manifest file to be injected with prerelease information",
    )

    parser.add_argument(
        "--root-spec",
        type=str,
        required=True,
        help="Name of the root spec of the deployment",
    )

    parser.add_argument(
        "--root-spec-version",
        type=str,
        required=True,
        help="Version to be used for the root spec projection in the manifest",
    )

    parser.add_argument(
        "--spack-packages-path",
        type=str,
        required=False,
        help="Local path to a spack-packages repository that is added to the manifests repos section",
    )

    parser.add_argument(
        "--output",
        type=str,
        required=False,
        help="Path to the output file where the modified manifest will be saved",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    injected_manifest: str = inject_prerelease_information(
        args.manifest, args.root_spec, args.root_spec_version, args.spack_packages_path
    )

    if args.output:
        with open(args.output, "w") as output_file:
            output_file.write(injected_manifest)
    else:
        print(injected_manifest)


if __name__ == "__main__":
    main()
