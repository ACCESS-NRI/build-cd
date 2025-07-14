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

def _get_includes(manifest: dict[str, Any]) -> set[str]:
    # Interrogating manifests of the form:
    # spack:
    #   modules:
    #     default:
    #       tcl:
    #         includes:
    #           - ROOT_PACKAGE
    #           - PACKAGE1
    #           - ...
    includes: list[str] = (
        manifest.get("spack", {})
        .get("modules", {})
        .get("default", {})
        .get("tcl", {})
        .get("includes", [])
    )

    return set(includes)

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

def inject_projections(
    manifest: str, root_spec: str, packages: set[str]
) -> dict[str, Any]:

    # Get projections that are already defined in the manifest - we don't want to redefine these
    defined_projections: dict[str, str] = _get_defined_projections(manifest)
    defined_projections_set: set[str] = set(defined_projections.keys())
    # Get packages that have versions defined in the manifest - we can only generate projections for things with an explicit version
    packages_with_versions_defined: set[str] = _get_packages_with_versions_defined(
        manifest
    )

    # Essentially...we want to generate projections for all packages that don't already have them, provided they have a version defined
    projections_to_generate: set[str] = (packages & packages_with_versions_defined) - defined_projections_set

    # To start with, add the projections that are already defined in the manifest
    new_projections: dict[str, str] = dict(defined_projections)

    if root_spec not in defined_projections_set:
        new_projections.update(generate_projection_for_root_spec_or_raise(manifest, root_spec))

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

def generate_projection_for_root_spec_or_raise(
    manifest: dict[str, Any], root_spec_name: str
) -> dict[str, str]:
    root_spec_definition: str | None = None

    # First check if the spec is defined in the multi-target format
    for spec_definition in manifest.get("spack", {}).get("definitions", []):
        if "ROOT_PACKAGE" in spec_definition and len(spec_definition["ROOT_PACKAGE"]) > 0:
            root_spec_definition = spec_definition["ROOT_PACKAGE"][0]
            break

    # Then check if the spec if defined in the traditional, single-target format
    if not root_spec_definition and len(manifest.get("spack", {}).get("specs", [])) > 0:
        root_spec_definition = manifest.get("spack", {}).get("specs", [])[0]

    # If it isn't in either of those places, we don't know where it is
    if not root_spec_definition:
        raise ValueError(
            f"Could not find root spec definition for root spec {root_spec_name} in the manifest. The spack.yaml is invalid"
        )

    # Now we can extract the actual version from the root spec definition
    version_regex = re.compile(r"([^@]+)@(?:git.)?([^+~= ]+).*")
    match = re.match(version_regex, root_spec_definition)

    if not match:
        raise ValueError(
            f"Could not extract name or version from root spec definition {root_spec_definition} for projection {root_spec_name}. The root spec needs a name and version defined properly."
        )

    root_spec_name_from_definition, version = match.group(1, 2)

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
    if len(manifest.get("spack", {}).get("packages", {}).get(package_name, {}).get("require", [])) == 0:
        raise ValueError(
            f"Package '{package_name}' does not have a version defined in the manifests 'spack.packages.{package_name}.require[0]' section. Projections can only be generated for packages with an explicit version."
        )

    full_package_version: str = manifest["spack"]["packages"][package_name]["require"][0]

    version_regex = re.compile(r"@(?:git.)?([^+~= ]+).*")

    match = re.match(version_regex, full_package_version)
    if match:
        version = match.group(1)
    else:
        print(f"Could not extract version from package {full_package_version}. ")
        return

    print(
        f"Extracted version '{version}' from package '{package_name}' using '{full_package_version}'"
    )

    # Projections for packages need to be delimited by hash
    return {package_name: f"{{name}}/{version}-{{hash:7}}"}

def inject_includes(
    manifest: dict[str, Any], root_spec: str, packages: set[str]
) -> dict[str, Any]:
    # We want to inject the includes for the root spec, all packages defined in --packages, and existing includes in the manifest.
    existing_includes: set[str] = _get_includes(manifest)

    # Includes are the union of packages, and existing includes - we add the root spec later
    includes: set[str] = packages | existing_includes

    # To sort, we want to ensure that the root spec is always first in the list, and the rest are sorted alphabetically
    sorted_include: list[str] = [root_spec] + sorted(includes)

    # Finally, we inject the includes into and updated manifest, which we return
    injected_manifest: dict[str, Any] = dict(manifest)
    injected_manifest.setdefault("spack", {}).setdefault("modules", {}).setdefault("default", {}).setdefault("tcl", {})["includes"] = sorted_include

    return injected_manifest

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

    parsed_args = parser.parse_args(args)

    # Verifying that --packages are space-separated, which is a bit different from the usual comma-separated lists
    if ',' in parsed_args.packages:
        raise ValueError(
            "The --packages argument must be a space-separated list of package names."
        )

    return parsed_args

def main():
    # Get inputs
    args = parse_args(sys.argv[1:])

    packages: set[str] = set(args.packages.split())

    with open(args.manifest, "r") as file:
        manifest: dict[str, Any] = yaml.safe_load(file)

    # Inject manifeest with projections and includes
    manifest_with_projections: dict[str, Any] = inject_projections(
        manifest=manifest, root_spec=args.root_spec, packages=packages
    )

    manifest_with_projections_and_includes: dict[str, Any] = inject_includes(manifest=manifest_with_projections, root_spec=args.root_spec, packages=packages)

    # Output the modified manifest
    print(
        yaml.dump(
            manifest_with_projections_and_includes,
            default_flow_style=False,
            sort_keys=False,
        )
    )

    if args.output:
        with open(args.output, "w") as output_file:
            yaml.dump(
                manifest_with_projections_and_includes,
                output_file,
                default_flow_style=False,
                sort_keys=False,
            )


if __name__ == "__main__":
    main()
