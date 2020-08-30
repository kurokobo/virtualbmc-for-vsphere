# VirtualBMC for vSphere (vbmc4vsphere)


## Overview

A virtual BMC for controlling virtual machines using IPMI commands for the vSphere environment.

In other words, the vSphere version of [VirtualBMC](https://github.com/openstack/virtualbmc) part of the OpenStack project.

![Demo](https://user-images.githubusercontent.com/2920259/91665870-a7d78400-eb33-11ea-8d5b-33d98b3fe107.gif)


### Installation

```bash
pip install vbmc4vsphere
```

### Supported IPMI commands

```bash
# Power the virtual machine on, off, graceful off and reset
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 power on|off|soft|reset

# Check the power status
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 power status
```

Not Implemented yet:

* Inject NMI: `power diag`
* Set the boot device to network, hd or cdrom: `chassis bootdev pxe|disk|cdrom`
* Get the current boot device: `chassis bootparam get 5`


## Architecture

![Architecture](https://user-images.githubusercontent.com/2920259/91664084-c20b6500-eb27-11ea-8633-cc49ad6677d2.png)


## Quick Start

Install VirtualBMC for vSphere on some linux host, start `vbmcd` daemon, and then configure through `vbmc` command.


### Installation

```bash
pip install vbmc4vsphere
```


### Start Daemon

* Start daemon:
  ```bash
  $ vbmcd
  ```
  By default, daemon starts in background. You can start it in foreground by `--foreground` option to get logs.
  ```bash
  $ vbmcd --foreground
  ```


### Configure VirtualBMC

* In order to see all command options supported by the `vbmc` tool do:
  ```bash
  $ vbmc --help
  ```
  It’s also possible to list the options from a specific command. For example, in order to know what can be provided as part of the `add` command do:
  ```bash
  $ vbmc add --help
  ```
* Adding a new virtual BMC to control VM called lab-vesxi01:
  ```bash
  $ vbmc add lab-vesxi01 --port 6230 --viserver 192.168.0.1 --viserver-username vbmc@vsphere.local --viserver-password my-secure-password
  ```
  * Binding a network port number below 1025 is restricted and only users with privilege will be able to start a virtual BMC on those ports.
  * Passing the credential for your vCenter Server is required.
  * By default, IPMI credential is confugired as `admin` and `password`. You can specify your own username and password by `--username` and `--password` at this time.
* Adding a additional virtual BMC to control VM called lab-vesxi02:
  ```bash
  $ vbmc add lab-vesxi02 --port 6231 --viserver 192.168.0.1 --viserver-username vbmc@vsphere.local --viserver-password my-secure-password
  ```
  * Specify a different port for each virtual machine.
* Starting the virtual BMC to control VMs:
  ```bash
  $ vbmc start lab-vesxi01
  $ vbmc start lab-vesxi02
  ```
* Getting the list of virtual BMCs including their VM name and IPMI network endpoints they are reachable at:
  ```bash
  $ vbmc list
  +-------------+---------+---------+------+
  | VM name     | Status  | Address | Port |
  +-------------+---------+---------+------+
  | lab-vesxi01 | running | ::      | 6230 |
  | lab-vesxi02 | running | ::      | 6231 |
  +-------------+---------+---------+------+
* To view configuration information for a specific virtual BMC:
  ```bash
  $ vbmc show lab-vesxi01
  +-------------------+--------------------+
  | Property          | Value              |
  +-------------------+--------------------+
  | active            | False              |
  | address           | ::                 |
  | password          | ***                |
  | port              | 6230               |
  | status            | running            |
  | username          | admin              |
  | viserver          | 192.168.0.1        |
  | viserver_password | ***                |
  | viserver_username | vbmc@vsphere.local |
  | vm_name           | lab-vesxi01        |
  +-------------------+--------------------+
  ```
* Stopping the virtual BMC to control VMs:
  ```bash
  $ vbmc stop lab-vesxi01
  $ vbmc stop lab-vesxi02
  ```


### Server Simulation

Once the virtual BMC for a specific VM has been created and started you can then issue IPMI commands against the address and port of that virtual BMC to control the VM.

In this example, if your VirtualBMC host has `192.168.0.100`, you can controll:

* `lab-vesxi01` througth `192.168.0.100:2360`
* `lab-vesxi02` througth `192.168.0.100:2361`

by using IPMI. For example:

* To power on the virtual machine:
  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6230 -U admin -P password chassis power on
  Chassis Power Control: Up/On
  ```
* To check its power status:
  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6230 -U admin -P password chassis power status
  Chassis Power is on
  ```
* To shutdown the virtual machine:
  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6230 -U admin -P password chassis power soft
  Chassis Power Control: Soft
  ```


## Reference resources

This project is started based on the copy of [VirtualBMC 2.1.0.dev](https://github.com/openstack/virtualbmc/commit/c4c8edb66bc49fcb1b8fb41af77546e06d2e8bce) and customized to support the vSphere environment instead of the OpenStack. 

* Original VirtualBMC documentation (for OpenStack): https://docs.openstack.org/virtualbmc/latest
* Its source: https://opendev.org/openstack/virtualbmc