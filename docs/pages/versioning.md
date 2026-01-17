# Versioning Policy

Wireup follows [Semantic Versioning](https://semver.org/) (SemVer) to provide clear expectations about version
compatibility.

## Version Numbers

Each version number follows the format `MAJOR.MINOR.PATCH`:

- **MAJOR**: Increments for backward-incompatible changes
- **MINOR**: Increments for new features (backward-compatible)
- **PATCH**: Increments for bug fixes (backward-compatible)

## Pre-release Versions (0.x.x)

Versions starting with `0` (e.g., `0.1.0`) are considered pre-release. During this phase:

- The API is considered unstable
- Minor version updates may include breaking changes
- Use version constraint `0.x.*` to receive bug fixes while avoiding breaking changes

## Public API Definition

The following components constitute Wireup's public API:

1. All direct exports from the `wireup` package
1. All public members and interfaces of the exported objects

Changes to these components are subject to semantic versioning rules.
