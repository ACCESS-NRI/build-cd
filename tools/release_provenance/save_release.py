from models import *
import json
import sys

session = create_session()


def read_release_data(filename):
    with open(filename) as release_data:
       return json.load(release_data)

def get_component_build(component_build_data_list, model_build):
    component_build_list = []
    for component_build_data in component_build_data_list:
        component_build = session.query(ComponentBuild).get(component_build_data["spack_hash"])

        if component_build == None:
            component_build = ComponentBuild()
            component_build.install_path = component_build_data["install_path"]
            component_build.spack_hash = component_build_data["spack_hash"]
            component_build.spec = component_build_data["spec"]
            component_build.model_build.append(model_build)
            component_build_list.append(component_build)
        else:
            component_build.model_build.append(model_build)
    session.add_all(component_build_list)

    return component_build_list

def get_model_build(model_build_data):
    model_build = session.query(ModelBuild).get(model_build_data["spack_hash"])

    if model_build == None:
        model_build = ModelBuild()
        model_build.spack_version = get_spack_version(model_build_data["spack_version"])
        model_build.spack_config = model_build_data["spack_config"]
        model_build.spack_package = model_build_data["spack_package"]
        model_build.spack_hash = model_build_data["spack_hash"]
        model_build.spec = model_build_data["spec"]
        model_build.release_url = model_build_data["release_url"]
        model_build.created_at = model_build_data["created_at"]
        session.add(model_build)

    return model_build

def get_spack_version(spack_version_data):
    spack_version = session.query(SpackVersion).get(spack_version_data["commit"])
    if  spack_version == None:
        spack_version = SpackVersion()
        spack_version.commit = spack_version_data["commit"]
        spack_version.version = spack_version_data["version"]
        session.add(spack_version)

    return spack_version.commit

def main():
    release_data_filename = sys.argv[1]
    release_data = read_release_data(release_data_filename)
    model_build = get_model_build(release_data["model_build"])
    get_component_build(release_data["component_build"], model_build)
    try:
        session.commit()
        print("release data added successfully")

    except:
        session.rollback()
        raise

    finally:
        session.close()



if __name__ == "__main__":
    main()