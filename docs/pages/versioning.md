This library adheres to Semantic Versioning (Semver) principles to ensure predictable versioning and compatibility for
its users. 

* Semver consists of three distinct version components: MAJOR, MINOR, and PATCH, separated by dots (e.g.,
1.2.3). 
* Changes in the MAJOR version indicate backward-incompatible changes, such as breaking API alterations. 
* MINOR version updates signify new, backward-compatible features or enhancements, while PATCH versions are reserved for
backward-compatible bug fixes. 
* Releases with a MAJOR version of 0 are considered pre-release and as such, the api is considered unstable.
  Minor-version releases may contain breaking changes as the api evolves.
* The following is considered public API
  * Direct exports of the `wireup` package.
  * Accessible objects from the public interface of the above exported objects.


!!! tip
    When using a pre-release version, pin the constraint to `0.x.*` so that you don't accidentally upgrade to a version
    with breaking changes, but are still able to get bug-fix releases.
