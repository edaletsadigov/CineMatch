from dagster import asset


@asset
def cinematch_health_check():
    return "CineMatch Dagster integration is working!"