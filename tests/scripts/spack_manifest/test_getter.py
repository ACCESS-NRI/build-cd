import pytest

from scripts.spack_manifest.getter import (
    RootSpec,
    Packages,
    Includes,
    Projections,

    NoSectionError,
    NoSectionComponentError,
)

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
            "spack": {
                "definitions": [
                    {
                        "ROOT_PACKAGE": ["access-om2@git.1.0.0"]
                    }
                ]
            }
        }

        root_spec_getter = RootSpec(manifest)

        assert root_spec_getter.root_spec == "access-om2@git.1.0.0", "Root spec should be correctly initialized from multi-target manifest."

    def test___init___valid_single_target_spec(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)

        assert root_spec_getter.root_spec == "access-om2@git.1.0.0", "Root spec should be correctly initialized from single-target manifest."

    def test___init___invalid_no_root_spec(self):
        manifest = {
            "spack": {
                "specs": []
            }
        }

        with pytest.raises(NoSectionError):
            RootSpec(manifest)

    def test___init___invalid_no_manifest(self):
        with pytest.raises(NoSectionError):
            RootSpec({})

    def test_from_file__valid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/prerelease.spack.yaml"
        root_spec_getter = RootSpec.from_file(manifest_path)

        assert root_spec_getter.root_spec == "access-om2@git.2024.03.0=latest", "Root spec should be correctly retrieved from file."

    def test_from_file__invalid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"

        with pytest.raises(OSError):
            RootSpec.from_file(manifest_path)

    def test_get_name__valid(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        name = root_spec_getter.get_name()

        assert name == "access-om2", "Root spec name should be correctly extracted."

    def test_get_name__invalid(self):
        manifest = {
            "spack": {
                "specs": ["@git.1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        with pytest.raises(NoSectionComponentError):
            root_spec_getter.get_name()

    def test_get_ref__valid_git(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        ref = root_spec_getter.get_ref()

        assert ref == "1.0.0", "Root spec ref should be correctly extracted."

    def test_get_ref__valid_non_git(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        ref = root_spec_getter.get_ref()

        assert ref == "1.0.0", "Root spec ref should be correctly extracted."

    def test_get_ref__valid_git_with_constraints(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0 %compiler@2.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        ref = root_spec_getter.get_ref()

        assert ref == "1.0.0", "Root spec ref should be correctly extracted with constraints."

    def test_get_ref__valid_git_with_space_constraints(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0 %compiler@2.0.0 +debug"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        ref = root_spec_getter.get_ref()

        assert ref == "1.0.0", "Root spec ref should be correctly extracted with space constraints."

    def test_get_ref__valid_git_with_spack_version_and_constraints(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0=develop %compiler@2.0.0 +debug"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        ref = root_spec_getter.get_ref()

        assert ref == "1.0.0", "Root spec ref should be correctly extracted with Spack version and constraints."

    def test_get_ref__invalid(self):
        manifest = {
            "spack": {
                "specs": ["access-om2"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        with pytest.raises(NoSectionComponentError):
            root_spec_getter.get_ref()

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
        ]
    )
    def test_get_non_version_constraints__valid(self, root_spec):
        manifest = {
            "spack": {
                "specs": [f"access-om2@git.1.0.0{root_spec}"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        constraints = root_spec_getter.get_non_version_constraints()

        assert constraints == root_spec.strip(), "Non-version constraints should be correctly extracted."

    def test_has_git_ref__valid_yes(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        assert root_spec_getter.has_git_ref(), "Root spec should have a git ref."

    def test_has_git_ref__valid_no(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@1.0.0"]
            }
        }

        root_spec_getter = RootSpec(manifest)
        assert not root_spec_getter.has_git_ref(), "Root spec should not have a git ref."


class TestPackagesGetter:
    def test___init___valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                    "package2": {"require": ["@git.2.0.0"]},
                }
            }
        }

        packages_getter = Packages(manifest)

        assert packages_getter.packages == {
            "package1": {"require": ["@git.1.0.0"]},
            "package2": {"require": ["@git.2.0.0"]},
        }, "Packages should be correctly initialized from manifest."

    def test___init___invalid_no_packages_section(self):
        manifest = {
            "spack": {}
        }

        with pytest.raises(NoSectionError):
            Packages(manifest)

    def test___init___invalid_no_packages(self):
        manifest = {
            "spack": {
                "packages": {}
            }
        }

        packages_getter = Packages(manifest)

        assert packages_getter.packages == {}, "Packages should be initialized as an empty dictionary if no packages are defined."

    def test___init___invalid_no_packages(self):
        manifest = {"spack": {}}

        with pytest.raises(NoSectionError):
            Packages(manifest)

    def test_from_file__valid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/prerelease.spack.yaml"
        packages_getter = Packages.from_file(manifest_path)

    def test_from_file__invalid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"

        with pytest.raises(OSError):
            Packages.from_file(manifest_path)

    def test_get_package_requirements__valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                    "package2": {"require": ["@git.2.0.0"]},
                }
            }
        }

        packages_getter = Packages(manifest)
        requirements = packages_getter.get_package_requirements("package1")

        assert requirements == {"require": ["@git.1.0.0"]}, "Package requirements should be correctly retrieved."

    def test_get_package_requirements__invalid_no_package(self):
        manifest = {
            "spack": {
                "packages": {}
            }
        }

        packages_getter = Packages(manifest)
        with pytest.raises(NoSectionComponentError):
            packages_getter.get_package_requirements("nonexistent_package")

    def test_get_package_full_version_requirement__valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                    "package2": {"require": ["@git.2.0.0"]},
                }
            }
        }

        packages_getter = Packages(manifest)
        full_version = packages_getter.get_package_full_version_requirement("package1")

        assert full_version == "@git.1.0.0", "Full version requirement should be correctly retrieved."

    def test_get_package_full_version_requirement__invalid_no_package(self):
        manifest = {
            "spack": {
                "packages": {}
            }
        }

        packages_getter = Packages(manifest)
        with pytest.raises(NoSectionError):
            packages_getter.get_package_full_version_requirement("nonexistent_package")

    def test_get_package_requirements__valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {
                        "require": [
                            "@git.1.0.0",
                            "+debug",
                            "%compiler@2.0.0"
                        ]
                    }
                }
            }
        }

        packages_getter = Packages(manifest)
        requirements = packages_getter.get_package_requirements("package1")

        assert requirements == ["@git.1.0.0", "+debug","%compiler@2.0.0"], "Package requirements should be correctly retrieved."

    def test_get_package_requirements__invalid_no_requirements(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {}
                }
            }
        }

        packages_getter = Packages(manifest)

        assert packages_getter.get_package_requirements("package1") == [], "Package with no requirements should return an empty list."

    def test_get_package_ref_requirement__valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                    "package2": {"require": ["@git.2.0.0"]},
                }
            }
        }

        packages_getter = Packages(manifest)
        ref = packages_getter.get_package_ref_requirement("package1")

        assert ref == "1.0.0", "Package ref requirement should be correctly retrieved."

    def test_get_package_ref_requirement__invalid_no_package(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                }
            }
        }

        packages_getter = Packages(manifest)
        with pytest.raises(NoSectionComponentError):
            packages_getter.get_package_ref_requirement("nonexistent_package")

####################

class TestProjectionsGetter:
    def test_from_file__invalid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"

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
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/invalid_manifest.yaml"

        with pytest.raises(OSError):
            Includes.from_file(manifest_path)

    def test__get_defined_includes__valid(self):
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {
                            "include": ["root-spec", "package2", "package3"]
                        }
                    }
                }
            }
        }

        expected = ["root-spec", "package2", "package3"]

        result = Includes(manifest).get()

        assert (
            result == expected
        ), "A valid manifest should return all defined includes."

    def test__get_defined_includes__no_includes(self):
        manifest = {"spack": {"modules": {"default": {"tcl": {"include": []}}}}}

        expected = []

        result = Includes(manifest).get()

        assert (
            result == expected
        ), "Manifest without includes should return an empty set."

    def test__get_defined_includes__no_modules_section(self):
        manifest = {"spack": {}}

        expected = []

        result = Includes(manifest).get()

        assert (
            result == expected
        ), "Manifest without a modules section should return an empty set."