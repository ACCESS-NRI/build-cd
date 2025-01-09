import os
import json
import argparse
from typing import Any

from scripts.jinja_template.render import render_using_context


def _build_deployments_context_from_folder(
    deployment_outputs_folder: str,
) -> list[dict[str, Any]]:
    """
    Builds a list of deployment contexts from deployment output files in the specified folder.

    Args:
        deployment_outputs_folder (str): The path to the folder containing deployment output JSON files.

    Returns:
        list[dict[str, Any]]: A list of dictionaries, each containing deployment information extracted from the JSON files.
    """
    deployments: list[dict[str, Any]] = []

    for f in sorted(os.listdir(deployment_outputs_folder)):
        # f has the format 'deploy-outputs.DEPLOYMENT_TARGET'
        with open(os.path.join(deployment_outputs_folder, f), "r") as f_in:
            data = json.load(f_in)
            deployment = {
                "name": f.split(".")[1],
                "result": data["deployment_result"],
                "release_version": data["release_deployment_version"],
                "spack_version": data["spack_version"],
                "spack_config_version": data["spack_config_version"],
                "spack_packages_version": data["spack_packages_version"],
                "modules_location": data["deployment_modules_location"],
                "spack_location": data["deployment_spack_location"],
            }
            deployments.append(deployment)

    return deployments


def build_deployment_context(
    deployments_folder_path: str, template_prefix: str
) -> dict[str, Any]:
    """
    Builds a deployment context dictionary by extracting environment variables
    that start with a given prefix and combining them with deployment information
    from a specified folder.

    Args:
        deployments_folder_path (str): The path to the folder containing deployment information files.
        template_prefix (str): The prefix used to filter template environment variables.

    Returns:
        dict[str, Any]: A dictionary containing the combined deployment context.
    """
    template_variables = {
        k.removeprefix(template_prefix).lower(): v
        for k, v in os.environ.items()
        if k.startswith(template_prefix)
    }

    context: dict[str, Any] = {
        **template_variables,
        "deployments": _build_deployments_context_from_folder(deployments_folder_path),
    }

    print(context)

    return context


def parse_args():
    parser = argparse.ArgumentParser(
        description="Script for generating deployment-related rendered output"
    )
    parser.add_argument(
        "--template", type=str, required=True, help="Path to .j2 template"
    )
    parser.add_argument(
        "--template-var-prefix",
        type=str,
        default="J2_",
        help="Environment variables with this prefix will be added to the template context",
    )
    parser.add_argument(
        "--deployment-outputs",
        type=str,
        required=True,
        help="Path to folder containing deploy-outputs.* files",
    )
    parser.add_argument("--output", type=str, help="Path to output file")

    return parser.parse_args()


def main():
    args = parse_args()

    context = build_deployment_context(
        deployments_folder_path=args.deployment_outputs,
        template_prefix=args.template_var_prefix,
    )

    rendered_output = render_using_context(template_path=args.template, context=context)

    print(rendered_output)

    if args.output is not None:
        with open(args.output, "w") as f:
            f.write(rendered_output)


if __name__ == "__main__":
    main()
