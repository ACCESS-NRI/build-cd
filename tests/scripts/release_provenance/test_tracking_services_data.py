import pytest

from pathlib import Path
from unittest.mock import patch, Mock

from scripts.release_provenance.tracking_services_data import (
    _format_tracking_services_header,
    _format_telemetry_of_model,
    _format_telemetry_of_deployment_target,
    _format_telemetry_of_model_components,
    get_ref_from_spack_spec_version_or_raise
)
from scripts.release_provenance.tracking_services_data import TRACKING_SERVICES_JSON_SCHEMA_VERSION

class TestFormatTrackingServicesHeader():
    def test__format_tracking_services_header__valid(self):
        # Test with a valid header
        expected_header = {
            "service": "release_provenance",
            "version": f"{TRACKING_SERVICES_JSON_SCHEMA_VERSION}",
            "telemetry": {}
        }

        actual_header = _format_tracking_services_header()

        assert actual_header == expected_header, f"Expected {expected_header}, but got {actual_header}"

class TestFormatTelemetryOfModel():

    @patch("scripts.release_provenance.tracking_services_data._get_release_data_of_model_or_raise")
    def test__format_telemetry_of_model__valid(self, release_data_mock):
        expected_telemetry = {
            "model.name": "ACCESS-OM3",
            "model.deployment_repository_url": "https://github.com/ACCESS-NRI/ACCESS-OM3",
            "model_deployment.version": "2025.01.2",
            "model_deployment.status": "ACTIVE",
            "model_deployment.released_at": "2025-03-27T05:16:15Z",
            "model_deployment.release_url": "https://github.com/ACCESS-NRI/ACCESS-OM3/releases/tag/2025.01.2",
            "deployment_targets": [],
        }

        # Mock the return value of _get_release_data_of_model_or_raise
        release_data_mock.return_value = {
            "created_at": "2025-03-27T05:16:15Z",
            "html_url": "https://github.com/ACCESS-NRI/ACCESS-OM3/releases/tag/2025.01.2",
        }

        actual_telemetry = _format_telemetry_of_model("ACCESS-NRI/ACCESS-OM3", Path("tests/scripts/release_provenance/inputs/deploy-access-om3-outputs.Gadi"))

        assert actual_telemetry == expected_telemetry, f"Expected {expected_telemetry}, but got {actual_telemetry}"

    @patch("scripts.release_provenance.tracking_services_data.requests.get", autospec=True)
    def test__format_telemetry_of_model__invalid_repo(self, requests_mock):

        # Mock the response of the requests.get call to simulate an invalid repository
        requests_mock.return_value = Mock(status_code=404)

        with pytest.raises(ValueError):
            _format_telemetry_of_model("invalid-repo", Path("tests/scripts/release_provenance/inputs/deploy-access-om3-outputs.Gadi"))

    def test__format_telemetry_of_model_invalid_file(self):
        with pytest.raises(FileNotFoundError):
            _format_telemetry_of_model("ACCESS-NRI/ACCESS-OM3", Path("invalid-file-path"))

class TestFormatTelemetryOfDeploymentTarget():
    def test__format_telemetry_of_deployment_target___valid_with_no_components(self):
        # Removing the components from the expected telemetry as that is tested in TestFormatTelemetryOfModelComponents
        expected_telemetry_without_components = {
            "deployment_target.name": "Gadi",
            "deployment_target.spack_version": "0.22",
            "deployment_target.spack_git_hash": "qwerty",
            "deployment_target.spack_config_version": "2025.02.2",
            "deployment_target.spack_config_git_hash": "asdfg",
            "deployment_target.builtin_spack_packages_version": "2025.03.002",
            "deployment_target.builtin_spack_packages_git_hash": "zxcvb",
            "deployment_target.access_spack_packages_version": "2025.10.000",
            "deployment_target.access_spack_packages_git_hash": "asdfg",
            "deployment_target.module_use_location": "/g/data/vk83/modules",

            "spack_model.name": "access-om3",
            "spack_model.spack_package_hash": "3jdoekn73de234jdh38dzojhdjfriksndpqj84903",
            "spack_model.module_load_command": "access-om3/2025.01.2",
        }

        actual_telemetry = _format_telemetry_of_deployment_target("access-om3", "Gadi", Path("tests/scripts/release_provenance/inputs/deploy-access-om3-outputs.Gadi"), Path("tests/scripts/release_provenance/inputs/deploy-access-test-metadata.Gadi"))
        actual_telemetry_without_components = {k: v for k, v in actual_telemetry.items() if k not in ["spack_model_components"]}

        assert actual_telemetry_without_components == expected_telemetry_without_components, f"Without components, expected {expected_telemetry_without_components}, but got {actual_telemetry_without_components}"

class TestFormatTelemetryOfModelComponents():
    def test__format_telemetry_of_model_components__valid(self):
        expected_telemetry = [
            {
                "name": "access-test-component",
                "spack_package_hash": "uyhr286gh2jyrh2uy3r2t6rg7236tr726t",
                "version": "2025.04.000",
                "install_location": "/g/data/vk83/releases/some/thing",
                "repository_url": "https://github.com/access-nri/access-test-component/commit/aa11bb22cc33dd44ee55ff66aa77bb88cc99dd00",
                "md5s": [
                    {
                        "path": "/g/data/vk83/releases/some/thing/bin/access-test-component",
                        "md5": "0cc175b9c0f1b6a831c399e269772661"
                    }
                ],
            },
        ]

        actual_telemetry = _format_telemetry_of_model_components("Gadi", Path("tests/scripts/release_provenance/inputs/deploy-access-test-metadata.Gadi"))

        assert actual_telemetry == expected_telemetry, f"Expected {expected_telemetry}, but got {actual_telemetry}"

class TestGetRefFromSpackSpecVersionOrRaise():
    def test_get_ref_from_spack_spec_version_or_raise__valid_no_git_no_version(self):
        spack_spec_version = "2025.01.2"
        expected_ref = "2025.01.2"

        actual_ref = get_ref_from_spack_spec_version_or_raise(spack_spec_version)

        assert actual_ref == expected_ref, f"Expected {expected_ref}, but got {actual_ref}"

    def test_get_ref_from_spack_spec_version_or_raise__valid_with_git_no_version(self):
        spack_spec_version = "git.2025.01.2"
        expected_ref = "2025.01.2"

        actual_ref = get_ref_from_spack_spec_version_or_raise(spack_spec_version)

        assert actual_ref == expected_ref, f"Expected {expected_ref}, but got {actual_ref}"

    def test_get_ref_from_spack_spec_version_or_raise__valid_with_git_with_version(self):
        spack_spec_version = "git.2025.01.2=access-esm1.6"
        expected_ref = "2025.01.2"

        actual_ref = get_ref_from_spack_spec_version_or_raise(spack_spec_version)

        assert actual_ref == expected_ref, f"Expected {expected_ref}, but got {actual_ref}"
