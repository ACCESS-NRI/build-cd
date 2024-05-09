import os
from sqlalchemy import (
    DateTime, Text, String, Column, ForeignKey )
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

def create_session():
    connection = os.getenv("BUILD_DB_CONNECTION_STR")
    if connection is None:
        raise Exception("No BUILD_DB_CONNECTION_STR found, check model repository secrets")

    engine = create_engine(connection)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine, autoflush=False)
    return Session()


class ComponentBuild(Base):
    __tablename__ = "component_build"

    spack_hash = Column(String, primary_key=True, index=True)
    spec = Column(String, nullable=False)
    install_path = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
    release_url = Column(Text, nullable=False)
    model_build = Column(String, ForeignKey("model_build.spack_hash"))



class ModelBuild(Base):
    __tablename__ = "model_build"

    spack_hash = Column(String, primary_key=True, index=True)
    spec = Column(String, nullable=False)
    spack_version = Column(String, ForeignKey("spack_version.commit"))
    component_build = relationship('ComponentBuild')


class SpackVersion(Base):
    __tablename__ = "spack_version"

    commit = Column(String, primary_key=True, index=True)
    version = Column(String, nullable=False)
    model_build = relationship('ModelBuild')
