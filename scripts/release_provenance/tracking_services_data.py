import os
import json
import argparse
import jsonschema
import requests
import re

from pathlib import Path
from typing import Any

TRACKING_SERVICES_JSON_SCHEMA_VERSION = "2-0-0"
TRACKING_SERVICES_JSON_SCHEMA_URL = f"https://raw.githubusercontent.com/ACCESS-NRI/schema/main/au.org.access-nri/tracking_services/release_provenance/telemetry/{TRACKING_SERVICES_JSON_SCHEMA_VERSION}.json"


def format_deployment_information(
    repository: str,
    root_spec: str,
    deployment_folder_path: Path,
    metadata_folder_path: Path,
) -> dict[str, Any]:
    deployment_information: dict[str, Any] = {}

    deployment_information.update(_format_tracking_services_header())

    model_telemetry = _format_telemetry_of_model(repository, deployment_folder_path)
    deployment_information["telemetry"] = model_telemetry

    # We demarcate the deployment targets by the file extension (eg. *.Gadi, *.Setonix)
    deployment_targets = {
        file.split(".")[-1] for file in os.listdir(deployment_folder_path)
    }

    for deployment_target in deployment_targets:
        components_telemetry = _format_telemetry_of_deployment_target(root_spec, deployment_target, deployment_folder_path, metadata_folder_path)
        deployment_information["telemetry"]["deployment_targets"].append(components_telemetry)

    print(deployment_information)

    validate_deployment_information_against_schema(deployment_information)

    return deployment_information


def _format_tracking_services_header() -> dict[str, Any]:
    """
    Constructs and returns a dictionary representing the header data for tracking services.

    Returns:
        dict[str, Any]: A dictionary for static header data required by tracking services.
    """
    return {
        "service": "release_provenance",  # Always "release_provenance" endpoint for this client
        "version": TRACKING_SERVICES_JSON_SCHEMA_VERSION,  # May differ if the structure is updated
        "telemetry": {},
    }


def _format_telemetry_of_model(
    repository: str, deployments_folder_path: Path
) -> dict[str, Any]:
    # Telemetry of the model is the same for all deployment targets, so we only need to read the first one.
    deployment_file = deployments_folder_path / os.listdir(deployments_folder_path)[0]

    with open(deployment_file, "r") as outputs_file:
        outputs = json.load(outputs_file)

        version = outputs["release_deployment_version"]

        # Get information from release
        release_request_headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if os.getenv("GITHUB_TOKEN") is not None:
            release_request_headers["Authorization"] = (
                f"Bearer {os.getenv('GITHUB_TOKEN')}"
            )

        release_json: dict[str, Any] = _get_release_data_of_model_or_raise(repository, release_request_headers, version)

        return {
            "model.name": outputs["model_name"],
            "model.deployment_repository_url": outputs["model_deployment_repository"],
            "model_deployment.version": version,
            "model_deployment.status": "ACTIVE",  # A deployment defaults to ACTIVE status
            "model_deployment.released_at": release_json["created_at"],
            "model_deployment.release_url": release_json["html_url"],
            "deployment_targets": [],
        }

def _get_release_data_of_model_or_raise(repository: str, headers: dict[str, str], version: str) -> dict[str, Any]:
    release_request = requests.get(
    f"https://api.github.com/repos/{repository}/releases/tags/{version}",
    headers=headers,
)

    if release_request.status_code != 200:
        raise ValueError(
            f"Failed to fetch {version} release from {repository}: {release_request.status_code}"
        )

    return release_request.json()


def _format_telemetry_of_deployment_target(
    root_spec: str,
    deployment_target: str,
    deployment_folder_path: Path,
    metadata_folder_path: Path,
) -> dict[str, Any]:
    with open(
        deployment_folder_path / f"deploy-{root_spec}-outputs.{deployment_target}", "r"
    ) as outputs_file:
        # Load relevant json files
        outputs = json.load(outputs_file)

        # TODO: Factor out _format_telemetry_of_model_components
        return {
            "deployment_target.name": deployment_target,
            "deployment_target.spack_version": outputs["spack_version"],
            "deployment_target.spack_git_hash": outputs["spack_git_hash"],
            "deployment_target.spack_config_version": outputs["spack_config_version"],
            "deployment_target.spack_config_git_hash": outputs["spack_config_git_hash"],
            "deployment_target.builtin_spack_packages_version": outputs["builtin_spack_packages_version"],
            "deployment_target.builtin_spack_packages_git_hash": outputs["builtin_spack_packages_git_hash"],
            "deployment_target.access_spack_packages_version": outputs["access_spack_packages_version"],
            "deployment_target.access_spack_packages_git_hash": outputs["access_spack_packages_git_hash"],
            "deployment_target.module_use_location": outputs["deployment_modules_location"],

            "spack_model.name": root_spec,
            "spack_model.spack_package_hash": outputs["root_spec_pkg_hash"],
            "spack_model.module_load_command": f"{root_spec}/{outputs['release_deployment_version']}",
            "spack_model_components": _format_telemetry_of_model_components(
                deployment_target, metadata_folder_path
            ),
        }


def _format_telemetry_of_model_components(
    deployment_target: str, metadata_folder_path: Path
) -> list[dict[str, str]]:
    model_components_telemetry: list[dict[str, str]] = []

    build_database_packages_filename = f"{deployment_target}.build-db-pkgs.json"
    with open(
        metadata_folder_path / build_database_packages_filename, "r"
    ) as outputs_file:
        # Load relevant json files
        outputs: list[dict[str, Any]] = json.load(outputs_file)

        if any("error" in component for component in outputs):
            raise ValueError(
                f"Errors found in model components metadata for deployment target {deployment_target}. Check {build_database_packages_filename}, fix and manually upload."
            )

        for component in outputs:
            version = get_ref_from_spack_spec_version_or_raise(component["version"])

            model_components_telemetry.append(
                {
                    "name": component["name"],
                    "spack_package_hash": component["hash"],
                    "version": version,
                    "install_location": component["location"],
                    "repository_url": component["url"],
                    "md5s": component["md5s"]
                }
            )

    return model_components_telemetry

def get_ref_from_spack_spec_version_or_raise(spec_version: str) -> str:
    """
    Extracts the git ref from a Spack spec version string.
    Args:
        spec_version (str): The Spack spec version string.
    Returns:
        str: The extracted git ref.
    Raises:
        ValueError: If the spec version string is invalid.
    """
    groups_regex=r'^(?:git\.)?(?P<ref>[^=+~ ]+)'

    match = re.search(groups_regex, spec_version)
    if not match:
        raise ValueError(f"Invalid spec version: {spec_version}")

    return match.group("ref")

def validate_deployment_information_against_schema(
    deployment_information: dict[str, Any]
) -> None:
    """
    Validates the deployment information against the JSON schema.

    Args:
        deployment_information (dict[str, Any]): The deployment information to validate.

    Raises:
        jsonschema.exceptions.ValidationError: If the deployment information does not conform to the schema.
        jsonschema.exceptions.SchemaError: If the schema is invalid.
        ValueError: If the schema cannot be fetched from the URL.
    """
    schema_request = requests.get(TRACKING_SERVICES_JSON_SCHEMA_URL)
    if schema_request.status_code != 200:
        raise ValueError(
            f"Failed to fetch schema from {TRACKING_SERVICES_JSON_SCHEMA_URL}: {schema_request.status_code}"
        )

    try:
        jsonschema.validate(
            instance=deployment_information, schema=schema_request.json()
        )
    except jsonschema.ValidationError as e:
        raise ValueError(f"Deployment information does not conform to the schema: {e}")
    except jsonschema.SchemaError as e:
        raise ValueError(f"Schema is invalid: {e}")


def post_tracking_services_blob_or_raise(tracking_services_json_blob: dict[str, Any]):
    if "TRACKING_SERVICES_POST_URL" not in os.environ or "TRACKING_SERVICES_POST_TOKEN" not in os.environ:
        raise ValueError(
            "Environment variables TRACKING_SERVICES_POST_URL and TRACKING_SERVICES_POST_TOKEN must be set to upload to Tracking Services."
        )

    # Get variables and secrets from environ
    ts_url = os.environ["TRACKING_SERVICES_POST_URL"] + "/api/release-provenance/ingest_raw/"
    ts_token = os.environ["TRACKING_SERVICES_POST_TOKEN"]

    # Prepare the data to be sent to the Tracking Services API
    telemetry_request_headers = {
        "Content-type": "application/json",
        "Authorization": "Token " + ts_token,
    }

    telemetry_response = requests.post(
        ts_url,
        headers=telemetry_request_headers,
        data=json.dumps(tracking_services_json_blob),
    )

    if telemetry_response.status_code != 201:
        raise ValueError(
            f"Failed to post telemetry to Tracking Services: {telemetry_response.status_code}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Script for generating and posting deployment information to tracking services release provenance database."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--repository",
        type=str,
        required=True,
        help="Repository name of the model deployment repository",
    )

    parser.add_argument(
        "--root-spec",
        type=str,
        required=True,
        help="Name of the root spec of the model deployment",
    )

    parser.add_argument(
        "--deployment-outputs",
        type=str,
        required=True,
        help="Path to folder containing deploy-*-outputs.* files",
    )
    parser.add_argument(
        "--metadata-outputs",
        type=str,
        required=True,
        help="Path to folder containing metadata-*-outputs.* files",
    )

    ## Args dealing with optional outputs or uploads
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload the tracking services JSON to the tracking services release provenance database",
    )
    parser.add_argument(
        "--output", type=str, help="Path to output the tracking services JSON"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    tracking_services_json_blob = format_deployment_information(
        repository=args.repository,
        root_spec=args.root_spec,
        deployment_folder_path=Path(args.deployment_outputs),
        metadata_folder_path=Path(args.metadata_outputs),
    )

    if args.output:
        with open(args.output, "w") as output_file:
            json.dump(tracking_services_json_blob, output_file, indent=2)

    if args.upload:
        post_tracking_services_blob_or_raise(tracking_services_json_blob)


if __name__ == "__main__":
    main()
