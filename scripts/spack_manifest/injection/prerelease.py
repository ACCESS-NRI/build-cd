import argparse
import yaml
import re
import sys

from typing import Any
from copy import deepcopy

from scripts.spack_manifest.getter import (
    ReservedDefinitions,
    Projections,
    Specs
)
from scripts.spack_manifest.injection.yaml_representer import (
    YamlExplicitFlowStyleSequence,
    YamlExplicitQuotedString,
    yaml_explicit_flow_style_sequence_representer,
    yaml_explicit_quoted_string_representer,
    enforce_explicit_flow_style_definitions
)


# The yaml representer sometimes dumps ambiguous strings in the case of projections like `{name}/...` as unquoted strings,
# which is not handled by spack very well.
yaml.add_representer(YamlExplicitQuotedString, yaml_explicit_quoted_string_representer)

# We represent reserved definitions as in flow-style sequences (eg. `[a]` rather than `- a`), so it is more compact.
yaml.add_representer(YamlExplicitFlowStyleSequence, yaml_explicit_flow_style_sequence_representer)

### Actual methods begin here ###

def inject_prerelease_information(
    manifest_path: str,
    version: str
) -> str:
    # In comparison to the projections script, this returns a string rather than a dict because we need to
    # add spack-specific, non-standard 'repo::' sections, which the yaml dumper does not support.
    with open(manifest_path, "r") as manifest_file:
        manifest: dict[str, Any] = yaml.safe_load(manifest_file)

    reserved_definitions_from_manifest = ReservedDefinitions(manifest)
    root_spec_name: str = reserved_definitions_from_manifest.get("name")

    updated_manifest: dict[str, Any] = deepcopy(manifest)

    # We want the root spec projection to be of the form {name}/prX-Y for single specs, and
    # {name}/prX-Y/DEMARCATOR for multiple specs, so we don't have modulefile clashes.
    # The DEMARCATOR can be a custom projection, or {hash:7} if not supplied.
    updated_manifest = update_root_spec_projections_version(
        updated_manifest, root_spec_name, version
    )

    # We want all other projections to be of the form {name}/prX-Y/VERSION
    updated_manifest = add_namespace_to_other_projection_versions(
        updated_manifest, root_spec_name, version
    )

    updated_manifest = enforce_explicit_flow_style_definitions(updated_manifest)

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


    projections_getter = Projections(mutable_manifest)
    projections: dict[str, str] = projections_getter.get()
    root_spec_like_projections: dict[str, str] = projections_getter.get_partial_specs_of(root_spec_name)

    # We only want to modify projections that are not root-spec-like, since they already have their version set
    for projection_name, projection_value in projections.items():
        if projection_name in root_spec_like_projections:
            continue
        # Non-root-spec projections are namespaced under ROOT_SPEC_NAME/dependencies/prX-Y,
        # while preserving the original projection structure (with or without a {name} token).
        new_projection_value = f"{root_spec_name}/dependencies/{version}/{projection_value.lstrip('/')}"

        print(
            f"Updating projection '{projection_name}' from '{projection_value}' to '{new_projection_value}'"
        )

        # Ensures that the new projection is a quoted string when dumped so spack does projected modules correctly, see top of file.
        mutable_manifest["spack"]["modules"]["default"]["tcl"]["projections"][projection_name] = YamlExplicitQuotedString(new_projection_value)

    return mutable_manifest


def update_root_spec_projections_version(
    manifest: dict[str, Any], root_spec_name: str, deployment_version: str
) -> dict[str, Any]:
    manifest.setdefault("spack", {}).setdefault("modules", {}).setdefault("default", {}).setdefault("tcl", {}).setdefault("projections", {})

    projections_like_root_spec: dict[str, str] | None = Projections(manifest).get_partial_specs_of(root_spec_name)
    number_of_root_specs_in_speclist = len(Specs(manifest).get_specs_with_name(root_spec_name))

    if projections_like_root_spec:
        # Replace the manifest version wherever it appears as a path segment in the projection.
        current_version = ReservedDefinitions(manifest).get("version")
        for root_spec_partial, current_root_projection in projections_like_root_spec.items():
            new_root_projection = current_root_projection.replace(current_version, deployment_version)

            if number_of_root_specs_in_speclist > 1 and re.match(fr"^.+/{deployment_version}$", new_root_projection):
                # If there are multiple of the same root spec, we need to demarcate them somehow if there was no custom suffix given.
                # We use a short package hash as the demarcator if no custom suffix was given.
                new_root_projection += "/{hash:7}"

            manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_partial] = new_root_projection
    else:
        if number_of_root_specs_in_speclist == 1:
            new_root_projection = f'{{name}}/{deployment_version}'
        else:
            new_root_projection = f'{{name}}/{deployment_version}/{{hash:7}}'

        manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_name] = new_root_projection

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
        args.version
    )

    print(injected_manifest)

    if args.output:
        with open(args.output, "w") as output_file:
            output_file.write(injected_manifest)


if __name__ == "__main__":
    main()
