import pytest

from scripts.spack_manifest.injection.modules import (
    _get_defined_projections,
    _get_packages_with_versions_defined,
    _generate_projection_version_from_package,
    _generate_projection_version_from_spec_or_raise,
    generate_projections,
    inject_projections,
    parse_args
)


class TestGetDefinedProjections:
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
        result = _get_defined_projections(manifest)

        assert (
            result == expected
        ), "A valid manifest should return all defined projections."

    def test__get_defined_projections__no_projections(self):
        manifest = {"spack": {"modules": {"default": {"tcl": {"projections": {}}}}}}

        expected = dict()
        result = _get_defined_projections(manifest)

        assert (
            result == expected
        ), "Manifest without projections should return an empty set."

    def test__get_defined_projections__no_modules_section(self):
        manifest = {"spack": {}}

        expected = dict()
        result = _get_defined_projections(manifest)

        assert (
            result == expected
        ), "Manifest without a modules section should return an empty set."


class TestGetPackagesWithVersionsDefined:
    def test__get_packages_with_versions_defined__valid(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0"]},
                    "package2": {"require": ["@git.2.0.0"]},
                    "package3": {"require": ["@git.3.0.0"]},
                }
            }
        }

        expected = {"package1", "package2", "package3"}
        result = _get_packages_with_versions_defined(manifest)

        assert (
            result == expected
        ), "A valid manifest should return all packages with versions defined."

    def test__get_packages_with_versions_defined__no_package_definitions(self):
        manifest = {"spack": {"packages": {}}}

        expected = set()
        result = _get_packages_with_versions_defined(manifest)

        assert (
            result == expected
        ), "An empty packages section should return an empty set."

    def test__get_packages_with_versions_defined__no_package_section(self):
        manifest = {"spack": {}}

        expected = set()
        result = _get_packages_with_versions_defined(manifest)

        assert (
            result == expected
        ), "Manifest without a packages section should return an empty set."

    def test__get_packages_with_versions_defined__package_defined_with_no_version(self):
        manifest = {"spack": {"packages": {"package1": {"require": [r"%gcc@8.5.0"]}}}}

        expected = set()
        result = _get_packages_with_versions_defined(manifest)
        assert (
            result == expected
        ), "Package defined without a version should not be included in the result."

    def test__get_packages_with_versions_defined__package_defined_with_multiple_constraints(
        self,
    ):
        manifest = {
            "spack": {
                "packages": {"package1": {"require": ["@git.1.0.0", r"%gcc@8.5.0"]}}
            }
        }

        expected = {"package1"}
        result = _get_packages_with_versions_defined(manifest)

        assert (
            result == expected
        ), "Packages with versions and other constraints should be included in the result."


class TestGenerateProjectionVersionFromPackage:
    def test__generate_projection_version_from_package__valid_at_git(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0 +debug"]},
                    "package2": {"require": ["@git.2.0.0"]},
                }
            }
        }

        projection = "package1"
        expected_version = "1.0.0"
        result = _generate_projection_version_from_package(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for package {projection}."

    def test__generate_projection_version_from_package__valid_at_no_git(self):
        manifest = {"spack": {"packages": {"package1": {"require": ["@1.0.0 +debug"]}}}}

        projection = "package1"
        expected_version = "1.0.0"
        result = _generate_projection_version_from_package(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for package {projection}."

    def test__generate_projection_version_from_package__no_version_defined(self):
        manifest = {"spack": {"packages": {"package1": {"require": [r"%gcc@8.5.0"]}}}}

        projection = "package1"
        result = _generate_projection_version_from_package(manifest, projection)

        assert (
            result is None
        ), "Should return None when no version is defined for the package."


class TestGenerateProjectionVersionFromSpecOrRaise:

    def test__generate_projection_version_from_spec_or_raise__valid_single_target(self):
        manifest = {"spack": {"specs": ["access-om2@git.2025.05.000 +debug ~mpi"]}}

        projection = "access-om2"
        expected_version = "2025.05.000"
        result = _generate_projection_version_from_spec_or_raise(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for spec {projection}."

    def test__generate_projection_version_from_spec_or_raise__valid_multi_target(self):
        manifest = {
            "spack": {
                "definitions": [
                    {"ROOT_PACKAGE": ["access-om2@git.2025.05.000 +debug ~mpi"]}
                ]
            }
        }

        projection = "access-om2"
        expected_version = "2025.05.000"
        result = _generate_projection_version_from_spec_or_raise(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for spec {projection}."

    def test__generate_projection_version_from_spec_or_raise__single_target_no_version_defined(
        self,
    ):
        manifest = {"spack": {"specs": ["access-om2"]}}

        projection = "access-om2"

        with pytest.raises(ValueError):
            _generate_projection_version_from_spec_or_raise(manifest, projection)

    def test__generate_projection_version_from_spec_or_raise__multi_target_no_version_defined(
        self,
    ):
        manifest = {"spack": {"definitions": [{"ROOT_PACKAGE": ["access-om2"]}]}}

        projection = "access-om2"

        with pytest.raises(ValueError):
            _generate_projection_version_from_spec_or_raise(manifest, projection)

    def test__generate_projection_version_from_spec_or_raise__single_target_wrong_projection(
        self,
    ):
        manifest = {"spack": {"specs": ["access-om2@git.2025.05.000 +debug ~mpi"]}}

        projection = "wrong-projection"

        with pytest.raises(ValueError):
            _generate_projection_version_from_spec_or_raise(manifest, projection)

    def test__generate_projection_version_from_spec_or_raise__multi_target_wrong_projection(
        self,
    ):
        manifest = {
            "spack": {
                "definitions": [
                    {"ROOT_PACKAGE": ["access-om2@git.2025.05.000 +debug ~mpi"]}
                ]
            }
        }

        projection = "wrong-projection"

        with pytest.raises(ValueError):
            _generate_projection_version_from_spec_or_raise(manifest, projection)


class TestGenerateProjections:
    def test__generate_projections__valid_single_target(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.2025.05.000 +debug ~mpi"],
                "packages": {
                    "mom5": {"require": ["@git.2025.05.000 +debug ~mpi"]},
                    "cice5": {"require": ["@2025.03.001 +debug ~mpi"]},
                    "libaccess-om2": {"require": ["@git.2025.05.000", "+debug ~mpi"]},
                },
            }
        }

        root_spec_name = "access-om2"
        defined_projections = dict()
        projections_to_generate = {"access-om2", "mom5", "cice5"}

        expected = {
            "access-om2": "{name}/2025.05.000",
            "cice5": "{name}/2025.03.001-{hash:7}",
            "mom5": "{name}/2025.05.000-{hash:7}",
        }

        result = generate_projections(
            manifest, root_spec_name, defined_projections, projections_to_generate
        )

        assert (
            result == expected
        ), "Generated projections should match the expected output."

    def test__generate_projections__valid_single_target_some_projections_defined(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.2025.05.000 +debug ~mpi"],
                "packages": {
                    "mom5": {"require": ["@git.2025.05.000 +debug ~mpi"]},
                    "cice5": {"require": ["@2025.03.001 +debug ~mpi"]},
                    "libaccess-om2": {"require": ["@git.2025.05.000", "+debug ~mpi"]},
                },
            }
        }

        root_spec_name = "access-om2"
        defined_projections = {"mom5": "{name}/2025.03.000-{hash:7}"}
        projections_to_generate = {"access-om2", "cice5"}

        expected = {
            "access-om2": "{name}/2025.05.000",
            "cice5": "{name}/2025.03.001-{hash:7}",
            "mom5": "{name}/2025.03.000-{hash:7}",
        }

        result = generate_projections(
            manifest, root_spec_name, defined_projections, projections_to_generate
        )

        assert (
            result == expected
        ), "Generated projections should match the expected output."

    def test__generate_projections__valid_multi_target(self):
        manifest = {
            "spack": {
                "definitions": [
                    {"ROOT_PACKAGE": ["access-om2@git.2025.05.000 +debug ~mpi"]}
                ],
                "packages": {
                    "mom5": {"require": ["@git.2025.05.000 +debug ~mpi"]},
                    "cice5": {"require": ["@2025.03.001 +debug ~mpi"]},
                    "libaccess-om2": {"require": ["@git.2025.05.000", "+debug ~mpi"]},
                },
            }
        }

        root_spec_name = "access-om2"
        defined_projections = dict()
        projections_to_generate = {"access-om2", "mom5", "cice5"}

        expected = {
            "access-om2": "{name}/2025.05.000",
            "cice5": "{name}/2025.03.001-{hash:7}",
            "mom5": "{name}/2025.05.000-{hash:7}",
        }

        result = generate_projections(
            manifest, root_spec_name, defined_projections, projections_to_generate
        )

        assert (
            result == expected
        ), "Generated projections should match the expected output."

    def test__generate_projections__valid_multi_target_some_projections_defined(self):
        manifest = {
            "spack": {
                "definitions": [
                    {"ROOT_PACKAGE": ["access-om2@git.2025.05.000 +debug ~mpi"]}
                ],
                "packages": {
                    "mom5": {"require": ["@git.2025.05.000 +debug ~mpi"]},
                    "cice5": {"require": ["@2025.03.001 +debug ~mpi"]},
                    "libaccess-om2": {"require": ["@git.2025.05.000", "+debug ~mpi"]},
                },
            }
        }

        root_spec_name = "access-om2"
        defined_projections = {"cice5": "{name}/2025.10.000-{hash:7}"}
        projections_to_generate = {"access-om2", "mom5"}

        expected = {
            "access-om2": "{name}/2025.05.000",
            "cice5": "{name}/2025.10.000-{hash:7}",
            "mom5": "{name}/2025.05.000-{hash:7}",
        }

        result = generate_projections(
            manifest, root_spec_name, defined_projections, projections_to_generate
        )

        assert (
            result == expected
        ), "Generated projections should match the expected output."

    def test__generate_projections__no_package_projections_to_generate(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.2025.05.000 +debug ~mpi"],
                "packages": {
                    "mom5": {"require": ["@git.2025.05.000 +debug ~mpi"]},
                    "cice5": {"require": ["@2025.03.001 +debug ~mpi"]},
                    "libaccess-om2": {"require": ["@git.2025.05.000", "+debug ~mpi"]},
                },
            }
        }

        root_spec_name = "access-om2"
        defined_projections = dict()
        projections_to_generate = set(["access-om2"])

        expected = {"access-om2": "{name}/2025.05.000"}

        result = generate_projections(
            manifest, root_spec_name, defined_projections, projections_to_generate
        )

        assert (
            result == expected
        ), "Should return an empty projections section when no projections are requested."

    def test__generate_projections__skips_invalid_projections(self):
        manifest = {
            "spack": {
                "specs": ["access-om2@git.2025.05.000 +debug ~mpi"],
                "packages": {
                    "mom5": {"require": [r"%gcc@8.5.0 +debug ~mpi"]},
                    "cice5": {"require": [r"%gcc@8.5.0 +debug ~mpi"]},
                    "libaccess-om2": {"require": ["@git.2025.05.000", "+debug ~mpi"]},
                },
            }
        }

        root_spec_name = "access-om2"
        defined_projections = dict()
        projections_to_generate = {"access-om2", "mom5", "cice5"}

        expected = {
            "access-om2": "{name}/2025.05.000",
            # mom5 and cice5 should be skipped as they do not have a valid version defined.
        }

        result = generate_projections(
            manifest, root_spec_name, defined_projections, projections_to_generate
        )

        assert (
            result == expected
        ), "Should skip package projections that do not have a valid version defined."


class TestInjectProjections:
    def test_inject_projections__valid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        root_spec_name = "access-om2"
        packages = {"mom5", "cice5", "libaccessom2", "oasis3-mct"}

        output = inject_projections(manifest_path, root_spec_name, packages)

        expected_output = {
            "spack": {
                "specs": ["access-om2@git.2024.03.0=latest"],
                "packages": {
                    "cice5": {"require": ["@git.2023.10.19=access-om2"]},
                    "mom5": {"require": ["@git.2023.11.09=access-om2"]},
                    "libaccessom2": {"require": ["@git.2023.10.26=access-om2"]},
                    "oasis3-mct": {"require": ["@git.2023.11.09=access-om2"]},
                    "netcdf-c": {"require": ["@4.7.4"]},
                    "netcdf-fortran": {"require": ["@4.5.2"]},
                    "parallelio": {"require": ["@2.5.2"]},
                    "openmpi": {"require": ["@4.0.2"]},
                    "all": {"require": ["%intel@19.0.5.281", "target=x86_64"]},
                },
                "view": True,
                "concretizer": {"unify": True},
                "modules": {
                    "default": {
                        "tcl": {
                            "include": [
                                "access-om2",
                                "mom5",
                                "cice5",
                                "libaccessom2",
                                "oasis3-mct",
                            ],
                            "projections": {
                                "access-om2": "{name}/2024.03.0",
                                "cice5": "{name}/2023.10.19-{hash:7}",
                                "libaccessom2": "{name}/2023.10.26-{hash:7}",
                                "mom5": "{name}/2023.11.09-{hash:7}",
                                "oasis3-mct": "{name}/2023.11.09-{hash:7}",
                            },
                        }
                    }
                },
            }
        }

        assert (
            output == expected_output
        ), "Injected projections should match the expected output."

class TestParseArgs:
    def test_parse_args__valid_no_optionals_one_package(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--root-spec",
            "access-om2",
            "--packages",
            "mom5",
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        assert parsed_args.root_spec == "access-om2"
        assert parsed_args.packages == "mom5"
        assert parsed_args.output is None, "Output should be None when not specified."


    def test_parse_args__valid_no_optionals_multiple_packages(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--root-spec",
            "access-om2",
            "--packages",
            "mom5 cice5 libaccessom2"
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        assert parsed_args.root_spec == "access-om2"
        assert parsed_args.packages == "mom5 cice5 libaccessom2"
        assert parsed_args.output is None, "Output should be None when not specified."


    def test_parse_args__valid_with_optionals_multiple_packages(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--root-spec",
            "access-om2",
            "--output",
            "output.yaml",
            "--packages",
            "mom5 cice5 libaccessom2"
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        assert parsed_args.root_spec == "access-om2"
        assert parsed_args.output == "output.yaml"
        assert parsed_args.packages == "mom5 cice5 libaccessom2"