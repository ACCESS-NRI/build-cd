import argparse
import re
import sys
import yaml

# Essentially we are looking to do the following substitutions in yq:
# yq -i '.modules.use += ["/g/data/vk83/prerelease/modules"]' config.yaml
# yq -i '.modules.load |= map(sub("^${{ needs.setup.outputs.root-sbd }}/.*"; "${{ env.DEPLOYMENT_IDENTIFIER }}"))' config.yaml
# yq -i '.manifest.reproduce.exe=false' config.yaml

def update_model_config_manifest(
    manifest: dict[str, any],
    deployment_target: str,
    root_sbd: str,
    module: str
) -> dict[str, any]:
    updated_manifest = update_modules_use_section(
        manifest, deployment_target
    )

    updated_manifest = update_modules_load_section(
        updated_manifest, root_sbd, module
    )

    updated_manifest = update_reproduce_exe_section(
        updated_manifest
    )

    return updated_manifest

def update_modules_use_section(
    manifest: dict[str, any],
    deployment_target: str
) -> dict[str, any]:
    """
    Updates the modules.use section of the model config manifest to use the prerelease module path
    """
    manifest.setdefault("modules", {}).setdefault("use", [])

    modules_use: list[str] = manifest["modules"]["use"]

    match deployment_target:
        case "Gadi":
            prerelease_module_path = "/g/data/vk83/prerelease/modules"
        case _:
            raise ValueError(f"Unsupported deployment target: {deployment_target}")

    if prerelease_module_path not in modules_use:
        modules_use.append(prerelease_module_path)

    manifest["modules"]["use"] = modules_use

    return manifest

def update_modules_load_section(
    manifest: dict[str, any],
    root_sbd: str,
    prerelease_module: str
) -> dict[str, any]:
    """
    Updates the modules.load section of the model config manifest to use the prerelease module name
    """
    manifest.setdefault("modules", {}).setdefault("load", [])

    modules_load: list[str] = manifest["modules"]["load"]

    # We remove all entries that start with the root_sbd to avoid conflicts with the existing release modules in the config.yaml
    updated_modules_load = [prerelease_module] + [m for m in modules_load if not m.startswith(f"{root_sbd}/")]

    print(f"When updating modules.load, removed entries starting with '{root_sbd}' and added '{prerelease_module}' giving: {updated_modules_load}")

    manifest["modules"]["load"] = updated_modules_load

    return manifest

def update_reproduce_exe_section(
    manifest: dict[str, any]
) -> dict[str, any]:
    """
    Updates the manifest.reproduce.exe section of the model config manifest to be false for prerelease builds
    """
    manifest.setdefault("manifest", {}).setdefault("reproduce", {})

    manifest["manifest"]["reproduce"]["exe"] = False

    return manifest

def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script for updating model configuration repositories config.yaml to use prerelease builds."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Path to the spack manifest file to be injected with prerelease information",
    )

    parser.add_argument(
        "--deployment-target",
        type=str,
        required=True,
        help="Deployment target to be used for projections in the manifest",
    )

    parser.add_argument(
        "--root-sbd",
        type=str,
        required=True,
        help="Root Spack Bundle Definition to be used for module path updates",
    )

    parser.add_argument(
        "--module",
        type=str,
        required=True,
        help="Module name to be used for module load updates",
    )

    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    with open(args.manifest, "r") as f:
        manifest = yaml.safe_load(f)

    updated_manifest = update_model_config_manifest(
        manifest,
        args.deployment_target,
        args.root_sbd,
        args.module
    )

    with open(args.manifest, "w") as f:
        yaml.safe_dump(updated_manifest, f)


if __name__ == "__main__":
    main()
