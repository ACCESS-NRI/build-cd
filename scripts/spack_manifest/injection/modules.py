import argparse
import yaml
import sys

from typing import Any
from scripts.spack_manifest.getter import (
    RootSpec,
    Packages,
    Includes,
    Projections,
)

##################
# Main functions #
##################


def main():
    # Get inputs
    args = parse_args(sys.argv[1:])

    packages: set[str] = set(args.packages.split())

    with open(args.manifest, "r") as file:
        manifest: dict[str, Any] = yaml.safe_load(file)

    # Inject manifest with projections and includes
    root_spec_name: str = RootSpec(manifest).get_name()

    manifest_with_projections: dict[str, Any] = inject_projections(
        manifest=manifest, root_spec=root_spec_name, packages=packages
    )

    manifest_with_projections_and_includes: dict[str, Any] = inject_includes(
        manifest=manifest_with_projections, root_spec=root_spec_name, packages=packages
    )

    # Output the modified manifest
    dumped_manifest: str = yaml.dump(
        manifest_with_projections_and_includes,
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

    if root_spec not in defined_projections:
        new_projections.update(
            generate_projection_for_root_spec_or_raise(manifest, root_spec)
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
    manifest: dict[str, Any], root_spec_name: str
) -> dict[str, str]:
    root_spec_definition: str | None = None

    root_spec_getter = RootSpec(manifest)

    root_spec_name_from_definition: str = root_spec_getter.get_name()
    version = root_spec_getter.get_ref()

    if root_spec_name_from_definition != root_spec_name:
        raise ValueError(
            f"Expected root spec name '{root_spec_name}' does not match the name in the root spec definition '{root_spec_name_from_definition}'. The --root-spec needs to be defined the same as the actual root spec."
        )

    print(
        f"Extracted version '{version}' from root spec definition '{root_spec_definition}'"
    )

    # We don't add a hash to the root spec projection, as it is a unique deployment
    return {root_spec_name: f"{{name}}/{version}"}


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
        help="List of space-separated packages (excluding the root spec) to be considered for projection injection",
    )

    parser.add_argument(
        "--output",
        type=str,
        required=False,
        help="Path to the output file where the modified manifest will be saved",
    )

    parsed_args = parser.parse_args(args)

    # Verifying that --packages are space-separated, which is a bit different from the usual comma-separated lists
    if "," in parsed_args.packages:
        raise ValueError(
            "The --packages argument must be a space-separated list of package names."
        )

    return parsed_args


if __name__ == "__main__":
    main()
