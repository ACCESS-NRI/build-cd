import os
from sqlalchemy import (
    DateTime, Text, String, Column, ForeignKey, Table, UniqueConstraint, Integer )
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

def create_session():
    # A connection string in postgresql:// style, for example: postgresql://user:pass@host/DB_NAME
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
    model_build = relationship('ModelBuild', secondary="model_component", back_populates='component_build')

class ModelBuild(Base):
    __tablename__ = "model_build"

    spack_hash = Column(String, primary_key=True, index=True)
    spec = Column(String, nullable=False)
    spack_version = Column(String, ForeignKey("spack_version.commit"))
    created_at = Column(DateTime, nullable=False)
    release_url = Column(Text, nullable=False, unique=True)
    component_build = relationship('ComponentBuild', secondary="model_component", back_populates='model_build')

class SpackVersion(Base):
    __tablename__ = "spack_version"

    commit = Column(String, primary_key=True, index=True)
    version = Column(String, nullable=False)
    model_build = relationship('ModelBuild')


model_component_association = Table(
    "model_component",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("model_build", ForeignKey(ModelBuild.spack_hash)),
    Column("component_build", ForeignKey(ComponentBuild.spack_hash)),
    UniqueConstraint('model_build', 'component_build', name='uix_1')
)
