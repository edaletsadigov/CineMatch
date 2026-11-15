
from dagster import asset
from sqlalchemy import text


@asset(required_resource_keys={"postgres"})
def postgres_health_check(context):

    engine = context.resources.postgres.get_connection()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()

        context.log.info(f"Database: {result[0]}")
        context.log.info(f"User: {result[1]}")

        return {
            "database": result[0],
            "user": result[1],
        }

    finally:
        engine.dispose()
