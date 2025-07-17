from typing import Any
import re
# from yaml import safe_load is loaded in the class methods from_file as that is the only place it is used

class NoSectionError(Exception):
    """Exception raised when the root spec is not found in the manifest."""
    pass

class NoSectionComponentError(Exception):
    """Exception raised when a specific component of the root spec is not found."""
    pass

class RootSpec:
    def __init__(self, manifest: dict[str, Any]):
        self.manifest = manifest

        self.root_spec: str = self._get_root_spec_from_manifest_or_raise()

    def _get_root_spec_from_manifest_or_raise(self) -> str:
        defs: list[dict[str, Any]] = self.manifest.get("spack", {}).get("definitions", [])
        specs: list[str] = self.manifest.get("spack", {}).get("specs", [])

        # It's either in the multi-target format or the single target format, we just need to find which
            # The multi-target format is of the form:
        # spack:
        #   definitions:
        #     - ROOT_PACKAGE: [access-om2@git.2025.05]
        #     # ...
        root_package_def = next((d["ROOT_PACKAGE"] for d in defs if "ROOT_PACKAGE" in d), [])
        if root_package_def != []:
            return root_package_def[0]
        elif len(specs) != 0:
            return specs[0]
        else:
            raise NoSectionError("No root spec defined in the manifest spack.specs section for a single-target manifest.")

    @classmethod
    def from_file(cls, manifest_path: str) -> 'RootSpec':
        from yaml import safe_load

        with open(manifest_path, "r") as file:
            manifest = safe_load(file)

        return cls(manifest)

    ## Get full root spec

    def get(self) -> str:
        # Extract the root spec name from the manifest
        return self.root_spec

    ## Get root spec name

    def get_name(self) -> str:
        match = re.match(r"[^@]+", self.root_spec)

        if match is None:
            raise NoSectionComponentError("Root spec component 'name' could not be extracted from the root spec string.")

        return match.group(0)

    ## Get version-related information

    # def get_full_version(self) -> str:
    #     pass

    def get_ref(self) -> str:
        match = re.match(r"[^@]+@(?:git.)?([^+~= ]+)", self.root_spec)

        if match is None:
            raise NoSectionComponentError("Root spec component 'ref' could not be extracted from the root spec string.")

        return match.group(1)

    # def get_spack_version(self) -> str:
    #     pass

    ## Get variant information

    # def get_variants(self) -> list[str]:
    #     pass

    ## Get compiler information

    # def get_compiler(self) -> str:
    #     pass

    # def get_compiler_name(self) -> str:
    #     pass

    # def get_compiler_version(self) -> str:
    #     pass

    ## Get architecture information

    # def get_arch(self) -> str:
    #     pass

    ## Other functions

    def get_non_version_constraints(self) -> str:
        """
        Get all non-version constraints from the root spec.
        This is everything after the @ref, including variants, compiler info and arch.
        """
        match = re.match(r"[^@]+@[^+~% ]+(.*)", self.root_spec)

        if match is None:
            return ""

        return match.group(1).strip()

    def has_git_ref(self) -> bool:
        """Check if the root spec has a git ref."""
        return "@git." in self.root_spec

####################################################

class Packages:
    def __init__(self, manifest: dict[str, Any]):
        self.manifest: dict[str, Any] = manifest

        self.packages: list[str] = self._get_packages_from_manifest_or_raise()

    def _get_packages_from_manifest_or_raise(self) -> dict[str, Any]:
        packages = self.manifest.get("spack", {}).get("packages", {})

        if "packages" not in self.manifest.get("spack", {}):
            raise NoSectionError(f"spack.packages section not found in the manifest.")

        return self.manifest.get("spack", {}).get("packages", {})

    # Can also pass in a path to a yaml manifest instead of a python object
    @classmethod
    def from_file(cls, manifest_path: str) -> 'Packages':
        from yaml import safe_load

        with open(manifest_path, "r") as file:
            manifest = safe_load(file)

        return cls(manifest)

    ## Get package information

    def get_all(self) -> dict[str, Any]:
        return self.packages

    def get_all_package_names_with_ref_requirement(self) -> list[str]:
        packages_with_versions_defined: list[str] = []

        for package_name, package_spec in self.packages.items():
            if len(package_spec.get("require", {})) != 0 and package_spec["require"][0].startswith("@"):
                packages_with_versions_defined.append(package_name)

        return packages_with_versions_defined

    def get_package_full_version_requirement(self, name: str) -> str:
        if name not in self.packages:
            raise NoSectionError(f"Package '{name}' not found in the manifest spack.packages section.")

        requirements = self.packages[name].get("require", [])

        if len(requirements) == 0:
            raise NoSectionComponentError(f"Package component 'full version' could not be extracted from the package requirements string for '{name}'.")

        return requirements[0]


    def get_package_requirements(self, name: str) -> list[str]:
        if name not in self.packages:
            raise NoSectionComponentError(f"Package '{name}' not found in the manifest spack.packages section.")

        return self.packages[name].get("require", [])

    def get_package_ref_requirement(self, name: str) -> str:
        requirements = self.get_package_requirements(name)

        if requirements == []:
            raise NoSectionComponentError(f"Package component 'version' could not be extracted from the package requirements string for '{name}'.")

        match = re.match(r"@(?:git\.)?([^+~=% ]+)", requirements[0])

        if match is None:
            raise NoSectionComponentError(f"Package component 'version' was not formatted correctly in the package requirements for '{name}'.")

        return match.group(1)

########################################3

class Includes:
    def __init__(self, manifest: dict[str, Any]):
        self.manifest: dict[str, Any] = manifest

    # Can also pass in a path to a yaml manifest instead of a python object
    @classmethod
    def from_file(cls, manifest_path: str) -> 'Includes':
        from yaml import safe_load

        with open(manifest_path, "r") as file:
            manifest = safe_load(file)

        return cls(manifest)

    def get(self) -> list[str]:
        return self.manifest.get("spack", {}).get("modules", {}).get("default", {}).get("tcl", {}).get("include", [])

class Projections:
    def __init__(self, manifest: dict[str, Any]):
        self.manifest: dict[str, Any] = manifest

    # Can also pass in a path to a yaml manifest instead of a python object
    @classmethod
    def from_file(cls, manifest_path: str) -> 'Projections':
        from yaml import safe_load

        with open(manifest_path, "r") as file:
            manifest = safe_load(file)

        return cls(manifest)


    def get(self) -> dict[str, str]:
        return self.manifest.get("spack", {}).get("modules", {}).get("default", {}).get("tcl", {}).get("projections", {})
