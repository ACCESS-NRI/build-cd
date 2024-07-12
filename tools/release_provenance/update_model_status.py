import sys
from models import *

def update_model_status(model, status):
    try:
        session = create_session()
        model = session.query(ModelBuild).filter(ModelBuild.spack_hash == model).update({
            "status": status
        })
        session.commit()
        print("model status updated successfully")
    except Exception as e:
        print(e)
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    update_model_status(sys.argv[1], sys.argv[2])