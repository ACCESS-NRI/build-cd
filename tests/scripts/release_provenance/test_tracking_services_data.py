import pytest

from pathlib import Path
from unittest.mock import patch, Mock

from scripts.release_provenance.tracking_services_data import (
    get_repo_url_at_ref_or_raise,
    _format_tracking_services_header,
    _format_telemetry_of_model,
    _format_telemetry_of_deployment_target,
    _format_telemetry_of_model_components,
    get_ref_from_spack_spec_version_or_raise
)
from scripts.release_provenance.tracking_services_data import TRACKING_SERVICES_JSON_SCHEMA_VERSION

class TestGetRepoUrlAtVersion:

    @patch("scripts.release_provenance.tracking_services_data._get_release_url_from_ref")
    def test__get_repo_url_at_ref_or_raise__valid_repo_and_version_release(self, release_url_mock):
        # Test with a valid repository and version tag (that is a GitHub release)
        repo_url = "https://github.com/access-nri/access-om2"
        repo = "access-nri/access-om2"
        version = "2024.03.0"

        expected_release_url = f"https://github.com/{repo}/releases/tag/{version}"

        # Mock the return value of _get_release_url_from_ref
        release_url_mock.return_value = expected_release_url

        actual_url = get_repo_url_at_ref_or_raise(repo_url, version)

        assert actual_url == expected_release_url, f"Expected tag-based {expected_release_url}, but got {actual_url}"

    @patch("scripts.release_provenance.tracking_services_data._get_tag_url_from_ref")
    @patch("scripts.release_provenance.tracking_services_data._get_release_url_from_ref")
    def test__get_repo_url_at_ref_or_raise__valid_repo_and_version_tag(self, release_url_mock, tag_url_mock):
        # Test with a valid repository and version tag (that is a GitHub release)
        repo_url = "https://github.com/access-nri/access-om2"
        repo = "access-nri/access-om2"
        version = "2024.03.0"

        expected_tag_url = f"https://github.com/{repo}/releases/tag/{version}"

        # Mock the return values
        release_url_mock.return_value = None
        tag_url_mock.return_value = expected_tag_url

        actual_url = get_repo_url_at_ref_or_raise(repo_url, version)

        assert actual_url == expected_tag_url, f"Expected tag-based {expected_tag_url}, but got {actual_url}"

    @patch("scripts.release_provenance.tracking_services_data._get_sha_url_from_ref")
    @patch("scripts.release_provenance.tracking_services_data._get_tag_url_from_ref")
    @patch("scripts.release_provenance.tracking_services_data._get_release_url_from_ref")
    def test_get_repo_url_at_ref_or_raise__valid_repo_and_version_sha(self, release_url_mock, tag_url_mock, sha_url_mock):
        # Test with a valid repository and version SHA
        repo_url = "https://github.com/access-nri/access-om2"
        repo = "access-nri/access-om2"
        version = "bf1f97ca75b942dd08506b88197cf0feaa1c694d"

        expected_sha_url = f"https://github.com/{repo}/commit/{version}"

        # Mock the return values
        release_url_mock.return_value = None
        tag_url_mock.return_value = None
        sha_url_mock.return_value = expected_sha_url

        # Call the function with the mocked return values
        actual_url = get_repo_url_at_ref_or_raise(repo_url, version)

        assert actual_url == expected_sha_url, f"Expected sha-based {expected_sha_url}, but got {actual_url}"

    def test_get_repo_url_at_ref_or_raise__invalid_repo_url(self):
        # Test with an invalid repository
        repo_url = "https://github.invalid.com/access-nri/access-om2"
        version = "2024.03.0"

        with pytest.raises(ValueError):
            get_repo_url_at_ref_or_raise(repo_url, version)

    def test_get_repo_url_at_ref_or_raise__invalid_repo_structure(self):
        # Test with an invalid repository
        repo_url = "https://github.com/not-access-nri/not-access-om2"
        version = "2024.03.0"

        with pytest.raises(ValueError):
            get_repo_url_at_ref_or_raise(repo_url, version)

    @patch("scripts.release_provenance.tracking_services_data._get_sha_url_from_ref")
    @patch("scripts.release_provenance.tracking_services_data._get_tag_url_from_ref")
    @patch("scripts.release_provenance.tracking_services_data._get_release_url_from_ref")
    def test_get_repo_url_at_ref_or_raise__invalid_version(self, release_url_mock, tag_url_mock, sha_url_mock):
        # Test with an invalid version tag
        repo_url = "https://github.com/access-nri/access-om2"
        version = "invalid-tag"

        # Mock the return values
        release_url_mock.return_value = None
        tag_url_mock.return_value = None
        sha_url_mock.return_value = None

        with pytest.raises(ValueError):
            get_repo_url_at_ref_or_raise(repo_url, version)

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
    def test__format_telemetry_of_model_1_0_0__valid(self, release_data_mock):
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

        actual_telemetry = _format_telemetry_of_model("ACCESS-NRI/ACCESS-OM3", Path("tests/scripts/release_provenance/inputs/1-0-0/deploy-access-om3-outputs.Gadi"))

        assert actual_telemetry == expected_telemetry, f"Expected {expected_telemetry}, but got {actual_telemetry}"

    @patch("scripts.release_provenance.tracking_services_data.requests.get", autospec=True)
    def test__format_telemetry_of_model_1_0_0__invalid_repo(self, requests_mock):

        # Mock the response of the requests.get call to simulate an invalid repository
        requests_mock.return_value = Mock(status_code=404)

        with pytest.raises(ValueError):
            _format_telemetry_of_model("invalid-repo", Path("tests/scripts/release_provenance/inputs/1-0-0/deploy-access-om3-outputs.Gadi"))

    def test__format_telemetry_of_model_1_0_0__invalid_file(self):
        with pytest.raises(FileNotFoundError):
            _format_telemetry_of_model("ACCESS-NRI/ACCESS-OM3", Path("invalid-file-path"))

class TestFormatTelemetryOfDeploymentTarget():
    def test__format_telemetry_of_deployment_target_1_0_0__valid_with_no_components(self):
        # Removing the components from the expected telemetry as that is tested in TestFormatTelemetryOfModelComponents
        expected_telemetry_without_components = {
            "deployment_target.name": "Gadi",
            "deployment_target.spack_version": "0.22",
            "deployment_target.spack_git_hash": "qwerty",
            "deployment_target.spack_config_version": "2025.02.2",
            "deployment_target.spack_config_git_hash": "asdfg",
            "deployment_target.spack_packages_version": "2025.03.002",
            "deployment_target.spack_packages_git_hash": "zxcvb",
            "deployment_target.module_use_location": "/g/data/vk83/modules",

            "spack_model.name": "access-om3",
            "spack_model.spack_package_hash": "3jdoekn73de234jdh38dzojhdjfriksndpqj84903",
            "spack_model.module_load_command": "access-om3/2025.01.2",
        }

        actual_telemetry = _format_telemetry_of_deployment_target("access-om3", "Gadi", Path("tests/scripts/release_provenance/inputs/1-0-0/deploy-access-om3-outputs.Gadi"), Path("tests/scripts/release_provenance/inputs/1-0-0/deploy-access-test-metadata.Gadi"))
        actual_telemetry_without_components = {k: v for k, v in actual_telemetry.items() if k not in ["spack_model_components"]}

        assert actual_telemetry_without_components == expected_telemetry_without_components, f"Without components, expected {expected_telemetry_without_components}, but got {actual_telemetry_without_components}"

class TestFormatTelemetryOfModelComponents():
    def test__format_telemetry_of_model_components_1_0_0__valid(self):
        expected_telemetry = [
            {
                "name": "access-test-component",
                "spack_package_hash": "uyhr286gh2jyrh2uy3r2t6rg7236tr726t",
                "version": "2025.04.000",
                "install_location": "/g/data/vk83/releases/some/thing",
                "repository_url": "https://github.com/access-nri/access-test-component/releases/tag/2025.04.000",
            },
        ]

        actual_telemetry = _format_telemetry_of_model_components("Gadi", Path("tests/scripts/release_provenance/inputs/1-0-0/deploy-access-test-metadata.Gadi"))

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
