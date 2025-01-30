import pytest
from pathlib import Path

from scripts.jinja_template.render_deployment_info import build_deployment_context, _build_deployments_context_from_folder

@pytest.fixture
def deployments_folder(request):
    return Path(request.path.parent) / "inputs"

@pytest.fixture(
    params=[
        [
            ("J2_MODEL", "model", "access-om2"),
            ("J2_VERSION","version", "pr12-2"),
            ("J2_ROOT_SBD","root_sbd","access-om2")
        ],
        [
            ("J2_MODEL", "model", "access-om2")
        ],
    ]
)
def env_vars(request, monkeypatch):
    for env_name, _, value in request.param:
        monkeypatch.setenv(env_name, value)

    yield request.param

def test_build_deployment_context__valid_envs(env_vars):
    context = build_deployment_context(
        template_prefix="J2_",
        deployments_folder_path="tests/scripts/jinja_template/inputs",
    )

    for env_name, key, value in env_vars:
        assert key in context, f"{key} (from {env_name}) does not exist in {context}"
        assert value == context[f"{key}"], f"{value} does not equal expected {context[f"{key}"]}"

def test_build_deployment_context__invalid_envs(env_vars):
    context = build_deployment_context(
        template_prefix="SOMETHING_",
        deployments_folder_path="tests/scripts/jinja_template/inputs"
    )

    assert len(context) == 1, "Environment variables were added with an incorrect template_prefix"


def test_build_deployments_context_from_folder(deployments_folder):
    context = _build_deployments_context_from_folder(deployments_folder)

    assert len(context) == 2

    assert context[0]["name"] == "Gadi"
    assert context[0]["result"] == "success"
    assert context[0]["release_version"] == "2024.11.16"
    assert context[0]["spack_version"] == "0.22"
    assert context[0]["spack_config_version"] == "2024.11.27"
    assert context[0]["spack_packages_version"] == "2024.09.20"
    assert context[0]["modules_location"] == "/g/data/vk83/prerelease/modules"
    assert context[0]["spack_location"] == "/g/data/vk83/prerelease/apps/spack/0.22/spack"

    assert context[1]["name"] == "Setonix"
    assert context[1]["result"] == "success"
    assert context[1]["release_version"] == "2024.11.16"
    assert context[1]["spack_version"] == "0.22"
    assert context[1]["spack_config_version"] == "2024.11.27"
    assert context[1]["spack_packages_version"] == "2024.09.20"
    assert context[1]["modules_location"] == "/some/dir/with/modules"
    assert context[1]["spack_location"] == "/some/apps/spack/0.22/spack"