from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from shared.database.base import Base
from shared.database.config import DatabaseConfig


def create_engine_from_config(config: DatabaseConfig) -> Engine:
	return create_engine(
		config.url,
		echo=config.echo,
		pool_pre_ping=config.pool_pre_ping,
	)


def create_session_factory_for_engine(engine: Engine) -> sessionmaker[Session]:
	return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_session_factory(config: DatabaseConfig) -> sessionmaker[Session]:
	engine = create_engine_from_config(config)
	return create_session_factory_for_engine(engine)


def create_all_tables(engine: Engine) -> None:
	Base.metadata.create_all(bind=engine)
