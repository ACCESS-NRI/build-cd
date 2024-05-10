from models import *
import json
import sys

session = create_session()


def read_release_data(filename):
    with open(filename) as release_data:
       return json.load(release_data)

def get_component_build(release_data):
    component_build_data = release_data["component_build"]
    component_build = session.query(ComponentBuild).get(component_build_data["spack_hash"])

    if component_build == None:
        component_build = ComponentBuild()
        component_build.created_at = component_build_data["created_at"]
        component_build.install_path = component_build_data["install_path"]
        component_build.spack_hash = component_build_data["spack_hash"]
        component_build.spec = component_build_data["spec"]
        component_build.release_url = component_build_data["release_url"]
    
    component_build.model_build.append(get_model_build(release_data["model_build"]))
    return component_build

def get_model_build(model_build_data):
    model_build = session.query(ModelBuild).get(model_build_data["spack_hash"])

    if model_build == None:
        model_build = ModelBuild()
        model_build.spack_version = get_spack_version(model_build_data["spack_version"])
        model_build.spack_hash = model_build_data["spack_hash"]
        model_build.spec = model_build_data["spec"]
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
    component_build = get_component_build(release_data)
    try:
        session.add(component_build)
        session.commit()
        print("release data added successfully")

    except:
        session.rollback()
        raise

    finally:
        session.close()



if __name__ == "__main__":
    main()