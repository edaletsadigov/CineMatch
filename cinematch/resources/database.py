from dagster import ConfigurableResource
from sqlalchemy import Engine

from notebooks.common import get_engine


class PostgresResource(ConfigurableResource):

    def get_connection(self) -> Engine:
        return get_engine()