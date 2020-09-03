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

# import xml.etree.ElementTree as ET

import struct
import traceback

import pyghmi.ipmi.bmc as bmc
import pyghmi.ipmi.private.session as ipmisession
from pyghmi.ipmi.private.serversession import IpmiServer as ipmiserver
from pyghmi.ipmi.private.serversession import ServerSession as serversession

from vbmc4vsphere import exception, log, utils

LOG = log.get_logger()

# Power states
POWEROFF = 0
POWERON = 1

# From the IPMI - Intelligent Platform Management Interface Specification
# Second Generation v2.0 Document Revision 1.1 October 1, 2013
# https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
#
# Command failed and can be retried
IPMI_COMMAND_NODE_BUSY = 0xC0
# Invalid data field in request
IPMI_INVALID_DATA = 0xCC


# Boot device maps
GET_BOOT_DEVICES_MAP = {
    "network": 4,
    "hd": 8,
    "cdrom": 0x14,
}

SET_BOOT_DEVICES_MAP = {
    "network": "network",
    "hd": "hd",
    "optical": "cdrom",
}


# Functions for patch pyghmi to handle sessionless IPMIv2 data and ASF Presence Ping
# Based on pyghmi 1.5.16
# Apache License 2.0
# https://opendev.org/x/pyghmi/src/branch/master/pyghmi/ipmi/private/serversession.py
def sessionless_data(self, data, sockaddr):
    """Examines unsolocited packet and decides appropriate action.

    For a listening IpmiServer, a packet without an active session
    comes here for examination.  If it is something that is utterly
    sessionless (e.g. get channel authentication), send the appropriate
    response.  If it is a get session challenge or open rmcp+ request,
    spawn a session to handle the context.
    """
    data = bytearray(data)
    if len(data) < 22:
        if data[0:4] == b"\x06\x00\xff\x06" and data[8] == 0x80:  # asf presense ping
            LOG.info("Responding to asf presence ping")
            send_asf_presence_pong(self, data, sockaddr)
        else:
            return
    if not (data[0] == 6 and data[2:4] == b"\xff\x07"):  # not ipmi
        return
    authtype = data[4]
    if authtype == 6:  # ipmi 2 payload...
        payloadtype = data[5]
        if payloadtype not in (0, 16):
            return
        if payloadtype == 16:  # new session to handle conversation
            serversession(
                self.authdata,
                self.kg,
                sockaddr,
                self.serversocket,
                data[16:],
                self.uuid,
                bmc=self,
            )
            return
        # ditch two byte, because ipmi2 header is two
        # bytes longer than ipmi1 (payload type added, payload length 2).
        data = data[2:]
    myaddr, netfnlun = struct.unpack("2B", bytes(data[14:16]))
    netfn = (netfnlun & 0b11111100) >> 2
    mylun = netfnlun & 0b11
    if netfn == 6:  # application request
        if data[19] == 0x38:  # cmd = get channel auth capabilities
            verchannel, level = struct.unpack("2B", bytes(data[20:22]))
            version = verchannel & 0b10000000
            if version != 0b10000000:
                return
            channel = verchannel & 0b1111
            if channel != 0xE:
                return
            (clientaddr, clientlun) = struct.unpack("BB", bytes(data[17:19]))
            clientseq = clientlun >> 2
            clientlun &= 0b11  # Lun is only the least significant bits
            level &= 0b1111
            if authtype == 6:
                self.send_auth_cap_v2(
                    myaddr, mylun, clientaddr, clientlun, clientseq, sockaddr
                )
            else:
                self.send_auth_cap(
                    myaddr, mylun, clientaddr, clientlun, clientseq, sockaddr
                )
        elif data[19] == 0x54:
            clientaddr, clientlun = data[17:19]
            clientseq = clientlun >> 2
            clientlun &= 0b11
            self.send_cipher_suites(
                myaddr, mylun, clientaddr, clientlun, clientseq, data, sockaddr
            )


# Functions for patch pyghmi to response to 0x38 in the forms of ipmi v2
# Based on pyghmi 1.5.16
# Apache License 2.0
# https://opendev.org/x/pyghmi/src/branch/master/pyghmi/ipmi/private/serversession.py
def send_auth_cap_v2(self, myaddr, mylun, clientaddr, clientlun, clientseq, sockaddr):
    header = bytearray(
        b"\x06\x00\xff\x07\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00"
    )
    headerdata = [clientaddr, clientlun | (7 << 2)]
    headersum = ipmisession._checksum(*headerdata)
    header += bytearray(
        headerdata + [headersum, myaddr, mylun | (clientseq << 2), 0x38]
    )
    header += self.authcap
    bodydata = struct.unpack("B" * len(header[19:]), bytes(header[19:]))

    header.append(ipmisession._checksum(*bodydata))
    ipmisession._io_sendto(self.serversocket, header, sockaddr)


# Functions for patch pyghmi to response to asf presence ping
def send_asf_presence_pong(self, data, sockaddr):
    header = bytearray(
        b"\x06\x00\xff\x06\x00\x00\x11\xbe\x40"
        + struct.pack("B", data[9])
        + b"\x00\x10\x00\x00\x11\xbe\x00\x00\x00\x00\x81\x00\x00\x00\x00\x00\x00\x00"
    )
    ipmisession._io_sendto(self.serversocket, header, sockaddr)


# Patch pyghmi with modified functions
ipmiserver.sessionless_data = sessionless_data
ipmiserver.send_auth_cap_v2 = send_auth_cap_v2


class VirtualBMC(bmc.Bmc):
    def __init__(
        self,
        username,
        password,
        port,
        address,
        vm_name,
        viserver,
        viserver_username=None,
        viserver_password=None,
        **kwargs
    ):
        super(VirtualBMC, self).__init__(
            {username: password}, port=port, address=address
        )
        self.vm_name = vm_name
        self._conn_args = {
            "vi": viserver,
            "vi_username": viserver_username,
            "vi_password": viserver_password,
        }

    def get_boot_device(self):
        LOG.debug("Get boot device called for %(vm)s", {"vm": self.vm_name})
        return IPMI_COMMAND_NODE_BUSY
        # with utils.libvirt_open(readonly=True, **self._conn_args) as conn:
        #     vm = utils.get_libvirt_vm(conn, self.vm_name)
        #     boot_element = ET.fromstring(vm.XMLDesc()).find('.//os/boot')
        #     boot_dev = None
        #     if boot_element is not None:
        #         boot_dev = boot_element.attrib.get('dev')
        #     return GET_BOOT_DEVICES_MAP.get(boot_dev, 0)

    def _remove_boot_elements(self, parent_element):
        for boot_element in parent_element.findall("boot"):
            parent_element.remove(boot_element)

    def set_boot_device(self, bootdevice):
        LOG.debug(
            "Set boot device called for %(vm)s with boot " 'device "%(bootdev)s"',
            {"vm": self.vm_name, "bootdev": bootdevice},
        )
        return IPMI_COMMAND_NODE_BUSY
        # device = SET_BOOT_DEVICES_MAP.get(bootdevice)
        # if device is None:
        #     # Invalid data field in request
        #     return IPMI_INVALID_DATA
        #
        # try:
        #     with utils.libvirt_open(**self._conn_args) as conn:
        #         vm = utils.get_libvirt_vm(conn, self.vm_name)
        #         tree = ET.fromstring(vm.XMLDesc())
        #
        #         # Remove all "boot" element under "devices"
        #         # They are mutually exclusive with "os/boot"
        #         for device_element in tree.findall('devices/*'):
        #             self._remove_boot_elements(device_element)
        #
        #         for os_element in tree.findall('os'):
        #             # Remove all "boot" elements under "os"
        #             self._remove_boot_elements(os_element)
        #
        #             # Add a new boot element with the request boot device
        #             boot_element = ET.SubElement(os_element, 'boot')
        #             boot_element.set('dev', device)
        #
        #         conn.defineXML(ET.tostring(tree, encoding="unicode"))
        # except libvirt.libvirtError:
        #     LOG.error('Failed setting the boot device  %(bootdev)s for '
        #               'vm %(vm)s', {'bootdev': device,
        #                                     'vm': self.vm_name})
        #     # Command failed, but let client to retry
        #     return IPMI_COMMAND_NODE_BUSY

    def get_power_state(self):
        LOG.debug("Get power state called for vm %(vm)s", {"vm": self.vm_name})
        try:
            with utils.viserver_open(**self._conn_args) as conn:
                vm = utils.get_viserver_vm(conn, self.vm_name)
                if "poweredOn" == vm.runtime.powerState:
                    return POWERON
        except Exception as e:
            msg = "Error getting the power state of vm %(vm)s. " "Error: %(error)s" % {
                "vm": self.vm_name,
                "error": e,
            }
            LOG.error(msg)
            raise exception.VirtualBMCError(message=msg)

        return POWEROFF

    def pulse_diag(self):
        LOG.debug("Power diag called for vm %(vm)s", {"vm": self.vm_name})
        return IPMI_COMMAND_NODE_BUSY
        # try:
        #     with utils.libvirt_open(**self._conn_args) as conn:
        #         vm = utils.get_libvirt_vm(conn, self.vm_name)
        #         if vm.isActive():
        #             vm.injectNMI()
        # except libvirt.libvirtError as e:
        #     LOG.error(
        #         "Error powering diag the vm %(vm)s. " "Error: %(error)s",
        #         {"vm": self.vm_name, "error": e},
        #     )
        #     # Command failed, but let client to retry
        #     return IPMI_COMMAND_NODE_BUSY

    def power_off(self):
        LOG.debug("Power off called for vm %(vm)s", {"vm": self.vm_name})
        try:
            with utils.viserver_open(**self._conn_args) as conn:
                vm = utils.get_viserver_vm(conn, self.vm_name)
                if "poweredOn" == vm.runtime.powerState:
                    vm.PowerOff()
        except Exception as e:
            LOG.error(
                "Error powering off the vm %(vm)s. " "Error: %(error)s",
                {"vm": self.vm_name, "error": e},
            )
            # Command failed, but let client to retry
            return IPMI_COMMAND_NODE_BUSY

    def power_on(self):
        LOG.debug("Power on called for vm %(vm)s", {"vm": self.vm_name})
        try:
            with utils.viserver_open(**self._conn_args) as conn:
                vm = utils.get_viserver_vm(conn, self.vm_name)
                if "poweredOn" != vm.runtime.powerState:
                    vm.PowerOn()
        except Exception as e:
            LOG.error(
                "Error powering on the vm %(vm)s. " "Error: %(error)s",
                {"vm": self.vm_name, "error": e},
            )
            # Command failed, but let client to retry
            return IPMI_COMMAND_NODE_BUSY

    def power_shutdown(self):
        LOG.debug("Soft power off called for vm %(vm)s", {"vm": self.vm_name})
        try:
            with utils.viserver_open(**self._conn_args) as conn:
                vm = utils.get_viserver_vm(conn, self.vm_name)
                if "poweredOn" == vm.runtime.powerState:
                    vm.ShutdownGuest()
        except Exception as e:
            LOG.error(
                "Error soft powering off the vm %(vm)s. " "Error: %(error)s",
                {"vm": self.vm_name, "error": e},
            )
            # Command failed, but let client to retry
            return IPMI_COMMAND_NODE_BUSY

    def power_reset(self):
        LOG.debug("Power reset called for vm %(vm)s", {"vm": self.vm_name})
        try:
            with utils.viserver_open(**self._conn_args) as conn:
                vm = utils.get_viserver_vm(conn, self.vm_name)
                if "poweredOn" == vm.runtime.powerState:
                    vm.Reset()
        except Exception as e:
            LOG.error(
                "Error reseting the vm %(vm)s. " "Error: %(error)s",
                {"vm": self.vm_name, "error": e},
            )
            # Command not supported in present state
            return IPMI_COMMAND_NODE_BUSY

    # Based on pyghmi 1.5.16
    # Apache License 2.0
    # https://opendev.org/x/pyghmi/src/branch/master/pyghmi/ipmi/bmc.py
    def handle_raw_request(self, request, session):
        LOG.info(
            "Received netfn = 0x%x (%d), command = 0x%x (%d), data = %s"
            % (
                request["netfn"],
                request["netfn"],
                request["command"],
                request["command"],
                request["data"].hex(),
            )
        )
        try:
            if request["netfn"] == 6:
                if request["command"] == 1:  # get device id
                    return self.send_device_id(session)
                elif request["command"] == 2:  # cold reset
                    return session.send_ipmi_response(code=self.cold_reset())
                elif request["command"] == 0x48:  # activate payload
                    return self.activate_payload(request, session)
                elif request["command"] == 0x49:  # deactivate payload
                    return self.deactivate_payload(request, session)
            elif request["netfn"] == 0:
                if request["command"] == 1:  # get chassis status
                    return self.get_chassis_status(session)
                elif request["command"] == 2:  # chassis control
                    return self.control_chassis(request, session)
                elif request["command"] == 8:  # set boot options
                    return self.set_system_boot_options(request, session)
                elif request["command"] == 9:  # get boot options
                    return self.get_system_boot_options(request, session)
            session.send_ipmi_response(code=0xC1)
        except NotImplementedError:
            session.send_ipmi_response(code=0xC1)
        except Exception:
            session._send_ipmi_net_payload(code=0xFF)
            traceback.print_exc()
