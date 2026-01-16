from typing import Any

# For sequences of reserved definitions, we keep it in the flow-style format (i.e., [a, b, c]) rather than block style
# as it is more compact for reserved definitions.
class YamlExplicitFlowStyleSequence(list[str]):
    pass

def yaml_explicit_flow_style_sequence_representer(dumper, data):
    """
    Custom representer for YAML to ensure that some sequences are represented in flow style.
    This is necessary for sequences that are used as definitions in spack manifests.
    """
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


# PyYaml by default dumps unquoted strings if they look unambiguous, and quoted strings otherwise.
# PyYaml dumps '{name}/prX-Y' as a quoted str as it has '{' at the front and causes ambiguity
# But 'ROOT_SPEC/.dependencies/prX-Y/VERSION-{hash:7}' is dumped as an unquoted str as it is unambiguous
# So we need to wrap projections in a custom class that forces PyYaml to dump them as quoted strings.
class YamlExplicitQuotedString(str):
    pass

def yaml_explicit_quoted_string_representer(dumper, data):
    """
    Custom representer for YAML to ensure that some strings are quoted explicitly.
    This is necessary for strings that are used as projections in spack manifests.
    """
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")

# Custom logic to enforce explicit flow-style sequences for `spack.definitions` that are reserved definitions
def enforce_explicit_flow_style_definitions(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure that the 'definitions' section of the manifest is represented in flow style.
    This is necessary for spack manifests to ensure that definitions are correctly interpreted.
    """
    if "spack" in manifest and "definitions" in manifest["spack"]:
        definitions: list[dict[str, Any]] = manifest["spack"]["definitions"]
        for i in range(len(definitions)):
            definition = definitions[i]
            if len(definition) > 0:
                reserved_definition, reserved_value_list = list(definition.items())[0]

                if reserved_definition.startswith("_"):
                    manifest["spack"]["definitions"][i][reserved_definition] = YamlExplicitFlowStyleSequence(reserved_value_list)

    return manifest
