import pytest
import yaml

from scripts.spack_manifest.getter import (
    ReservedDefinitions,
    RootSpec,
    Packages,
    Includes,
    Projections,
    Specs,
    NoSectionError,
    NoSectionComponentError,
)

### Global Fixtures ###


@pytest.fixture
def manifest_from_file():
    return {
        "spack": {
            "specs": ["access-om2@git.1.0.0"],
            "packages": {
                "package1": {"require": ["@git.1.0.0"]},
                "package2": {"require": ["@git.2.0.0"]},
            },
            "modules": {
                "default": {
                    "tcl": {
                        "include": ["root-spec", "package2", "package3"],
                        "projections": {
                            "package1": "package1/1.0.0",
                            "package2": "package2/2.0.0",
                        },
                    }
                }
            },
        }
    }

class TestReservedDefinitionsGetter:
    @pytest.fixture
    def manifest_with_reserved_definitions(self):
        return {
            "spack": {
                "definitions": [
                    {"_name": ["access-om2"]},
                    {"_version": ["2025.11.000"]},
                    {"OTHER_DEFINITION": ["some-value"]},
                ]
            }
        }
    def test___init___valid(self, manifest_with_reserved_definitions):

        reserved_definitions_getter = ReservedDefinitions(manifest_with_reserved_definitions)

        expected = {
            "name": "access-om2",
            "version": "2025.11.000",
        }

        assert (
            reserved_definitions_getter.reserved_definitions == expected
        ), "Reserved definitions should be correctly initialized from manifest."

    def test___init___invalid_no_definitions_section(self):
        manifest = {"spack": {}}

        with pytest.raises(NoSectionError):
            ReservedDefinitions(manifest)

    def test_get__valid(self, manifest_with_reserved_definitions):

        reserved_definitions_getter = ReservedDefinitions(manifest_with_reserved_definitions)
        definition_value = reserved_definitions_getter.get("name")

        expected = "access-om2"

        assert (
            definition_value == expected
        ), "Reserved definitions should be correctly retrieved."

    def test_get__invalid_no_definition(self, manifest_with_reserved_definitions):

        reserved_definitions_getter = ReservedDefinitions(manifest_with_reserved_definitions)

        with pytest.raises(NoSectionComponentError):
            reserved_definitions_getter.get("nonexistent_definition")

    def test_get_list__missing_definition_with_default(self, manifest_with_reserved_definitions):
        reserved_definitions_getter = ReservedDefinitions(manifest_with_reserved_definitions)

        assert reserved_definitions_getter.get_list("custom-scopes", default=[]) == []


class TestRootSpecGetter:
    def test___init___valid_multi_target_spec(self):
        # This is a pared-down example due to json being annoying to represent without many lines of code.
        # In practice, the multi-target spec looks something like:
        # spack:
        #   definitions:
        #     - ROOT_PACKAGE: [access-om2@git.2025.05]
        #     - ROOT_SPEC:
        #         - matrix:
        #             - [$ROOT_PACKAGE]
        #             - ['%intel@2021.2.0', '%intel@2021.10.0']
        #   spec:
        #     - $ROOT_SPEC
        manifest = {
            "spack": {"definitions": [{"ROOT_PACKAGE": ["access-om2@git.1.0.0"]}]}
        }

        root_spec_getter = RootSpec(manifest)

        assert (
            root_spec_getter.root_spec == "access-om2@git.1.0.0"
        ), "Root spec should be correctly initialized from multi-target manifest."

    def test___init___valid_single_target_spec(self):
        manifest = {"spack": {"specs": ["access-om2@git.1.0.0"]}}

        root_spec_getter = RootSpec(manifest)

        assert (
            root_spec_getter.root_spec == "access-om2@git.1.0.0"
        ), "Root spec should be correctly initialized from single-target manifest."

    def test___init___invalid_no_root_spec(self):
        manifest = {"spack": {"specs": []}}

        with pytest.raises(NoSectionError):
            RootSpec(manifest)

    def test___init___invalid_no_manifest(self):
        with pytest.raises(NoSectionError):
            RootSpec({})

    def test_from_file__valid(self, manifest_from_file, tmp_path):
        manifest_path = tmp_path / "manifest.yaml"
        with open(manifest_path, "w") as file:
            yaml.dump(manifest_from_file, file)

        root_spec_getter = RootSpec.from_file(tmp_path / "manifest.yaml")

        assert (
            root_spec_getter.root_spec == "access-om2@git.1.0.0"
        ), "Root spec should be correctly retrieved from file."

    def test_from_file__invalid(self):
        manifest_path = (
            "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"
        )

        with pytest.raises(OSError):
            RootSpec.from_file(manifest_path)

    @pytest.mark.parametrize(
        "spec, expected_name",
        [
            ("access-om2@git.1.0.0", "access-om2"),
            ("access-esm1p6@git.2025.05+debug", "access-esm1p6"),
            ("access-om2@1.0.0 %intel@2021.2.0 +debug", "access-om2"),
        ],
    )
    def test_get_name__valid(self, spec, expected_name):
        manifest = {"spack": {"specs": [spec]}}

        assert (
            RootSpec(manifest).get_name() == expected_name
        ), "Root spec name should be correctly extracted."

    @pytest.mark.parametrize(
        "spec",
        [
            "@git.1.0.0",
            "%compiler@2.0.0",
            "+debug",
        ],
    )
    def test_get_name__invalid(self, spec):
        manifest = {"spack": {"specs": [spec]}}

        with pytest.raises(NoSectionComponentError):
            RootSpec(manifest).get_name()

    @pytest.mark.parametrize(
        "spec, expected_ref",
        [
            ("access-om2@git.1.0.0", "1.0.0"),
            ("access-om2@git.1.0.0 %compiler@2.0.0", "1.0.0"),
            ("access-om2@git.1.0.0 %compiler@2.0.0 +debug", "1.0.0"),
            ("access-om2@git.1.0.0=develop %compiler@2.0.0 +debug", "1.0.0"),
            ("access-om2@git.1.0.0=latest %compiler@2.0.0 +debug", "1.0.0"),
            ("access-esm1p5@git.develop=access-esm1p5 +debug", "develop"),
            ("access-esm1p5@git.2025.05+debug", "2025.05"),
        ],
    )
    def test_get_ref__valid(self, spec, expected_ref):
        manifest = {"spack": {"specs": [spec]}}

        assert (
            RootSpec(manifest).get_ref() == expected_ref
        ), "Root spec ref should be correctly extracted."

    @pytest.mark.parametrize(
        "spec",
        [
            "access-om2",
            "access-om2+debug",
            "access-om2%intel@2025.05",
        ],
    )
    def test_get_ref__invalid(self, spec):
        manifest = {"spack": {"specs": [spec]}}

        with pytest.raises(NoSectionComponentError):
            RootSpec(manifest).get_ref()

    @pytest.mark.parametrize(
        "root_spec",
        [
            "",
            "%compiler@2.0.0",
            " %compiler@2.0.0 +debug",
            "+debug",
            "~debug",
            " +debug",
            " ~debug",
        ],
    )
    def test_get_non_version_constraints__valid(self, root_spec):
        manifest = {"spack": {"specs": [f"access-om2@git.1.0.0{root_spec}"]}}

        assert (
            RootSpec(manifest).get_non_version_constraints() == root_spec.strip()
        ), "Non-version constraints should be correctly extracted."

    @pytest.mark.parametrize(
        "root_spec, expected",
        [
            ("access-om2@git.1.0.0", True),
            ("access-om2@1.0.0", False),
        ],
    )
    def test_has_git_ref__valid(self, root_spec, expected):
        manifest = {"spack": {"specs": [root_spec]}}

        assert RootSpec(manifest).has_git_ref() == expected


class TestPackagesGetter:
    ### Fixtures ###

    @pytest.fixture
    def manifest_with_no_packages(self):
        return {"spack": {"packages": {}}}

    ### Tests ###

    @pytest.mark.parametrize(
        "packages",
        [
            {
                "package1": {"require": ["@git.1.0.0"]},
                "package2": {"require": ["@git.2.0.0"]},
            },
            {},
        ],
    )
    def test___init___valid(self, packages):
        manifest = {"spack": {"packages": packages}}

        packages_getter = Packages(manifest)

        assert (
            packages_getter.packages == packages
        ), "Packages should be correctly initialized from manifest."

    def test___init___valid_no_packages(self):
        manifest = {"spack": {"packages": {}}}

        packages_getter = Packages(manifest)

        assert (
            packages_getter.packages == {}
        ), "Packages should be initialized as an empty dictionary if no packages are defined."

    def test___init___invalid_no_packages_section(self):
        manifest = {"spack": {}}

        with pytest.raises(NoSectionError):
            Packages(manifest)

    def test_from_file__valid(self, tmp_path, manifest_from_file):
        manifest_path = tmp_path / "manifest.yaml"
        with open(manifest_path, "w") as file:
            yaml.dump(manifest_from_file, file)

        assert Packages.from_file(manifest_path).manifest == manifest_from_file

    def test_from_file__invalid(self):
        manifest_path = (
            "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"
        )

        with pytest.raises(OSError):
            Packages.from_file(manifest_path)

    def test_get_package_requirements__valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                }
            }
        }

        packages_getter = Packages(manifest)
        requirements = packages_getter.get_package_requirements("package1")

        assert requirements == {
            "require": ["@git.1.0.0"]
        }, "Package requirements should be correctly retrieved."

    def test_get_package_requirements__invalid_no_package(
        self, manifest_with_no_packages
    ):
        packages_getter = Packages(manifest_with_no_packages)
        with pytest.raises(NoSectionComponentError):
            packages_getter.get_package_requirements("nonexistent_package")

    @pytest.mark.parametrize("version_req", ["@git.1.0.9", "@2.0.0"])
    def test_get_package_full_version_requirement__valid(self, version_req):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": [version_req, "+debug"]},
                }
            }
        }

        packages_getter = Packages(manifest)
        full_version = packages_getter.get_package_full_version_requirement("package1")

        assert (
            full_version == version_req
        ), "Full version requirement should be correctly retrieved."

    def test_get_package_full_version_requirement__invalid_no_package(
        self, manifest_with_no_packages
    ):

        packages_getter = Packages(manifest_with_no_packages)
        with pytest.raises(NoSectionError):
            packages_getter.get_package_full_version_requirement("nonexistent_package")

    @pytest.mark.parametrize(
        "version_reqs",
        [
            ["@git.1.0.0", "+debug", "%compiler@2.0.0"],
            ["@git.2.0.0"],
        ],
    )
    def test_get_package_requirements__valid(self, version_reqs):
        manifest = {"spack": {"packages": {"package1": {"require": version_reqs}}}}

        packages_getter = Packages(manifest)
        requirements = packages_getter.get_package_requirements("package1")

        assert (
            requirements == version_reqs
        ), "Package requirements should be correctly retrieved."

    def test_get_package_requirements__invalid_no_requirements(self):
        manifest = {"spack": {"packages": {"package1": {}}}}

        packages_getter = Packages(manifest)

        assert (
            packages_getter.get_package_requirements("package1") == []
        ), "Package with no requirements should return an empty list."

    @pytest.mark.parametrize(
        "ref_requirement, expected_ref",
        [
            ("@git.1.0.0", "1.0.0"),
            ("@2.0.0", "2.0.0"),
            ("@git.2025.05+debug", "2025.05"),
        ],
    )
    def test_get_package_ref_requirement__valid(self, ref_requirement, expected_ref):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": [ref_requirement]},
                }
            }
        }

        packages_getter = Packages(manifest)
        ref = packages_getter.get_package_ref_requirement("package1")

        assert (
            ref == expected_ref
        ), "Package ref requirement should be correctly retrieved."

    def test_get_package_ref_requirement__invalid_no_package(
        self, manifest_with_no_packages
    ):
        packages_getter = Packages(manifest_with_no_packages)
        with pytest.raises(NoSectionComponentError):
            packages_getter.get_package_ref_requirement("nonexistent_package")


class TestProjectionsGetter:
    def test_from_file__invalid(self):
        manifest_path = (
            "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"
        )

        with pytest.raises(OSError):
            Projections.from_file(manifest_path)

    def test__get_defined_projections__valid(self):
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {
                            "projections": {
                                "package1": "package1/1.0.0",
                                "package2": "package2/2.0.0",
                            }
                        }
                    }
                }
            }
        }

        expected = {"package1": "package1/1.0.0", "package2": "package2/2.0.0"}

        result = Projections(manifest).get()

        assert (
            result == expected
        ), "A valid manifest should return all defined projections."

    def test__get_defined_projections__no_projections(self):
        manifest = {"spack": {"modules": {"default": {"tcl": {"projections": {}}}}}}

        expected = dict()

        result = Projections(manifest).get()

        assert (
            result == expected
        ), "Manifest without projections should return an empty set."

    def test__get_defined_projections__no_modules_section(self):
        manifest = {"spack": {}}

        expected = dict()

        result = Projections(manifest).get()

        assert (
            result == expected
        ), "Manifest without a modules section should return an empty set."


class TestIncludesGetter:
    def test_from_file__invalid(self):
        manifest_path = (
            "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"
        )

        with pytest.raises(OSError):
            Includes.from_file(manifest_path)

    @pytest.mark.parametrize(
        "includes",
        [
            ["root-spec", "package2", "package3"],
            ["root-spec"],
            [],
        ],
    )
    def test__get_defined_includes__valid(self, includes):
        manifest = {"spack": {"modules": {"default": {"tcl": {"include": includes}}}}}

        result = Includes(manifest).get()

        assert (
            result == includes
        ), "A valid manifest should return all defined includes."

    def test__get_defined_includes__no_modules_section(self):
        manifest = {"spack": {}}

        expected = []

        result = Includes(manifest).get()

        assert (
            result == expected
        ), "Manifest without a modules section should return an empty set."


class TestSpecsGetter:
    @pytest.mark.parametrize(
        "specs",
        [
            ["access-om2"],  # Single root spec
            ["access-om2 +var", "access-om2 ~var"]  # Multiple root specs
        ]
    )
    def test_get_specs__valid(self, specs):
        manifest = {"spack": {"specs": specs}}

        assert Specs(manifest).get_specs() == specs, "Should return all specs"

    @pytest.mark.parametrize(
        "specs,expected",
        [
            (["access-om2", "access-om3"], ["access-om2"]),  # Single root spec
            (["access-om2 +var", "access-om2 ~var", "access-om3"], ["access-om2 +var", "access-om2 ~var"])  # Multiple root specs
        ]
    )
    def test_get_specs_with_name__exist(self, specs, expected):
        manifest = {"spack": {"specs": specs}}

        assert Specs(manifest).get_specs_with_name("access-om2") == expected, "Should return specs with the given name"

    @pytest.mark.parametrize(
        "specs",
        [
            ["access-om3"],
            ["access-om3 +var", "access-om3 ~var"]
        ]
    )
    def test_get_specs_with_name__no_exist(self, specs):
        manifest = {"spack": {"specs": specs}}

        assert Specs(manifest).get_specs_with_name("access-om2") == [], "Should return no specs"