import pytest
import yaml

from scripts.model_config_manifest.prerelease_update import (
    update_model_config_manifest,
    update_modules_use_section,
    update_modules_load_section,
    update_reproduce_exe_section,
)

#### Fixtures ####

@pytest.fixture
def valid_manifest() -> dict[str, any]:
    return {
        "jobname": "01deg_jra55_iaf",
        "modules": {
            "use": ["/g/data/vk83/modules"],
            "load": ["access-om2/2025.12.000"],
        },
        "reproduce": {
            "exe": True
        }
    }

@pytest.fixture
def vaild_similar_manifest() -> dict[str, any]:
    return {
        "jobname": "01deg_jra55_iaf",
        "modules": {
            "use": ["/g/data/vk83/prerelease/modules"],
            "load": ["access-om2/2025.12.000", "other-module/1.0.0"],
        },
        "reproduce": {
            "exe": False
        }
    }

@pytest.fixture
def empty_manifest() -> dict[str, any]:
    return {}

class TestPrereleaseUpdate:
    ########################################
    ## Testing update_modules_use_section ##
    ########################################

    def test_update_modules_use_section__valid(self, valid_manifest):
        updated_manifest = update_modules_use_section(
            valid_manifest,
            deployment_target="Gadi"
        )

        assert updated_manifest["modules"]["use"] == [
            "/g/data/vk83/modules",
            "/g/data/vk83/prerelease/modules"
        ]

    def test_update_modules_use_section__vaild_similar(self, vaild_similar_manifest):
        updated_manifest = update_modules_use_section(
            vaild_similar_manifest,
            deployment_target="Gadi"
        )

        assert updated_manifest["modules"]["use"] == [
            "/g/data/vk83/prerelease/modules"
        ]

    def test_update_modules_use_section__vaild_empty(self, empty_manifest):
        updated_manifest = update_modules_use_section(
            empty_manifest,
            deployment_target="Gadi"
        )

        assert updated_manifest["modules"]["use"] == [
            "/g/data/vk83/prerelease/modules"
        ]

    #########################################
    ## Testing update_modules_load_section ##
    #########################################

    def test_update_modules_load_section__valid(self, valid_manifest):
        module = "access-om2/pr12-34"
        updated_manifest = update_modules_load_section(
            valid_manifest,
            root_sbd="access-om2",
            prerelease_module=module
        )

        assert updated_manifest["modules"]["load"] == [
            module
        ]

    def test_update_modules_load_section__vaild_similar(self, vaild_similar_manifest):
        module = "access-om2/pr12-34"
        updated_manifest = update_modules_load_section(
            vaild_similar_manifest,
            root_sbd="access-om2",
            prerelease_module=module
        )

        assert updated_manifest["modules"]["load"] == [
            module,
            "other-module/1.0.0"
        ]

    def test_update_modules_load_section__vaild_empty(self, empty_manifest):
        module = "access-om2/pr12-34"
        updated_manifest = update_modules_load_section(
            empty_manifest,
            root_sbd="access-om2",
            prerelease_module=module
        )

        assert updated_manifest["modules"]["load"] == [module]

    ##########################################
    ## Testing update_reproduce_exe_section ##
    ##########################################

    def test_update_reproduce_exe_section__valid(self, valid_manifest):
        updated_manifest = update_reproduce_exe_section(
            valid_manifest
        )

        assert updated_manifest["manifest"]["reproduce"]["exe"] is False

    def test_update_reproduce_exe_section__vaild_similar(self, vaild_similar_manifest):
        updated_manifest = update_reproduce_exe_section(
            vaild_similar_manifest
        )

        assert updated_manifest["manifest"]["reproduce"]["exe"] is False

    def test_update_reproduce_exe_section__vaild_empty(self, empty_manifest):
        updated_manifest = update_reproduce_exe_section(
            empty_manifest
        )

        assert updated_manifest["manifest"]["reproduce"]["exe"] is False
