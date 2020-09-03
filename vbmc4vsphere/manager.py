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

import configparser
import errno
import multiprocessing
import os
import shutil
import signal

from vbmc4vsphere import config as vbmc_config
from vbmc4vsphere import exception, log, utils
from vbmc4vsphere.vbmc import VirtualBMC

LOG = log.get_logger()

# BMC status
RUNNING = "running"
DOWN = "down"
ERROR = "error"

DEFAULT_SECTION = "VirtualBMC"

CONF = vbmc_config.get_config()


class VirtualBMCManager(object):

    VBMC_OPTIONS = [
        "username",
        "password",
        "address",
        "port",
        "fakemac",
        "vm_name",
        "viserver",
        "viserver_username",
        "viserver_password",
        "active",
    ]

    def __init__(self):
        super(VirtualBMCManager, self).__init__()
        self.config_dir = CONF["default"]["config_dir"]
        self._running_vms = {}

    def _parse_config(self, vm_name):
        config_path = os.path.join(self.config_dir, vm_name, "config")
        if not os.path.exists(config_path):
            raise exception.VMNotFound(vm=vm_name)

        try:
            config = configparser.ConfigParser()
            config.read(config_path)

            bmc = {}
            for item in self.VBMC_OPTIONS:
                try:
                    value = config.get(DEFAULT_SECTION, item)
                except configparser.NoOptionError:
                    value = None

                bmc[item] = value

            # Generate Fake MAC if needed
            if bmc["fakemac"] is None:
                bmc["fakemac"] = utils.generate_fakemac_by_vm_name(vm_name)

            # Port needs to be int
            bmc["port"] = config.getint(DEFAULT_SECTION, "port")

            return bmc

        except OSError:
            raise exception.VMNotFound(vm=vm_name)

    def _store_config(self, **options):
        config = configparser.ConfigParser()
        config.add_section(DEFAULT_SECTION)

        for option, value in options.items():
            if value is not None:
                config.set(DEFAULT_SECTION, option, str(value))

        config_path = os.path.join(self.config_dir, options["vm_name"], "config")

        with open(config_path, "w") as f:
            config.write(f)

    def _vbmc_enabled(self, vm_name, lets_enable=None, config=None):
        if not config:
            config = self._parse_config(vm_name)

        try:
            currently_enabled = utils.str2bool(config["active"])

        except Exception:
            currently_enabled = False

        if lets_enable is not None and lets_enable != currently_enabled:
            config.update(active=lets_enable)
            self._store_config(**config)
            currently_enabled = lets_enable

        return currently_enabled

    def _sync_vbmc_states(self, shutdown=False):
        """Starts/stops vBMC instances

        Walks over vBMC instances configuration, starts
        enabled but dead instances, kills non-configured
        but alive ones.
        """

        def vbmc_runner(bmc_config):
            # The manager process installs a signal handler for SIGTERM to
            # propagate it to children. Return to the default handler.
            signal.signal(signal.SIGTERM, signal.SIG_DFL)

            show_passwords = CONF["default"]["show_passwords"]

            if show_passwords:
                show_options = bmc_config
            else:
                show_options = utils.mask_dict_password(bmc_config)

            try:
                vbmc = VirtualBMC(**bmc_config)

            except Exception as ex:
                LOG.exception(
                    "Error running vBMC with configuration " "%(opts)s: %(error)s",
                    {"opts": show_options, "error": ex},
                )
                return

            try:
                vbmc.listen(timeout=CONF["ipmi"]["session_timeout"])

            except Exception as ex:
                LOG.exception(
                    "Shutdown vBMC for vm %(vm)s, cause " "%(error)s",
                    {"vm": show_options["vm_name"], "error": ex},
                )
                return

        for vm_name in os.listdir(self.config_dir):
            if not os.path.isdir(os.path.join(self.config_dir, vm_name)):
                continue

            try:
                bmc_config = self._parse_config(vm_name)

            except exception.VMNotFound:
                continue

            if shutdown:
                lets_enable = False
            else:
                lets_enable = self._vbmc_enabled(vm_name, config=bmc_config)

            instance = self._running_vms.get(vm_name)

            if lets_enable:

                if not instance or not instance.is_alive():

                    instance = multiprocessing.Process(
                        name="vbmcd-managing-vm-%s" % vm_name,
                        target=vbmc_runner,
                        args=(bmc_config,),
                    )

                    instance.daemon = True
                    instance.start()

                    self._running_vms[vm_name] = instance

                    LOG.info(
                        "Started vBMC instance for vm " "%(vm)s", {"vm": vm_name},
                    )

                if not instance.is_alive():
                    LOG.debug(
                        "Found dead vBMC instance for vm %(vm)s " "(rc %(rc)s)",
                        {"vm": vm_name, "rc": instance.exitcode},
                    )

            else:
                if instance:
                    if instance.is_alive():
                        instance.terminate()
                        LOG.info(
                            "Terminated vBMC instance for vm " "%(vm)s",
                            {"vm": vm_name},
                        )

                    self._running_vms.pop(vm_name, None)

    def _show(self, vm_name):
        bmc_config = self._parse_config(vm_name)

        show_passwords = CONF["default"]["show_passwords"]

        if show_passwords:
            show_options = bmc_config
        else:
            show_options = utils.mask_dict_password(bmc_config)

        instance = self._running_vms.get(vm_name)

        if instance and instance.is_alive():
            show_options["status"] = RUNNING
        elif instance and not instance.is_alive():
            show_options["status"] = ERROR
        else:
            show_options["status"] = DOWN

        return show_options

    def periodic(self, shutdown=False):
        self._sync_vbmc_states(shutdown)

    def add(
        self,
        username,
        password,
        port,
        address,
        fakemac,
        vm_name,
        viserver,
        viserver_username,
        viserver_password,
        **kwargs
    ):

        # check VI Serevr's connection and if vm exist prior to adding it
        # utils.check_viserver_connection_and_vm(
        #     viserver, vm_name,
        #     vi_username=viserver_username,
        #     vi_password=viserver_password)

        vm_path = os.path.join(self.config_dir, vm_name)

        try:
            os.makedirs(vm_path)
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                return 1, str(ex)

            msg = "Failed to create vm %(vm)s. " "Error: %(error)s" % {
                "vm": vm_name,
                "error": ex,
            }
            LOG.error(msg)
            return 1, msg

        if fakemac is None:
            fakemac = utils.generate_fakemac_by_vm_name(vm_name)

        try:
            self._store_config(
                vm_name=vm_name,
                username=username,
                password=password,
                port=str(port),
                address=address,
                fakemac=fakemac.replace("-", ":"),
                viserver=viserver,
                viserver_username=viserver_username,
                viserver_password=viserver_password,
                active=False,
            )

        except Exception as ex:
            self.delete(vm_name)
            return 1, str(ex)

        return 0, ""

    def delete(self, vm_name):
        vm_path = os.path.join(self.config_dir, vm_name)
        if not os.path.exists(vm_path):
            raise exception.VMNotFound(vm=vm_name)

        try:
            self.stop(vm_name)
        except exception.VirtualBMCError:
            pass

        shutil.rmtree(vm_path)

        return 0, ""

    def start(self, vm_name):
        try:
            bmc_config = self._parse_config(vm_name)

        except Exception as ex:
            return 1, str(ex)

        if vm_name in self._running_vms:

            self._sync_vbmc_states()

            if vm_name in self._running_vms:
                LOG.warning(
                    "BMC instance %(vm)s already running, ignoring "
                    '"start" command' % {"vm": vm_name}
                )
                return 0, ""

        try:
            self._vbmc_enabled(vm_name, config=bmc_config, lets_enable=True)

        except Exception as e:
            LOG.exception("Failed to start vm %s", vm_name)
            return (
                1,
                (
                    "Failed to start vm %(vm)s. Error: "
                    "%(error)s" % {"vm": vm_name, "error": e}
                ),
            )

        self._sync_vbmc_states()

        return 0, ""

    def stop(self, vm_name):
        try:
            self._vbmc_enabled(vm_name, lets_enable=False)

        except Exception as ex:
            LOG.exception("Failed to stop vm %s", vm_name)
            return 1, str(ex)

        self._sync_vbmc_states()

        return 0, ""

    def list(self):
        rc = 0
        tables = []
        try:
            for vm in os.listdir(self.config_dir):
                if os.path.isdir(os.path.join(self.config_dir, vm)):
                    tables.append(self._show(vm))

        except OSError as e:
            if e.errno == errno.EEXIST:
                rc = 1

        return rc, tables

    def show(self, vm_name):
        return 0, list(self._show(vm_name).items())
