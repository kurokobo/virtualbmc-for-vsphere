<!-- omit in toc -->
# VirtualBMC for vSphere (vbmc4vsphere)

[![Downloads](https://pepy.tech/badge/vbmc4vsphere)](https://pepy.tech/project/vbmc4vsphere)

⚠️ ***IMPORTANT UPDATES*** ⚠️

***Since `0.1.0`, the commands have been renamed to `vsbmc` and `vsbmcd` to allow coexistence with the original VirtualBMC. Also, the path to the configuration files has been changed.***

***To migrate your old configuration files, please refer to [the migration guide on the GitHub Wiki page](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Migrate-configuration-files-from-0.0.8-or-earlier-to-0.1.0-or-later).***

<!-- omit in toc -->
## Table of Contents

- [Overview](#overview)
  - [Disclaimer](#disclaimer)
  - [Installation](#installation)
  - [vSphere Permissions](#vsphere-permissions)
  - [Supported IPMI commands](#supported-ipmi-commands)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Installation](#installation-1)
  - [Start Daemon](#start-daemon)
  - [Configure VirtualBMC](#configure-virtualbmc)
  - [Server Simulation](#server-simulation)
- [Tips](#tips)
  - [Optional configuration file](#optional-configuration-file)
  - [Manage stored data manually](#manage-stored-data-manually)
  - [Use in large-scale vSphere deployments](#use-in-large-scale-vsphere-deployments)
  - [Use with Nested-ESXi and vCenter Server](#use-with-nested-esxi-and-vcenter-server)
  - [Use with Nested-KVM and oVirt](#use-with-nested-kvm-and-ovirt)
  - [Use with OpenShift Bare Metal IPI](#use-with-openshift-bare-metal-ipi)
- [Reference resources](#reference-resources)

## Overview

A virtual BMC for controlling virtual machines using IPMI commands for the VMware vSphere environment.

In other words, this is the VMware vSphere version of [VirtualBMC](https://github.com/openstack/virtualbmc) part of the OpenStack project.

**This can be used as a BMC of Nested-ESXi**, therefore **you can make the vSphere DPM work in your nested environment** for testing purpose.

![Demo](https://user-images.githubusercontent.com/2920259/91665870-a7d78400-eb33-11ea-8d5b-33d98b3fe107.gif)

See:

- 📖[The guide to use with Nested-ESXi and vCenter Server](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Use-with-Nested-ESXi-and-vCenter-Server).
- 📖[The guide to use with Nested-KVM and oVirt](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Use-with-Nested-KVM-and-oVirt).
- 📖[The guide to use with OpenShift Bare Metal IPI](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Install-OpenShift-in-vSphere-environment-using-the-Baremetal-IPI-procedure).

### Disclaimer

- For testing purposes only. Not for production use.
- The vCenter Server credentials including password are stored in plain text.
- The vSphere DPM can be enabled with VirtualBMC for vSphere, but be careful with the recommendations presented in the vSphere DPM in nested environments may not be accurate or meet expectations. [See the wiki page for detail](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Use-with-Nested-ESXi-and-vCenter-Server#notice).

### Installation

```bash
python -m pip install vbmc4vsphere
```

If you want to run VirtualBMC for vSphere in Docker container, [see the guide on wiki page](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Containerized-VirtualBMC-for-vSphere).

### vSphere Permissions

The following are the minimum permissions needed on vSphere for VirtualBMC for vSphere (queried using [govc](https://github.com/vmware/govmomi/tree/master/govc)).

```text
VirtualMachine.Config.Settings
VirtualMachine.Interact.PowerOff
VirtualMachine.Interact.PowerOn
VirtualMachine.Interact.Reset
Global.Diagnostics
```

### Supported IPMI commands

```bash
# Power the virtual machine on, off, graceful off, reset, and NMI.
# Note that NMI is currently experimental.
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 power on|off|soft|reset|diag

# Check the power status.
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 power status

# Set the boot device to network, disk or cdrom.
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 chassis bootdev pxe|disk|cdrom

# Get the current boot device.
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 chassis bootparam get 5

# Get the channel info. Note that its output is always a dummy, not actual information.
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 channel info

# Get the network info. Note that its output is always a dummy, not actual information.
ipmitool -I lanplus -U admin -P password -H 192.168.0.1 -p 6230 lan print 1
```

- Experimental support: `power diag`
  - The command returns a response immediately, but the virtual machine receives NMI **60 seconds later**. This depends on the behavior of `debug-hung-vm` on the ESXi.

## Architecture

![Architecture](https://user-images.githubusercontent.com/2920259/91664084-c20b6500-eb27-11ea-8633-cc49ad6677d2.png)

## Quick Start

Install VirtualBMC for vSphere on some linux host, start `vsbmcd` daemon, and then configure through `vsbmc` command.

### Installation

```bash
python -m pip install vbmc4vsphere
```

### Start Daemon

- Start daemon:

  ```bash
  vsbmcd
  ```

  By default, daemon starts in background. You can start it in foreground by `--foreground` option to get logs.

  ```bash
  vsbmcd --foreground
  ```

### Configure VirtualBMC

- In order to see all command options supported by the `vsbmc` tool do:

  ```bash
  vsbmc --help
  ```

  It’s also possible to list the options from a specific command. For example, in order to know what can be provided as part of the `add` command do:

  ```bash
  vsbmc add --help
  ```

- Adding a new virtual BMC to control VM called lab-vesxi01:

  ```bash
  vsbmc add lab-vesxi01 --port 6230 --viserver 192.168.0.1 --viserver-username vsbmc@vsphere.local --viserver-password my-secure-password
  ```

  - Binding a network port number below 1025 is restricted and only users with privilege will be able to start a virtual BMC on those ports.
  - Passing the credential for your vCenter Server is required.
  - By default, IPMI credential is configured as `admin` and `password`. You can specify your own username and password by `--username` and `--password` at this time.

- Adding a additional virtual BMC to control VM called lab-vesxi02:

  ```bash
  vsbmc add lab-vesxi02 --port 6231 --viserver 192.168.0.1 --viserver-username vsbmc@vsphere.local --viserver-password my-secure-password
  ```

  - Specify a different port for each virtual machine.
- Starting the virtual BMC to control VMs:

  ```bash
  vsbmc start lab-vesxi01
  vsbmc start lab-vesxi02
  ```

- Getting the list of virtual BMCs including their VM name and IPMI network endpoints they are reachable at:

  ```bash
  $ vsbmc list
  +-------------+---------+---------+------+
  | VM name     | Status  | Address | Port |
  +-------------+---------+---------+------+
  | lab-vesxi01 | running | ::      | 6230 |
  | lab-vesxi02 | running | ::      | 6231 |
  +-------------+---------+---------+------+
  ```

- To view configuration information for a specific virtual BMC:

  ```bash
  $ vsbmc show lab-vesxi01
  +-------------------+---------------------+
  | Property          | Value               |
  +-------------------+---------------------+
  | active            | False               |
  | address           | ::                  |
  | password          | ***                 |
  | port              | 6230                |
  | status            | running             |
  | username          | admin               |
  | viserver          | 192.168.0.1         |
  | viserver_password | ***                 |
  | viserver_username | vsbmc@vsphere.local |
  | vm_name           | lab-vesxi01         |
  | vm_uuid           | None                |
  +-------------------+---------------------+
  ```

- Stopping the virtual BMC:

  ```bash
  vsbmc stop lab-vesxi01
  vsbmc stop lab-vesxi02
  ```

### Server Simulation

Once the virtual BMC for a specific VM has been created and started you can then issue IPMI commands against the address and port of that virtual BMC to control the VM.

In this example, if your VirtualBMC host has `192.168.0.100`, you can control:

- `lab-vesxi01` through `192.168.0.100:6230`
- `lab-vesxi02` through `192.168.0.100:6231`

by using IPMI. For example:

- To power on the virtual machine `lab-vesxi01`:

  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6230 -U admin -P password chassis power on
  Chassis Power Control: Up/On
  ```

- To check its power status:

  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6230 -U admin -P password chassis power status
  Chassis Power is on
  ```

- To shutdown `lab-vesxi01`:

  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6230 -U admin -P password chassis power soft
  Chassis Power Control: Soft
  ```

- To reset the `lab-vesxi02`:

  ```bash
  $ ipmitool -I lanplus -H 192.168.0.100 -p 6231 -U admin -P password chassis power reset
  Chassis Power Control: Reset
  ```

## Tips

### Optional configuration file

Both `vsbmcd` and `vsbmc` can make use of an optional configuration file, which is looked for in the following locations (in this order):

- `VBMC4VSPHERE_CONFIG` environment variable pointing to a file
- `$HOME/.vsbmc/vbmc4vsphere.conf` file
- `/etc/vbmc4vsphere/vbmc4vsphere.conf` file

If no configuration file has been found, the internal defaults apply.

The configuration files are not created automatically unless you create them manually. And even if you don't create a configuration file, it won't matter in most cases.

Below is a sample of `vbmc4vsphere.conf`.

```bash
[default]
#show_passwords = false
config_dir = /home/vsbmc/.vsbmc
#pid_file = /home/vsbmc/.vsbmc/master.pid
#server_port = 50891
#server_response_timeout = 5000
#server_spawn_wait = 3000

[log]
# logfile = /home/vsbmc/.vsbmc/log/vbmc4vsphere.log
debug = true 

[ipmi]
session_timeout = 10
```

### Manage stored data manually

Once you invoke `vsbmc add` command, everything that you specified will be stored as `config` file per virtual machine under `$HOME/.vsbmc/` by default. There files can be used backup/restoration, migration, and of course can be managed by any kind of configuration management tools. Please note **everything including password stored in plain text** in these `config` file.

The path for these files can be changed by `config_dir` in your `vbmc4vsphere.conf` described above.

```bash
$ cat ~/.vsbmc/lab-vesxi01/config
[VirtualBMC]
username = admin
password = password
address = ::
port = 6230
vm_name = lab-vesxi01
vm_uuid = 903a0dfb-68d1-4d2e-9674-10e353a733ca
viserver = 192.168.0.1
viserver_username = vsbmc@vsphere.local
viserver_password = my-secure-password
active = True
```

### Use in large-scale vSphere deployments

You can use UUID instead of name to identify virtual machine by specifying `--vm-uuid` option in `vsbmc add` command. This makes response time for IPMI command faster in large-scale vSphere deployments with a large number of virtual machines.

```bash
vsbmc add lab-vesxi01 \
  --vm-uuid 903a0dfb-68d1-4d2e-9674-10e353a733ca \
  --port 6230 \
  --viserver 192.168.0.1 \
  --viserver-username vsbmc@vsphere.local \
  --viserver-password my-secure-password
```

The UUID for virtual machines can be gathered in various ways like [govc](https://github.com/vmware/govmomi/tree/master/govc) and [PowerCLI](https://developer.vmware.com/powercli).

```bash
# Get UUID by govc
$ govc vm.info lab-vesxi01
Name:           lab-vesxi01
  ...
  UUID:         903a0dfb-68d1-4d2e-9674-10e353a733ca
  ...
```

```powershell
# Get UUID by PowerCLI
> (Get-VM lab-vesxi01).ExtensionData.Config.Uuid
903a0dfb-68d1-4d2e-9674-10e353a733ca
```

### Use with Nested-ESXi and vCenter Server

In the vCenter Server, by using VirtualBMC for vSphere (`0.0.3` or later), **you can enable the vSphere DPM: Distributed Power Management feature** for Nested-ESXi host that is running in your VMware vSphere environment.

So you can achieve:

- Power-On the virtual ESXi in the same way as for physical ESXi.
- Automated power on/off control of ESXi hosts based on the load of the host cluster by vCenter Server.

See 📖[the guide on GitHub Wiki page to use with Nested-ESXi and vCenter Server](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Use-with-Nested-ESXi-and-vCenter-Server).

### Use with Nested-KVM and oVirt

In the oVirt, by using VirtualBMC for vSphere, you can enable the Power Management feature for Nested-KVM that is running in your vSphere environment.

See 📖[the guide on GitHub Wiki page to use with Nested-KVM and oVirt](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Use-with-Nested-KVM-and-oVirt).

### Use with OpenShift Bare Metal IPI

With VirtualBMC for vSphere, you can control your virtual machines in the same way as a physical server. This means that tasks that require a physical BMC can be done in a virtual environment.

One such example is the provisioning of a physical server.

Here's how to automatically provision OpenShift to a physical server, called Bare Metal IPI, using a virtual machine in vSphere environment with VirtualBMC for vSphere.

See 📖[the guide to GitHub Wiki page to use with OpenShift Bare Metal IPI](https://github.com/kurokobo/virtualbmc-for-vsphere/wiki/Install-OpenShift-in-vSphere-environment-using-the-Baremetal-IPI-procedure).

## Reference resources

This project is started based on the copy of [VirtualBMC 2.1.0.dev](https://github.com/openstack/virtualbmc/commit/c4c8edb66bc49fcb1b8fb41af77546e06d2e8bce) and customized to support the VMware vSphere environment instead of the OpenStack.

- Original VirtualBMC documentation (for OpenStack): <https://docs.openstack.org/virtualbmc/latest>
- Its source: <https://opendev.org/openstack/virtualbmc>
