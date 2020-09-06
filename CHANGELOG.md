# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]
### Added
- N/A

## [0.0.4] - 2020-09-06
### Added
- Add docker support

## [0.0.3] - 2020-09-05
### Added
- Add "Get Channel Information" command support with faked response
- Add "Get Channel Access" command support with faked response
- Add "Get LAN Configuration Parameters" command with faked response
- Add ability to control fake MAC address to pass the sanity check of vCenter Server

## [0.0.2] - 2020-09-04
### Added
- Patch pyghmi to support `0x38` command in IPMI v2.0
- Add ASF Presence Ping/Pong support
- Add [CHANGELOG.md]

### Changed
- Refactor some codes
- Update [README.md]


## 0.0.1 - 2020-08-31
### Added
- Add VMware vSphere support with few IPMI commands and remove OpenStack support
- Project starts based on the copy of [VirtualBMC 2.1.0.dev](https://github.com/openstack/virtualbmc/commit/c4c8edb66bc49fcb1b8fb41af77546e06d2e8bce)


[Unreleased]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.4...HEAD
[0.0.4]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.3...0.0.4
[0.0.3]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.2...0.0.3
[0.0.2]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.1...0.0.2