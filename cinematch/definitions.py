from dagster import Definitions

from cinematch.defs.health_check import cinematch_health_check
from cinematch.defs.postgres_health_check import postgres_health_check
from cinematch.resources.database import PostgresResource


defs = Definitions(
    assets=[
        cinematch_health_check,
        postgres_health_check,
    ],
    resources={
        "postgres": PostgresResource(),
    },
)