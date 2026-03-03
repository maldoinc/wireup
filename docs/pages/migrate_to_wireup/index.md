# Migrate to Wireup

This section contains migration guides for teams moving to Wireup from other Python dependency-injection systems.

## FastAPI (from `Depends`)

This guide is for FastAPI users who want to migrate from `Depends(...)`-based service wiring to Wireup while keeping
FastAPI for routing, request parsing, and validation.

- [Migrate from FastAPI Depends](fastapi_depends.md)

## Dependency Injector

This guide is for Dependency Injector users who want to migrate provider-based wiring (`Singleton`, `Factory`,
`Resource`, `Provide[...]`) to Wireup injectables and lifetimes.

- [Migrate from Dependency Injector](dependency_injector.md)
