# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

### Added

- N/A

## [0.3.0] - 2022-10-01

### Added

- Add `--vm-uuid` option to `vsbmc add` command to specify UUID for virtual machine without modifying config file (#17)

## [0.2.0] - 2022-10-01

### Added

- Add UUID lookup method via config file for VM search (#14)

### Changed

- Bump Python version to 3.10

## [0.1.0] - 2022-02-02

### Breaking Changes

- Rename commands to `vsbmc` and `vsbmcd` to allow coexistence with the original VirtualBMC (#9)

### Fixed

- Make the container image to run as non-root user (#11)

## [0.0.8] - 2021-09-15

### Fixed

- Failed to find VM in environments with more than 100 VMs (#5)

## [0.0.7] - 2021-03-27

### Fixed

- Failed to pickle `vbmc_runner` due to `multiprocessing` on Python 3.8+ on macOS (#2)

## [0.0.6] - 2020-09-11

### Added

- Add experimental support for `chassis power diag`

## [0.0.5] - 2020-09-09

### Added

- Add `chassis bootdev pxe|disk|cdrom` command support
- Add `chassis bootparam get 5` command support

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

[Unreleased]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.3.0...HEAD
[0.3.0]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.8...0.1.0
[0.0.8]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.7...0.0.8
[0.0.7]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.6...0.0.7
[0.0.6]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.5...0.0.6
[0.0.5]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.4...0.0.5
[0.0.4]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.3...0.0.4
[0.0.3]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.2...0.0.3
[0.0.2]: https://github.com/kurokobo/virtualbmc-for-vsphere/compare/0.0.1...0.0.2
