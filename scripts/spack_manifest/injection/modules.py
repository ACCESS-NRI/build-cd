import argparse
import yaml
import sys
import re

from typing import Any
from scripts.spack_manifest.getter import (
    ReservedDefinitions,
    Packages,
    Includes,
    Projections,
    Specs
)
from scripts.spack_manifest.injection.yaml_representer import (
    YamlExplicitFlowStyleSequence,
    yaml_explicit_flow_style_sequence_representer,
    enforce_explicit_flow_style_definitions
)

# We represent reserved definitions as in flow-style sequences (eg. `[a]` rather than `- a`), so it is more compact.
yaml.add_representer(YamlExplicitFlowStyleSequence, yaml_explicit_flow_style_sequence_representer)

##################
# Main functions #
##################


def main():
    # Get inputs
    args = parse_args(sys.argv[1:])

    packages: set[str] = set(args.packages.split(",") if args.packages != '' else [])

    with open(args.manifest, "r") as file:
        manifest: dict[str, Any] = yaml.safe_load(file)

    # Inject manifest with projections and includes

    deployment_name: str = ReservedDefinitions(manifest).get("name")

    manifest_with_projections: dict[str, Any] = inject_projections(
        manifest=manifest, root_spec=deployment_name, packages=packages
    )

    manifest_with_projections_and_includes: dict[str, Any] = inject_includes(
        manifest=manifest_with_projections, root_spec=deployment_name, packages=packages
    )

    finalized_manifest: dict[str, Any] = enforce_explicit_flow_style_definitions(
        manifest_with_projections_and_includes
    )

    # Output the modified manifest
    dumped_manifest: str = yaml.dump(
        finalized_manifest,
        default_flow_style=False,
        sort_keys=False,
    )

    print(dumped_manifest)

    if args.output:
        with open(args.output, "w") as output_file:
            output_file.write(dumped_manifest)

def inject_projections(
    manifest: str, root_spec: str, packages: set[str]
) -> dict[str, Any]:

    # Get projections that are already defined in the manifest - we don't want to redefine these
    projections_getter = Projections(manifest)
    defined_projections_dict: dict[str, str] = projections_getter.get()
    defined_projections: set[str] = set(defined_projections_dict.keys())

    # Get packages that have versions defined in the manifest - we can only generate projections for things with an explicit version
    packages_getter = Packages(manifest)
    packages_with_versions_defined: set[str] = set(
        packages_getter.get_all_package_names_with_ref_requirement()
    )

    # Generate projections for all packages that don't already have them, provided they have a version defined
    projections_to_generate: set[str] = (
        packages & packages_with_versions_defined
    ) - defined_projections

    # To start with, add the projections that are already defined in the manifest
    new_projections: dict[str, str] = dict(defined_projections_dict)

    new_projections.update(
        generate_projection_for_root_spec_or_raise(manifest, root_spec, defined_projections_dict.get(root_spec, ''))
    )

    for projection in projections_to_generate:
        new_projections.update(
            generate_projection_for_package_or_raise(manifest, projection)
        )

    # Sort the projections by name to ensure a consistent order...
    ordered_new_projections = dict(sorted(new_projections.items()))

    # But, we want to ensure that the root spec projection is always first in the list because it's special
    root_spec_version = ordered_new_projections.pop(root_spec)
    ordered_new_projections = {root_spec: root_spec_version, **ordered_new_projections}

    # Finally, add the new projections to the manifest
    injected_manifest: dict[str, Any] = dict(manifest)
    injected_manifest.setdefault("spack", {}).setdefault("modules", {}).setdefault("default", {}).setdefault("tcl", {})["projections"] = ordered_new_projections

    return injected_manifest


def inject_includes(
    manifest: dict[str, Any], root_spec: str, packages: set[str]
) -> dict[str, Any]:
    # We want to inject the includes for the root spec, all packages defined in --packages, and existing includes in the manifest.
    includes_getter = Includes(manifest)
    existing_includes: set[str] = set(includes_getter.get())

    # Includes are the union of the root spec, packages, and existing includes
    includes: set[str] = {root_spec} | packages | existing_includes

    # To sort, we want to ensure that the root spec is always first in the list, and the rest (minus that root spec) are sorted alphabetically
    sorted_includes: list[str] = [root_spec] + sorted(includes - {root_spec})

    # Finally, inject the includes into a new copy of the manifest, which is returned
    injected_manifest: dict[str, Any] = dict(manifest)
    injected_manifest.setdefault("spack", {}).setdefault("modules", {}).setdefault("default", {}).setdefault("tcl", {})["include"] = sorted_includes

    return injected_manifest


#######################################################
# Lower-level functions to generate manifest sections #
#######################################################


def generate_projection_for_root_spec_or_raise(
    manifest: dict[str, Any],
    root_spec_name: str,
    root_spec_projection: str = ''
) -> dict[str, str]:
    reserved_definitions_getter = ReservedDefinitions(manifest)
    specs_getter = Specs(manifest)

    version = reserved_definitions_getter.get("version")

    print(
        f"Extracted version '{version}' from _version definition'"
    )

    # Essentially we're looking to infix the version between {name} and what comes after, if there exists a projection.
    module_projection_pattern = re.compile(
        r"""
        ^(.*\{name\}[^\/]*?)  # First group - Either '{name}' (most common) or a prefix like 'system-tools/{name}' (for SDRs)
        (?:\/(.+))?$          # Optional second group - Rest of the projection after '{name}/', if given. Used for variants/descriptors in modulefile names
        """,
        re.VERBOSE
    )

    projection_components: re.Match | None = re.match(module_projection_pattern, root_spec_projection)

    # If there is a root spec projection and it is well-formed, we need to infix the version
    if projection_components:
        # We have a custom projection defined for the root spec, so we need to respect that
        projection_groups: tuple[str] = projection_components.groups()

        updated_version: str = f"{projection_groups[0]}/{version}" + (f"/{projection_groups[1]}" if projection_groups[1] else "")

        print(f"Root spec already had a projection ({root_spec_projection}) so we infix the the version ({version}) to give: {updated_version}")

        return {root_spec_name: updated_version}

    # Otherwise, we need to construct a projection from scratch
    root_specs_in_speclist = len(specs_getter.get_specs_with_name(root_spec_name))

    if root_specs_in_speclist == 0:
        raise ValueError(f"No specs with name {root_spec_name} in speclist")
    elif root_specs_in_speclist == 1:
        return {root_spec_name: f"{{name}}/{version}"}
    else:
        # If there are multiple of the same root spec (for example, different variants housed under the same environment), we need to demarcate the modulefile with a spack package hash
        return {root_spec_name: f"{{name}}/{version}/{{hash:7}}"}


def generate_projection_for_package_or_raise(
    manifest: dict[str, Any], package_name: str
) -> dict[str, str]:
    # We require the package to have a version defined first in the spack.packages.PACKAGE section.

    packages_getter = Packages(manifest)

    full_package_version: str = packages_getter.get_package_full_version_requirement(
        package_name
    )
    version: str = packages_getter.get_package_ref_requirement(package_name)

    print(
        f"Extracted version '{version}' from package '{package_name}' using '{full_package_version}'"
    )

    # Projections for packages need to be delimited by hash
    return {package_name: f"{{name}}/{version}-{{hash:7}}"}


#########################################
# Invoked module parsing and validation #
#########################################


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script for injecting module information into spack manifest files."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Path to the spack manifest file to be injected with projection information",
    )

    parser.add_argument(
        "--packages",
        type=str,
        required=True,
        help="List of comma-separated packages (excluding the root spec) to be considered for projection injection",
    )

    parser.add_argument(
        "--output",
        type=str,
        required=False,
        help="Path to the output file where the modified manifest will be saved",
    )

    parsed_args = parser.parse_args(args)

    return parsed_args


if __name__ == "__main__":
    main()
