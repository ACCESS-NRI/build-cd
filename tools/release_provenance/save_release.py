from models import *
import json
import sys
from sqlalchemy.orm.exc import NoResultFound

def read_release_data(filename):
    with open(filename) as release_data:
       return json.load(release_data)
    
def get_component_build(release_data, session):
    component_build = ComponentBuild()
    component_build.model_build = get_model_build(release_data["model_build"], session)
    component_build.created_at = release_data["created_at"]
    component_build.install_path = release_data["install_path"]
    component_build.spack_hash = release_data["spack_hash"]
    component_build.spec = release_data["spec"]
    component_build.release_url = release_data["release_url"]
    return component_build

def get_model_build(model_build_data, session):
    try:
        model_build = session.query(ModelBuild).filter(
            ModelBuild.spack_hash == model_build_data["spack_hash"]
        ).one()
    except NoResultFound:
        model_build = ModelBuild()
        model_build.spack_version = get_spack_version(model_build_data["spack_version"], session)
        model_build.spack_hash = model_build_data["spack_hash"]
        model_build.spec = model_build_data["spec"]
        session.add(model_build)
        session.commit()
    
    return model_build.spack_hash

def get_spack_version(spack_version_data, session):
    try:
        spack_version = session.query(SpackVersion).filter(
            SpackVersion.commit == spack_version_data["commit"]
        ).one()
    except NoResultFound:
        spack_version = SpackVersion()
        spack_version.commit = spack_version_data["commit"]
        spack_version.version = spack_version_data["version"]
        session.add(spack_version)
        session.commit()
    
    return spack_version.commit

def main():
    session = create_session()
    release_data_filename = sys.argv[1]
    release_data = read_release_data(release_data_filename)
    component_build = get_component_build(release_data, session)
    try:
        session.add(component_build)
        session.commit()
        print("release data added sucessfully")
        
    except:
        session.rollback()
        raise

    finally:
        session.close()



if __name__ == "__main__":
    main()