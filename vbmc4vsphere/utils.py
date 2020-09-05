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

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim, vmodl

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


def get_obj(conn, root, vim_type):
    container = conn.content.viewManager.CreateContainerView(root, vim_type, True)
    view = container.view
    container.Destroy()
    return view


def create_filter_spec(pc, vms, prop):
    objSpecs = []
    for vm in vms:
        objSpec = vmodl.query.PropertyCollector.ObjectSpec(obj=vm)
        objSpecs.append(objSpec)
    filterSpec = vmodl.query.PropertyCollector.FilterSpec()
    filterSpec.objectSet = objSpecs
    propSet = vmodl.query.PropertyCollector.PropertySpec(all=False)
    propSet.type = vim.VirtualMachine
    propSet.pathSet = [prop]
    filterSpec.propSet = [propSet]
    return filterSpec


def filter_results(result, value):
    vms = []
    for o in result.objects:
        if o.propSet[0].val == value:
            vms.append(o.obj)
    return vms


def get_viserver_vm(conn, vm):
    try:
        vms = get_obj(conn, conn.content.rootFolder, [vim.VirtualMachine])
        pc = conn.content.propertyCollector

        filter_spec = create_filter_spec(pc, vms, "name")
        options = vmodl.query.PropertyCollector.RetrieveOptions()
        result = pc.RetrievePropertiesEx([filter_spec], options)

        vms = filter_results(result, vm)

        if len(vms) != 1:
            raise Exception

        return vms[0]

    except Exception:
        raise exception.VMNotFound(vm=vm)


def check_viserver_connection_and_vm(vi, vm, vi_username=None, vi_password=None):
    with viserver_open(
        vi, readonly=True, vi_username=vi_username, vi_password=vi_password
    ) as conn:
        get_viserver_vm(conn, vm)


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
