import argparse
import yaml
import re
import sys

from typing import Any
from copy import deepcopy

from scripts.spack_manifest.getter import (
    RootSpec,
    Projections,
)


# PyYaml by default dumps unquoted strings if they look unambiguous, and quoted strings otherwise.
# PyYaml dumps '{name}/prX-Y' as a quoted str as it has '{' at the front and causes ambiguity
# But 'ROOT_SPEC/.dependencies/prX-Y/VERSION-{hash:7}' is dumped as an unquoted str as it is unambiguous
# So we need to wrap projections in a custom class that forces PyYaml to dump them as quoted strings.
class YamlExplicitQuotedString(str):
    pass


def yaml_explicit_quoted_string_representer(dumper, data):
    """
    Custom representer for YAML to ensure that some strings are quoted explicitly.
    This is necessary for strings that are used as projections in spack manifests.
    """
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")


yaml.add_representer(YamlExplicitQuotedString, yaml_explicit_quoted_string_representer)

### Actual methods begin here ###


def inject_prerelease_information(
    manifest_path: str,
    version: str,
    custom_root_projection: str | None = None,
    keep_root_spec_intact: bool = False,
    spack_packages_path: str | None = None,
) -> str:
    # In comparison to the projections script, this returns a string rather than a dict because we need to
    # add spack-specific, non-standard 'repo::' sections, which the yaml dumper does not support.
    with open(manifest_path, "r") as manifest_file:
        manifest: dict[str, Any] = yaml.safe_load(manifest_file)

    root_spec_from_manifest = RootSpec(manifest)
    root_spec_name = root_spec_from_manifest.get_name()

    updated_manifest: dict[str, Any] = deepcopy(manifest)

    # Remove @git.VERSION information from the root spec, since it will be a tag that does not yet exist for prereleases
    # This does not include versions of the form @VERSION, which are the hallmark of software deployment repositories,
    # or builds that explicitly ask to keep_root_spec_intact.
    if not keep_root_spec_intact:
        updated_manifest = remove_potential_root_spec_git_version(manifest)

    # We want the root spec projection to be of the form {name}/prX-Y
    updated_manifest = update_root_spec_projection_version(
        updated_manifest, root_spec_name, version, custom_root_projection
    )

    # We want all other projections to be of the form {name}/prX-Y/VERSION
    updated_manifest = add_namespace_to_other_projection_versions(
        updated_manifest, root_spec_name, version
    )

    if spack_packages_path:
        # Add the 'repo:' section for prerelease spack packages if provided
        updated_manifest = add_prerelease_repos_section(
            updated_manifest, spack_packages_path
        )

    # Dump the current dict, and add the non-standard 'repo::' section
    manifest_str: str = yaml.dump(
        updated_manifest, default_flow_style=False, sort_keys=False
    )

    return manifest_str


def add_namespace_to_other_projection_versions(
    manifest: dict[str, Any], root_spec_name: str, version: str
) -> dict[str, Any]:
    # We don't want to modify the linked manifest dict, so we create a mutable copy.
    mutable_manifest: dict[str, Any] = deepcopy(manifest)
    projections_from_manifest = Projections(mutable_manifest)
    projections = projections_from_manifest.get()

    # We only want to modify projections that are not the root spec, since that already has its version set
    if root_spec_name in projections:
        projections.pop(root_spec_name)

    for projection_name, projection_value in projections.items():
        # Non-root-spec projections will be of the form ROOT_SPEC_NAME/prX-Y/{name}/VERSION, where VERSION is previously defined.
        # For example, access-om2/pr12-13/mom5/main-{hash:7}
        new_projection_value = re.sub(
            r"{name}/(.+)", rf"{root_spec_name}/dependencies/{version}/{{name}}/\1", projection_value
        )

        print(
            f"Updating projection '{projection_name}' from '{projection_value}' to '{new_projection_value}'"
        )

        # Ensures that the new projection is a quoted string when dumped so spack does projected modules correctly, see top of file.
        manifest["spack"]["modules"]["default"]["tcl"]["projections"][projection_name] = YamlExplicitQuotedString(new_projection_value)

    return manifest


def remove_potential_root_spec_git_version(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Remove the version information from the root spec in the manifest.
    This is necessary for prerelease deployments where the version may not yet exist.
    """
    root_spec_from_manifest = RootSpec(manifest)
    name = root_spec_from_manifest.get_name()
    constraints = root_spec_from_manifest.get_non_version_constraints()

    if root_spec_from_manifest.has_git_ref():
        # Remove the @git version and then add later contraints back
        manifest["spack"]["specs"][0] = f"{name} {constraints}".strip()
    else:
        print(
            f"The root spec '{name}' does not have a git ref, so no changes are made."
        )

    return manifest


def update_root_spec_projection_version(
    manifest: dict[str, Any], root_spec_name: str, root_spec_version: str, custom_root_projection: str | None = None
) -> dict[str, Any]:

    if custom_root_projection is not None and custom_root_projection != "":
        projection_components = custom_root_projection.split("/", 1)

        if len(projection_components) == 1:
            updated_version: str = f"{{name}}/{root_spec_version}/{projection_components[0]}"
        else:
            updated_version: str = f"{{name}}/{root_spec_version}/{projection_components[1]}"
    else:
        updated_version: str = f"{{name}}/{root_spec_version}"

    manifest.setdefault("spack", {}).setdefault("modules", {}).setdefault("default", {}).setdefault("tcl", {}).setdefault("projections", {})

    manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_name] = updated_version

    return manifest


def add_prerelease_repos_section(
    manifest: dict[str, Any], spack_packages_path: str
) -> dict[str, Any]:

    manifest.setdefault("spack", {}).setdefault("repos", {})
    manifest["spack"]["repos"] = {
        "access_spack_packages": {
            "git": "https://github.com/ACCESS-NRI/access-spack-packages.git",
            "destination": spack_packages_path,
        }
    }

    return manifest


def parse_args(args: list[str]) -> argparse.Namespace:
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
        "--version",
        type=str,
        required=True,
        help="Version to be used for projections in the manifest",
    )

    parser.add_argument(
        "--custom-root-projection",
        type=str,
        required=False,
        help="Custom projection string to be used for the root spec in the manifest",
    )

    # This option is for the special case where the root spec defined at the repository level (a bundle with
    # a version that doesn't yet exist) is not the same as the root spec defined in the manifest (which could
    # be a regular package with a meaningful version). This is not recommended, but can be useful for special builds.
    parser.add_argument(
        "--keep-root-spec-intact",
        action="store_true",
        help="If set, the root spec will not be modified to remove git version information.",
    )

    parser.add_argument(
        "--spack-packages-path",
        type=str,
        required=False,
        help="Local path to a spack-packages repository that is added to the manifests repos section",
    )

    # Args dealing with outputs
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        help="Path to the output file where the modified manifest will be saved",
    )

    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    injected_manifest: str = inject_prerelease_information(
        args.manifest,
        args.version,
        args.custom_root_projection,
        args.keep_root_spec_intact,
        args.spack_packages_path,
    )

    print(injected_manifest)

    if args.output:
        with open(args.output, "w") as output_file:
            output_file.write(injected_manifest)


if __name__ == "__main__":
    main()
