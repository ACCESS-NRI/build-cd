import pytest

from scripts.spack_manifest.injection.prerelease import (
    inject_prerelease_information,
    add_prerelease_repos_section,
    remove_potential_root_spec_git_version,
    update_root_spec_projection_version,
    add_namespace_to_other_projection_versions,
    parse_args
)

class TestUpdateRootSpecProjectionVersion:
    def test_update_root_spec_projection_version__valid_existing(self):
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {
                            "projections": {
                                "access-om2": "{name}/1.0.0",
                                "dependency": "{name}/2.0.0"
                            }
                        }
                    }
                }
            }
        }
        root_spec_name = "access-om2"
        root_spec_version = "pr12-2"

        updated_manifest = update_root_spec_projection_version(manifest, root_spec_name, root_spec_version)

        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_name] == f"{{name}}/{root_spec_version}"

    def test_update_root_spec_projection_version__valid_new(self):
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {
                            "projections": {}
                        }
                    }
                }
            }
        }
        root_spec_name = "access-om2"
        root_spec_version = "pr12-2"

        updated_manifest = update_root_spec_projection_version(manifest, root_spec_name, root_spec_version)

        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_name] == f"{{name}}/{root_spec_version}"

    def test_update_root_spec_projection_version__no_projections(self):
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {}
                    }
                }
            }
        }
        root_spec_name = "access-om2"
        root_spec_version = "pr12-2"

        updated_manifest = update_root_spec_projection_version(manifest, root_spec_name, root_spec_version)

        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"][root_spec_name] == f"{{name}}/{root_spec_version}"

class TestRemovePotentialRootSpecGitVersion:
    def test_remove_potential_root_spec_git_version__valid_no_constraints(self):
        manifest = {
            "spack": {
                "specs": [
                    "access-om2@git.1.0.0"
                ]
            }
        }

        updated_manifest = remove_potential_root_spec_git_version(manifest)

        assert updated_manifest["spack"]["specs"][0] == "access-om2"

    def test_remove_potential_root_spec_git_version__valid_with_constraints_no_space(self):
        manifest = {
            "spack": {
                "specs": [
                    r"access-om2@git.1.0.0%compiler@2.0.0"
                ]
            }
        }

        updated_manifest = remove_potential_root_spec_git_version(manifest)

        assert updated_manifest["spack"]["specs"][0] == f"access-om2 %compiler@2.0.0"

    def test_remove_potential_root_spec_git_version__valid_with_constraints_with_space(self):
        manifest = {
            "spack": {
                "specs": [
                    r"access-om2@git.1.0.0 %compiler@2.0.0 +debug"
                ]
            }
        }

        updated_manifest = remove_potential_root_spec_git_version(manifest)

        assert updated_manifest["spack"]["specs"][0] == f"access-om2 %compiler@2.0.0 +debug"

    def test_remove_potential_root_spec_git_version__invalid_no_git_version(self):
        manifest = {
            "spack": {
                "specs": [
                    "access-om2@1.0.0"
                ]
            }
        }

        updated_manifest = dict(remove_potential_root_spec_git_version(manifest))

        assert manifest == updated_manifest, "Manifest should remain unchanged if no git version is present"

class TestAddPrereleaseReposSection:
    def test_add_prerelease_repos_section__valid(self):
        manifest_str = "spack:\n  specs:\n    - access-om2@git.1.0.0\n"
        spack_packages_path = "/path/to/spack/packages"

        updated_manifest_str = add_prerelease_repos_section(manifest_str, spack_packages_path)

        last_three_lines = "\n".join(updated_manifest_str.splitlines()[-3:])

        expected_last_three_lines = (
            f"  repos::\n"
            f"  - {spack_packages_path}\n"
            f"  - $spack/var/spack/repos/builtin\n"
        )

        assert last_three_lines.strip() == expected_last_three_lines.strip()

class TestInjectPrereleaseInformation:
    def test_inject_prerelease_information__valid(self):
        manifest_path = "tests/scripts/spack_manifest/injection/inputs/prerelease.spack.yaml"
        root_spec_version = "pr12-12"
        spack_packages_path = "/some/spack-packages"

        updated_manifest_str: str = inject_prerelease_information(
            manifest_path, root_spec_version, False, spack_packages_path
        )

        expected_manifest_path = "tests/scripts/spack_manifest/injection/outputs/expected.prerelease.spack.yaml"
        with open(expected_manifest_path, 'r') as f:
            expected_manifest_str = f.read()

        assert updated_manifest_str.strip() == expected_manifest_str.strip()

class TestAddNamespaceToOtherProjectionVersions:
    def test_add_namespace_to_other_projection_versions__valid(self):
        root_spec_name = "access-om2"
        version = "pr12-2"

        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {
                            "projections": {
                                "access-om2": f"{{name}}/{version}",
                                "dependency1": "{name}/2.0.0",
                                "dependency2": "{name}/3.0.0-{hash:7}",
                                "dependency3": "{name}/special/4.0.0-{hash:7}"
                            }
                        }
                    }
                }
            }
        }


        updated_manifest = add_namespace_to_other_projection_versions(manifest, root_spec_name, version)

        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"]["access-om2"] == f"{{name}}/{version}"
        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"]["dependency1"] == f"{root_spec_name}/dependencies/{version}/{{name}}/2.0.0"
        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"]["dependency2"] == f"{root_spec_name}/dependencies/{version}/{{name}}/3.0.0-{{hash:7}}"
        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"]["dependency3"] == f"{root_spec_name}/dependencies/{version}/{{name}}/special/4.0.0-{{hash:7}}"

    def test_add_namespace_to_other_projection_versions__no_projections_except_for_root(self):
        root_spec_name = "access-om2"
        version = "pr12-2"
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {
                            "projections": {
                                "access-om2": f"{{name}}/{version}"
                            }
                        }
                    }
                }
            }
        }

        updated_manifest = add_namespace_to_other_projection_versions(manifest, root_spec_name, version)

        assert updated_manifest["spack"]["modules"]["default"]["tcl"]["projections"] == {"access-om2": f"{{name}}/{version}"}

    def test_add_namespace_to_other_projection_versions__no_projections(self):
        root_spec_name = "access-om2"
        version = "pr12-2"
        manifest = {
            "spack": {
                "modules": {
                    "default": {
                        "tcl": {}
                    }
                }
            }
        }

        updated_manifest = add_namespace_to_other_projection_versions(manifest, root_spec_name, version)

        assert updated_manifest["spack"]["modules"]["default"]["tcl"] == {}

class TestParseArgs:
    def test_parse_args__valid_no_optionals(self):
        args = [
            "--manifest", "path/to/manifest.yaml",
            "--version", "pr12-2",
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "path/to/manifest.yaml"
        assert parsed_args.version == "pr12-2"
        assert parsed_args.spack_packages_path is None
        assert parsed_args.output is None

    def test_parse_args__valid_with_optionals(self):
        args = [
            "--manifest", "path/to/manifest.yaml",
            "--version", "pr12-2",
            "--spack-packages-path", "/some/spack/packages",
            "--output", "output.yaml"
        ]

        parsed_args = parse_args(args)

        assert parsed_args.manifest == "path/to/manifest.yaml"
        assert parsed_args.version == "pr12-2"
        assert parsed_args.spack_packages_path == "/some/spack/packages"
        assert parsed_args.output == "output.yaml"
