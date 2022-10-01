#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import hashlib
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from threading import Thread

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from vbmc4vsphere import exception


class viserver_open(object):
    def __init__(self, vi, vi_username=None, vi_password=None, readonly=False):
        self.vi = vi
        self.vi_username = vi_username
        self.vi_password = vi_password
        self.readonly = readonly

    def __enter__(self):
        context = None
        if hasattr(ssl, "_create_unverified_context"):
            context = ssl._create_unverified_context()
        try:
            self.conn = SmartConnect(
                host=self.vi,
                user=self.vi_username,
                pwd=self.vi_password,
                # port=self.vi_port,
                sslContext=context,
            )
            if not self.conn:
                raise Exception
        except Exception as e:
            raise exception.VIServerConnectionOpenError(vi=self.vi, error=e)

        return self.conn

    def __exit__(self, type, value, traceback):
        _ = Disconnect(self.conn)


def get_obj_by_name(conn, root, vim_type, value):
    objs = []
    container = conn.content.viewManager.CreateContainerView(root, vim_type, True)
    for obj in container.view:
        if obj.name == value:
            objs.append(obj)
    container.Destroy()
    return objs


def get_viserver_vm_by_uuid(conn, uuid):
    try:
        search_index = conn.content.searchIndex
        vm = search_index.FindByUuid(None, uuid, True)

        if vm:
            return vm
        else:
            raise Exception

    except Exception:
        raise exception.VMNotFoundByUUID(uuid=uuid)


def get_viserver_vm(conn, vm):
    try:
        vms = get_obj_by_name(conn, conn.content.rootFolder, [vim.VirtualMachine], vm)

        if len(vms) != 1:
            raise Exception

        return vms[0]

    except Exception:
        raise exception.VMNotFound(vm=vm)


def get_bootable_device_type(conn, boot_dev):
    if isinstance(boot_dev, vim.vm.BootOptions.BootableFloppyDevice):
        return "floppy"
    elif isinstance(boot_dev, vim.vm.BootOptions.BootableDiskDevice):
        return "disk"
    elif isinstance(boot_dev, vim.vm.BootOptions.BootableCdromDevice):
        return "cdrom"
    elif isinstance(boot_dev, vim.vm.BootOptions.BootableEthernetDevice):
        return "ethernet"


def set_boot_device(conn, vm, device):
    """Set boot device to specified device.

    https://github.com/ansible-collections/vmware/blob/main/plugins/module_utils/vmware.py
    """

    boot_order_list = []
    if device == "cdrom":
        bootable_cdroms = [
            dev
            for dev in vm.config.hardware.device
            if isinstance(dev, vim.vm.device.VirtualCdrom)
        ]
        if bootable_cdroms:
            boot_order_list.append(vim.vm.BootOptions.BootableCdromDevice())
    elif device == "disk":
        bootable_disks = [
            dev
            for dev in vm.config.hardware.device
            if isinstance(dev, vim.vm.device.VirtualDisk)
        ]
        if bootable_disks:
            boot_order_list.extend(
                [
                    vim.vm.BootOptions.BootableDiskDevice(deviceKey=bootable_disk.key)
                    for bootable_disk in bootable_disks
                ]
            )
    elif device == "ethernet":
        bootable_ethernets = [
            dev
            for dev in vm.config.hardware.device
            if isinstance(dev, vim.vm.device.VirtualEthernetCard)
        ]
        if bootable_ethernets:
            boot_order_list.extend(
                [
                    vim.vm.BootOptions.BootableEthernetDevice(
                        deviceKey=bootable_ethernet.key
                    )
                    for bootable_ethernet in bootable_ethernets
                ]
            )
    elif device == "floppy":
        bootable_floppy = [
            dev
            for dev in vm.config.hardware.device
            if isinstance(dev, vim.vm.device.VirtualFloppy)
        ]
        if bootable_floppy:
            boot_order_list.append(vim.vm.BootOptions.BootableFloppyDevice())

    kwargs = dict()
    kwargs.update({"bootOrder": boot_order_list})

    vm_conf = vim.vm.ConfigSpec()
    vm_conf.bootOptions = vim.vm.BootOptions(**kwargs)
    vm.ReconfigVM_Task(vm_conf)
    return


def send_nmi(conn, vm):
    """Send NMI to specified VM.

    https://github.com/vmware/pyvmomi/issues/726
    """
    context = None
    if hasattr(ssl, "_create_unverified_context"):
        context = ssl._create_unverified_context()

    vmx_path = vm.config.files.vmPathName
    for ds_url in vm.config.datastoreUrl:
        vmx_path = vmx_path.replace("[%s] " % ds_url.name, "%s/" % ds_url.url)

    url = "https://%s/cgi-bin/vm-support.cgi?manifests=%s&vm=%s" % (
        vm.runtime.host.name,
        urllib.parse.quote_plus("HungVM:Send_NMI_To_Guest"),
        urllib.parse.quote_plus(vmx_path),
    )

    spec = vim.SessionManager.HttpServiceRequestSpec(method="httpGet", url=url)
    ticket = conn.content.sessionManager.AcquireGenericServiceTicket(spec)
    headers = {
        "Cookie": "vmware_cgi_ticket=%s" % ticket.id,
    }

    req = urllib.request.Request(url, headers=headers)
    Thread(
        target=urllib.request.urlopen, args=(req,), kwargs={"context": context}
    ).start()


def is_pid_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def str2bool(string):
    lower = string.lower()
    if lower not in ("true", "false"):
        raise ValueError('Value "%s" can not be interpreted as ' "boolean" % string)
    return lower == "true"


def mask_dict_password(dictionary, secret="***"):
    """Replace passwords with a secret in a dictionary."""
    d = dictionary.copy()
    for k in d:
        if "password" in k:
            d[k] = secret
    return d


def generate_fakemac_by_vm_name(vm_name):
    hash = hashlib.md5(vm_name.encode()).digest()
    fakemac = ":".join(
        "%02x" % b for b in [0x02, 0x00, 0x00, hash[0], hash[1], hash[2]]
    )
    return fakemac


def convert_fakemac_string_to_bytes(fakemac_str):
    fakemac_bytes = [int(b, 16) for b in re.split(":|-", fakemac_str)]
    return fakemac_bytes


class detach_process(object):
    """Detach the process from its parent and session."""

    def _fork(self, parent_exits):
        try:
            pid = os.fork()
            if pid > 0 and parent_exits:
                os._exit(0)

            return pid

        except OSError as e:
            raise exception.DetachProcessError(error=e)

    def _change_root_directory(self):
        """Change to root directory.

        Ensure that our process doesn't keep any directory in use. Failure
        to do this could make it so that an administrator couldn't
        unmount a filesystem, because it was our current directory.
        """
        try:
            os.chdir("/")
        except Exception as e:
            error = "Failed to change root directory. Error: %s" % e
            raise exception.DetachProcessError(error=error)

    def _change_file_creation_mask(self):
        """Set the umask for new files.

        Set the umask for new files the process creates so that it does
        have complete control over the permissions of them. We don't
        know what umask we may have inherited.
        """
        try:
            os.umask(0)
        except Exception as e:
            error = "Failed to change file creation mask. Error: %s" % e
            raise exception.DetachProcessError(error=error)

    def __enter__(self):
        pid = self._fork(parent_exits=False)
        if pid > 0:
            return pid

        os.setsid()

        self._fork(parent_exits=True)

        self._change_root_directory()
        self._change_file_creation_mask()

        sys.stdout.flush()
        sys.stderr.flush()

        si = open(os.devnull, "r")
        so = open(os.devnull, "a+")
        se = open(os.devnull, "a+")

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        return pid

    def __exit__(self, type, value, traceback):
        pass
