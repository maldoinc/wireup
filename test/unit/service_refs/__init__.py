from test.unit.services.with_annotations.env import EnvService

# This serves here as part of a test to check that when the same name is imported from multiple locations,
# it does not result in duplicate registration.
# See test: test_container_deduplicates_services_from_multiple_modules
# See: https://github.com/maldoinc/wireup/issues/61
__all__ = ["EnvService"]
