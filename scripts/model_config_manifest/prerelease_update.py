import argparse
import configparser
import sys

import ruamel.yaml
from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

# Constants for deployment targets
GADI_MODULE_USE_PATH: str = "/g/data/vk83/prerelease/modules"

# Constants for default configuration files to edit
DEFAULT_PAYU_CONFIG_PATH: str = "config.yaml"
DEFAULT_ROSE_CYLC_CONFIG_PATH: str = "rose-suite.conf"

class ConfigUpdater(ABC):
    def __init__(self, config_path: str, deployment_target: str) -> None:
        self.config_path = Path(config_path)
        self.deployment_target = deployment_target

    @abstractmethod
    def update_modules_use_section(self) -> None:
        pass

    @abstractmethod
    def update_modules_load_section(
        self,
        root_sbd: str,
        prerelease_module: str
    ) -> None:
        pass

class PayuConfigUpdater(ConfigUpdater):
    def __init__(self, config_path: str, deployment_target: str) -> None:
        super().__init__(config_path, deployment_target)

        # Setting up the YAML parser...
        self.yaml=ruamel.yaml.YAML()
        # To cut down on large diffs, keep the original quoting of config.yaml
        self.yaml.preserve_quotes = True
        # Some files have 'foo: null' being updated to 'foo: ' - this will ensure that
        # original 'null' values are still represented as 'null'
        self.yaml.representer.add_representer(
            type(None), lambda self, _: self.represent_scalar("tag:yaml.org,2002:null", "null")
        )
        # Some extra-long values are being wrapped, which increases the diff size.
        # This ensures that wrapping only occurs at the extreme end of file width...
        self.yaml.width = 1000

    # Essentially we are looking to do the following substitutions in yq:
    ## For payu-based configurations:
    # yq -i '.modules.use += ["/g/data/vk83/prerelease/modules"]' config.yaml
    # yq -i '.modules.load |= map(sub("^${{ needs.setup.outputs.root-sbd }}/.*"; "${{ env.DEPLOYMENT_IDENTIFIER }}"))' config.yaml
    # yq -i '.manifest.reproduce.exe=false' config.yaml

    def update_modules_use_section(self) -> None:
        with open(self.config_path, "r") as cfg:
            manifest = self.yaml.load(cfg)

        manifest.setdefault("modules", {}).setdefault("use", [])

        modules_use: list[str] = manifest["modules"]["use"]

        match self.deployment_target:
            case "gadi":
                prerelease_module_path = "/g/data/vk83/prerelease/modules"
            case _:
                raise ValueError(f"Unsupported deployment target: {self.deployment_target}")

        if prerelease_module_path not in modules_use:
            modules_use.append(prerelease_module_path)

        manifest["modules"]["use"] = modules_use

        with open(self.config_path, "w") as cfg:
            self.yaml.dump(manifest, cfg)

    def update_modules_load_section(
        self,
        root_sbd: str,
        prerelease_module: str
    ) -> None:
        """
        Updates the modules.load section of the model config manifest to use the prerelease module name
        """
        with open(self.config_path, "r") as cfg:
            manifest = self.yaml.load(cfg)

        manifest.setdefault("modules", {}).setdefault("load", [])

        modules_load: list[str] = manifest["modules"]["load"]

        # We remove all entries that start with the root_sbd to avoid conflicts with the existing release modules in the config.yaml
        updated_modules_load = [prerelease_module] + [m for m in modules_load if not m.startswith(f"{root_sbd}/")]

        print(f"When updating modules.load, removed entries starting with '{root_sbd}' and added '{prerelease_module}' giving: {updated_modules_load}")

        manifest["modules"]["load"] = updated_modules_load

        with open(self.config_path, "w") as cfg:
            self.yaml.dump(manifest, cfg)

    def update_reproduce_exe_section(
        self,
    ) -> None:
        """
        Updates the manifest.reproduce.exe section of the model config manifest to be false for prerelease builds
        """
        with open(self.config_path, "r") as cfg:
            manifest = self.yaml.load(cfg)

        manifest.setdefault("manifest", {}).setdefault("reproduce", {})

        manifest["manifest"]["reproduce"]["exe"] = False

        with open(self.config_path, "w") as cfg:
            self.yaml.dump(manifest, cfg)


class RoseCylcConfigUpdater(ConfigUpdater):
    def __init__(self, config_path: str, deployment_target: str) -> None:
        self.config = configparser.ConfigParser()
        # Usually ConfigParser converts option keys via KEY.lower, but we want them unchanged,
        # hence we are returning the KEY unlowered.
        self.config.optionxform = lambda optionstr: optionstr

        super().__init__(config_path, deployment_target)

    ## For rose-cylc-based configurations:
    # SPACK_MODULE_USE=/g/data/vk83/prerelease/modules in rose-suite.conf
    # SPACK_BUILD=${{ needs.setup.outputs.root-sbd }}/${{ env.DEPLOYMENT_IDENTIFIER }}

    def update_modules_use_section(self) -> None:
        self.config.read(self.config_path)

        if not self.config.get("jinja2:suite.rc", "SPACK_MODULE_USE", fallback=None):
            raise Exception(f"Couldn't find a SPACK_MODULE_USE directive in {self.config_path}, can't update the configuration!")

        self.config.set("jinja2:suite.rc", "SPACK_MODULE_USE", f"'{GADI_MODULE_USE_PATH}'")

        with open(self.config_path, "w") as config_file:
            self.config.write(config_file, space_around_delimiters=False)

    def update_modules_load_section(self, root_sbd: str, prerelease_module: str) -> None:
        self.config.read(self.config_path)

        if root_sbd not in self.config.get("jinja2:suite.rc", "SPACK_BUILD", fallback=''):
            raise Exception(f"Couldn't find a SPACK_BUILD directive with {root_sbd} in {self.config_path}, can't update the configuration!")

        self.config.set("jinja2:suite.rc", "SPACK_BUILD", f"'{prerelease_module}'")

        with open(self.config_path, "w") as config_file:
            self.config.write(config_file, space_around_delimiters=False)

def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script for updating model configuration repositories configuration to use prerelease builds."
    )

    ## Args dealing with inputs
    parser.add_argument(
        "--workflow-manager",
        type=str,
        required=True,
        help="Workflow manager used to run the configurations"
    )

    parser.add_argument(
        "--deployment-target",
        type=str,
        required=True,
        help="Deployment HPC target to be used for the configurations",
    )

    parser.add_argument(
        "--root-sbd",
        type=str,
        required=True,
        help="Root Spack Bundle Definition for the model",
    )

    parser.add_argument(
        "--module",
        type=str,
        required=True,
        help="Module name to be used for module use updates",
    )

    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    match args.workflow_manager:
        case "payu":
            payu_updater = PayuConfigUpdater(DEFAULT_PAYU_CONFIG_PATH, args.deployment_target)
            payu_updater.update_modules_use_section()
            payu_updater.update_modules_load_section(args.root_sbd, args.module)
            payu_updater.update_reproduce_exe_section()
        case "rose-cylc":
            rose_cylc_updater = RoseCylcConfigUpdater(DEFAULT_ROSE_CYLC_CONFIG_PATH, args.deployment_target)
            rose_cylc_updater.update_modules_use_section()
            rose_cylc_updater.update_modules_load_section(args.root_sbd, args.module)
        case _:
            raise ValueError(f"Unsupported workflow manager: {args.workflow_manager}")


if __name__ == "__main__":
    main()
