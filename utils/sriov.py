
import os
import re
import commands
import logging

def get_full_pci_id(pci_id):
    """
    Get full PCI ID of pci_id.

    @param pci_id: PCI ID of a device.
    """
    cmd = "lspci -D | awk '/%s/ {print $1}'" % pci_id
    status, full_id = commands.getstatusoutput(cmd)
    if status != 0:
        return None
    return full_id


def get_vendor_from_pci_id(pci_id):
    """
    Check out the device vendor ID according to pci_id.

    @param pci_id: PCI ID of a device.
    """
    cmd = "lspci -n | awk '/%s/ {print $3}'" % pci_id
    return re.sub(":", " ", commands.getoutput(cmd))


class sriov(object):
    """
    Request PCI assignable devices on host. It will check whether to request
    PF (physical Functions) or VF (Virtual Functions).
    """
    def __init__(self, type="vf", driver=None, driver_option=None,
                 names=None, devices_requested=None):
        """
        Initialize parameter 'type' which could be:
        vf: Virtual Functions
        pf: Physical Function (actual hardware)
        mixed:  Both includes VFs and PFs

        If pass through Physical NIC cards, we need to specify which devices
        to be assigned, e.g. 'eth1 eth2'.

        If pass through Virtual Functions, we need to specify how many vfs
        are going to be assigned, e.g. passthrough_count = 8 and max_vfs in
        config file.

        @param type: PCI device type.
        @param driver: Kernel module for the PCI assignable device.
        @param driver_option: Module option to specify the maximum number of
                VFs (eg 'max_vfs=7')
        @param names: Physical NIC cards correspondent network interfaces,
                e.g.'eth1 eth2 ...'
        @param devices_requested: Number of devices being requested.
        """
        self.type = type
        self.driver = driver
        self.driver_option = driver_option
        if names:
            self.name_list = names.split()
        if devices_requested:
            self.devices_requested = int(devices_requested)
        else:
            self.devices_requested = None


    def _get_pf_pci_id(self, name, search_str):
        """
        Get the PF PCI ID according to name.

        @param name: Name of the PCI device.
        @param search_str: Search string to be used on lspci.
        """
        cmd = "ethtool -i %s | awk '/bus-info/ {print $2}'" % name
        s, pci_id = commands.getstatusoutput(cmd)
        if not (s or "Cannot get driver information" in pci_id):
            return pci_id[5:]
        cmd = "lspci | awk '/%s/ {print $1}'" % search_str
        pci_ids = [id for id in commands.getoutput(cmd).splitlines()]
        nic_id = int(re.search('[0-9]+', name).group(0))
        if (len(pci_ids) - 1) < nic_id:
            return None
        return pci_ids[nic_id]


    def _release_dev(self, pci_id):
        """
        Release a single PCI device.

        @param pci_id: PCI ID of a given PCI device.
        """
        base_dir = "/sys/bus/pci"
        full_id = get_full_pci_id(pci_id)
        vendor_id = get_vendor_from_pci_id(pci_id)
        drv_path = os.path.join(base_dir, "devices/%s/driver" % full_id)
        if 'pci-stub' in os.readlink(drv_path):
            cmd = "echo '%s' > %s/new_id" % (vendor_id, drv_path)
            if os.system(cmd):
                return False

            stub_path = os.path.join(base_dir, "drivers/pci-stub")
            cmd = "echo '%s' > %s/unbind" % (full_id, stub_path)
            if os.system(cmd):
                return False

            driver = self.dev_drivers[pci_id]
            cmd = "echo '%s' > %s/bind" % (full_id, driver)
            if os.system(cmd):
                return False

        return True


    def get_vf_devs(self):
        """
        Catch all VFs PCI IDs.

        @return: List with all PCI IDs for the Virtual Functions avaliable
        """
        if not self.sr_iov_setup():
            return []

        cmd = "lspci | awk '/Virtual Function/ {print $1}'"
        return commands.getoutput(cmd).split()


    def get_pf_devs(self):
        """
        Catch all PFs PCI IDs.

        @return: List with all PCI IDs for the physical hardware requested
        """
        pf_ids = []
        for name in self.name_list:
            pf_id = self._get_pf_pci_id(name, "Ethernet")
            if not pf_id:
                continue
            pf_ids.append(pf_id)
        return pf_ids


    def get_devs(self, count):
        """
        Check out all devices' PCI IDs according to their name.

        @param count: count number of PCI devices needed for pass through
        @return: a list of all devices' PCI IDs
        """
        if self.type == "vf":
            vf_ids = self.get_vf_devs()
        elif self.type == "pf":
            vf_ids = self.get_pf_devs()
        elif self.type == "mixed":
            vf_ids = self.get_vf_devs()
            vf_ids.extend(self.get_pf_devs())
        return vf_ids[0:count]


    def get_vfs_count(self):
        """
        Get VFs count number according to lspci.
        """
        # FIXME: Need to think out a method of identify which
        # 'virtual function' belongs to which physical card considering
        # that if the host has more than one 82576 card. PCI_ID?
        cmd = "lspci | grep 'Virtual Function' | wc -l"
        return int(commands.getoutput(cmd))


    def check_vfs_count(self):
        """
        Check VFs count number according to the parameter driver_options.
        """
        # Network card 82576 has two network interfaces and each can be
        # virtualized up to 7 virtual functions, therefore we multiply
        # two for the value of driver_option 'max_vfs'.
        expected_count = int((re.findall("(\d)", self.driver_option)[0])) * 2
        return (self.get_vfs_count == expected_count)


    def is_binded_to_stub(self, full_id):
        """
        Verify whether the device with full_id is already binded to pci-stub.

        @param full_id: Full ID for the given PCI device
        """
        base_dir = "/sys/bus/pci"
        stub_path = os.path.join(base_dir, "drivers/pci-stub")
        if os.path.exists(os.path.join(stub_path, full_id)):
            return True
        return False


    def sr_iov_setup(self):
        """
        Ensure the PCI device is working in sr_iov mode.

        Check if the PCI hardware device drive is loaded with the appropriate,
        parameters (number of VFs), and if it's not, perform setup.

        @return: True, if the setup was completed successfuly, False otherwise.
        """
        re_probe = False
        s, o = commands.getstatusoutput('lsmod | grep %s' % self.driver)
        if s:
            re_probe = True
        elif not self.check_vfs_count():
            os.system("modprobe -r %s" % self.driver)
            re_probe = True
        else:
            return True

        # Re-probe driver with proper number of VFs
        if re_probe:
            cmd = "modprobe %s %s" % (self.driver, self.driver_option)
            logging.info("Loading the driver '%s' with option '%s'",
                         self.driver, self.driver_option)
            s, o = commands.getstatusoutput(cmd)
            if s:
                return False
            return True


    def request_devs(self):
        """
        Implement setup process: unbind the PCI device and then bind it
        to the pci-stub driver.

        @return: a list of successfully requested devices' PCI IDs.
        """
        base_dir = "/sys/bus/pci"
        stub_path = os.path.join(base_dir, "drivers/pci-stub")

        self.pci_ids = self.get_devs(self.devices_requested)
        logging.debug("The following pci_ids were found: %s", self.pci_ids)
        requested_pci_ids = []
        self.dev_drivers = {}

        # Setup all devices specified for assignment to guest
        for pci_id in self.pci_ids:
            full_id = get_full_pci_id(pci_id)
            if not full_id:
                continue
            drv_path = os.path.join(base_dir, "devices/%s/driver" % full_id)
            dev_prev_driver = os.path.realpath(os.path.join(drv_path,
                                               os.readlink(drv_path)))
            self.dev_drivers[pci_id] = dev_prev_driver

            # Judge whether the device driver has been binded to stub
            if not self.is_binded_to_stub(full_id):
                logging.debug("Binding device %s to stub", full_id)
                vendor_id = get_vendor_from_pci_id(pci_id)
                stub_new_id = os.path.join(stub_path, 'new_id')
                unbind_dev = os.path.join(drv_path, 'unbind')
                stub_bind = os.path.join(stub_path, 'bind')

                info_write_to_files = [(vendor_id, stub_new_id),
                                       (full_id, unbind_dev),
                                       (full_id, stub_bind)]

                for content, file in info_write_to_files:
                    try:
                        utils.open_write_close(file, content)
                    except IOError:
                        logging.debug("Failed to write %s to file %s", content,
                                      file)
                        continue

                if not self.is_binded_to_stub(full_id):
                    logging.error("Binding device %s to stub failed", pci_id)
                    continue
            else:
                logging.debug("Device %s already binded to stub", pci_id)
            requested_pci_ids.append(pci_id)
        self.pci_ids = requested_pci_ids
        return self.pci_ids


    def release_devs(self):
        """
        Release all PCI devices currently assigned to VMs back to the
        virtualization host.
        """
        try:
            for pci_id in self.dev_drivers:
                if not self._release_dev(pci_id):
                    logging.error("Failed to release device %s to host", pci_id)
                else:
                    logging.info("Released device %s successfully", pci_id)
        except:
            return