import argparse
import yaml
import re
import sys

from typing import Any


def _get_defined_projections(manifest: dict[str, Any]) -> dict[str, str]:
    # These are the projections that are already defined in the manifest
    projections: dict[str, Any] = (
        manifest.get("spack", {})
        .get("modules", {})
        .get("default", {})
        .get("tcl", {})
        .get("projections", {})
    )

    return projections


def _get_packages_with_versions_defined(manifest: dict[str, Any]) -> set[str]:
    # Interrogating manifests of the form:
    # spack:
    #   packages:
    #     package1:
    #       require:
    #         - "@git.1.0.0"
    packages: dict[str, Any] = manifest.get("spack", {}).get("packages", {})
    packages_with_versions_defined: set[str] = set()

    for package_name, package_spec in packages.items():
        if package_spec["require"][0].startswith("@"):
            packages_with_versions_defined.add(package_name)

    return packages_with_versions_defined


def generate_projections(
    manifest: dict[str, Any],
    root_spec_name: str,
    existing_projections: dict[str, str],
    projections_to_generate: set[str],
) -> dict[str, str]:
    projections: dict[str, str] = existing_projections

    for projection in projections_to_generate:
        if projection == root_spec_name:
            projection_version: str = _generate_projection_version_from_spec_or_raise(
                manifest, projection
            )
            if projection_version:
                # We don't add a hash to the root spec projection, as it is a unique deployment
                projections[projection] = f"{{name}}/{projection_version}"
        else:
            projection_version: str = _generate_projection_version_from_package(
                manifest, projection
            )
            if projection_version:
                # This is not the case for the other projections, so we add the spack hash to them
                projections[projection] = f"{{name}}/{projection_version}-{{hash:7}}"

    # Sort the projections by name to ensure a consistent order
    ordered_projections = dict(sorted(projections.items()))

    # But, we want to ensure that the root spec projection is always first in the list because it's special
    if projections[root_spec_name] is not None:
        root_spec_version = ordered_projections.pop(root_spec_name)
        ordered_projections = {root_spec_name: root_spec_version, **ordered_projections}

    return ordered_projections


def _generate_projection_version_from_package(
    manifest: dict[str, Any], projection: str
) -> str:
    # We require the package to have a version defined first in the spack.packages.PACKAGE section.
    full_package_version: str = manifest["spack"]["packages"][projection]["require"][0]

    version_regex = re.compile(r"@(?:git.)?([^+~= ]+).*")

    match = re.match(version_regex, full_package_version)
    if match:
        version = match.group(1)
    else:
        print(f"Could not extract version from package {full_package_version}. ")
        return

    print(
        f"Extracted version {version} from package {projection}{full_package_version}"
    )

    return version


def _generate_projection_version_from_spec_or_raise(
    manifest: dict[str, Any], projection: str
) -> str:
    root_spec_definition: str | None = None

    # First check if the spec is defined in the multi-target format
    for spec_definition in manifest.get("spack", {}).get("definitions", []):
        if "ROOT_PACKAGE" in spec_definition:
            root_spec_definition = spec_definition["ROOT_PACKAGE"][0]
            break

    # Then check if the spec if defined in the traditional, single-target format
    if not root_spec_definition:
        root_spec_definition = manifest.get("spack", {}).get("specs", [])[0]

    # If it isn't in either of those places, we don't know where it is
    if not root_spec_definition:
        raise ValueError(
            f"Could not find root spec definition for projection {projection} in the manifest. The spack.yaml is invalid"
        )

    # Now we can extract the version from the root spec definition
    version_regex = re.compile(rf"{projection}@(?:git.)?([^+~= ]+).*")
    match = re.match(version_regex, root_spec_definition)

    if not match:
        raise ValueError(
            f"Could not extract version from root spec definition {root_spec_definition} for projection {projection}. The root spec needs a version defined."
        )

    version = match.group(1)

    print(
        f"Extracted version {version} from root spec definition {root_spec_definition}"
    )

    return version


def inject_projections(
    manifest_path: str, root_spec: str, packages: set[str]
) -> dict[str, Any]:

    with open(manifest_path, "r") as file:
        manifest: dict[str, Any] = yaml.safe_load(file)

    # We should try and inject projections for the root spec as well, so we create a set with just it
    root_spec_set: set[str] = {root_spec}

    # Get projections that are already defined in the manifest - we don't want to redefine these
    defined_projections: dict[str, str] = _get_defined_projections(manifest)
    defined_projections_set: set[str] = set(defined_projections.keys())
    # Get packages that have versions defined in the manifest - we can only generate projections for things with an explicit version
    packages_with_versions_defined: set[str] = _get_packages_with_versions_defined(
        manifest
    )

    # Essentially...we want to generate projections for all packages that don't already have them, provided they have a version defined, or they are the root spec.
    projections_to_generate: set[str] = (
        root_spec_set | (packages & packages_with_versions_defined)
    ) - defined_projections_set

    # Generate the new projections based on the manifest content
    new_projections: dict[str, str] = generate_projections(
        manifest, root_spec, defined_projections, projections_to_generate
    )

    # Inject the new projections into the manifest content, and sort them
    injected_manifest: dict[str, Any] = manifest
    injected_manifest["spack"]["modules"]["default"]["tcl"][
        "projections"
    ] = new_projections

    return injected_manifest


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script for injecting projection information into spack manifest files."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Path to the spack manifest file to be injected with projection information",
    )

    parser.add_argument(
        "--root-spec",
        type=str,
        required=True,
        help="Name of the root spec of the deployment",
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

    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    packages: set[str] = set(args.packages.split())

    injected_manifest: dict[str, Any] = inject_projections(
        manifest_path=args.manifest, root_spec=args.root_spec, packages=packages
    )

    print(
        yaml.dump(
            injected_manifest,
            default_flow_style=False,
            sort_keys=False,
        )
    )

    if args.output:
        with open(args.output, "w") as output_file:
            yaml.dump(
                injected_manifest,
                output_file,
                default_flow_style=False,
                sort_keys=False,
            )


if __name__ == "__main__":
    main()
