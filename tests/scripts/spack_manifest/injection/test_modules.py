import pytest
import yaml

from scripts.spack_manifest.injection.modules import (
    inject_projections,
    inject_includes,

    generate_projection_for_root_spec_or_raise,
    generate_projection_for_package_or_raise,

    parse_args
)
from scripts.spack_manifest.getter import (
    NoSectionComponentError,
    NoSectionError
)


class TestParseArgs:
    def test_parse_args__valid_no_optionals_one_package(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--packages",
            "mom5",
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        assert parsed_args.packages == "mom5"
        assert parsed_args.output is None, "Output should be None when not specified."


    def test_parse_args__valid_no_optionals_multiple_packages(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--packages",
            "mom5 cice5 libaccessom2"
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        assert parsed_args.packages == "mom5 cice5 libaccessom2"
        assert parsed_args.output is None, "Output should be None when not specified."


    def test_parse_args__valid_with_optionals_multiple_packages(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--output",
            "output.yaml",
            "--packages",
            "mom5 cice5 libaccessom2"
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        assert parsed_args.output == "output.yaml"
        assert parsed_args.packages == "mom5 cice5 libaccessom2"

    def test_parse_args__invalid_comma_separated_packages(self):
        args = [
            "--manifest",
            "tests/scripts/spack_manifest/injection/inputs/spack.yaml",
            "--packages",
            "mom5,cice5,libaccessom2"
        ]

        with pytest.raises(ValueError):
            parse_args(args)


class TestGenerateProjectionForRootSpecOrRaise:

    def test_generate_projection_for_root_spec_or_raise__valid_single_target(self):
        manifest = {"spack": {"specs": ["access-om2@git.2025.05.000 +debug ~mpi"]}}

        projection = "access-om2"
        expected_version = {"access-om2": "{name}/2025.05.000"}
        result = generate_projection_for_root_spec_or_raise(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for spec {projection}."

    def test_generate_projection_for_root_spec_or_raise__valid_multi_target(self):
        manifest = {
            "spack": {
                "definitions": [
                    {"ROOT_PACKAGE": ["access-om2@git.2025.05.000 +debug ~mpi"]}
                ]
            }
        }

        projection = "access-om2"
        expected_version = {"access-om2": "{name}/2025.05.000"}
        result = generate_projection_for_root_spec_or_raise(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for spec {projection}."

    def test_generate_projection_for_root_spec_or_raise__single_target_no_version_defined(
        self,
    ):
        manifest = {"spack": {"specs": ["access-om2"]}}

        projection = "access-om2"

        with pytest.raises(NoSectionComponentError):
            generate_projection_for_root_spec_or_raise(manifest, projection)

    def test_generate_projection_for_root_spec_or_raise__multi_target_no_version_defined(
        self,
    ):
        manifest = {"spack": {"definitions": [{"ROOT_PACKAGE": ["access-om2"]}]}}

        projection = "access-om2"

        with pytest.raises(NoSectionComponentError):
            generate_projection_for_root_spec_or_raise(manifest, projection)

    def test_generate_projection_for_root_spec_or_raise__single_target_wrong_projection(
        self,
    ):
        manifest = {"spack": {"specs": ["access-om2@git.2025.05.000 +debug ~mpi"]}}

        projection = "wrong-projection"

        with pytest.raises(ValueError):
            generate_projection_for_root_spec_or_raise(manifest, projection)

    def test_generate_projection_for_root_spec_or_raise__multi_target_wrong_projection(
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
            generate_projection_for_root_spec_or_raise(manifest, projection)


class TestGenerateProjectionForPackageOrRaise:
    def test_generate_projection_for_package_or_raise__valid_at_git(self):
        manifest = {
            "spack": {
                "packages": {
                    "package1": {"require": ["@git.1.0.0 +debug"]},
                    "package2": {"require": ["@git.2.0.0"]},
                }
            }
        }

        projection = "package1"
        expected_version = {"package1": "{name}/1.0.0-{hash:7}"}
        result = generate_projection_for_package_or_raise(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for package {projection}."

    def test_generate_projection_for_package_or_raise__valid_at_no_git(self):
        manifest = {"spack": {"packages": {"package1": {"require": ["@1.0.0 +debug"]}}}}

        projection = "package1"
        expected_version = {"package1": "{name}/1.0.0-{hash:7}"}
        result = generate_projection_for_package_or_raise(manifest, projection)

        assert (
            result == expected_version
        ), f"Expected version {expected_version} for package {projection}."

    def test_generate_projection_for_package_or_raise__no_version_defined(self):
        manifest = {"spack": {"packages": {"package1": {"require": [r"%gcc@8.5.0"]}}}}

        projection = "package1"

        with pytest.raises(NoSectionComponentError):
            generate_projection_for_package_or_raise(manifest, projection)


###############

class TestInjectProjections:
    def test_inject_projections__valid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        root_spec_name = "access-om2"
        packages = {"mom5", "cice5", "libaccessom2", "oasis3-mct"}

        with open(manifest_path, "r") as file:
            manifest = yaml.safe_load(file)

        output = inject_projections(manifest, root_spec_name, packages)

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
                                "mom5",
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


class TestInjectIncludes:
    def test_inject_includes__valid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/spack.yaml"
        root_spec_name = "access-om2"
        packages = {"mom5", "cice5", "libaccessom2", "oasis3-mct"}

        with open(manifest_path, "r") as file:
            manifest = yaml.safe_load(file)

        output = inject_includes(manifest, root_spec_name, packages)

        expected_output = [
            "access-om2",
            "cice5",
            "libaccessom2",
            "mom5",
            "oasis3-mct",
        ]

        assert (
            output["spack"]["modules"]["default"]["tcl"]["include"] == expected_output
        ), "Injected includes should match the expected output."