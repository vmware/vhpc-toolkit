# Virtualized High Performance Computing Toolkit
#
# Copyright (c) 2018-2019 VMware, Inc. All Rights Reserved.
#
# This product is licensed to you under the Apache 2.0 license (the
# "License"). You may not use this product except in compliance with the
# Apache 2.0 License. This product may include a number of subcomponents with
#  separate copyright notices and license terms. Your use of these
# subcomponents is subject to the terms and conditions of the subcomponent's
# license, as noted in the LICENSE file.
# SPDX-License-Identifier: Apache-2.0
# coding=utf-8
import os

from pyVmomi import vim
from pyVmomi import vmodl

from vhpc_toolkit import log
from vhpc_toolkit.get_objs import GetDatacenter
from vhpc_toolkit.get_objs import GetHost
from vhpc_toolkit.get_objs import GetVM
from vhpc_toolkit.wait import GetWait


class ConfigVM(object):
    """
    A class for configuring VM properties.
    Methods under this class will call ReconfigVM_Task (a method of
    VirtualMachine object) and return a Task
    object, with which to monitor the status of operation.

    API References:
            https://pubs.vmware.com/vi3/sdk/ReferenceGuide
            https://github.com/vmware/pyvmomi

    """

    def __init__(self, vm_obj):
        """
        Args:
            vm_obj (vim.VirtualMachine)

        """

        self.vm_obj = vm_obj
        self.logger = log.my_logger(name=self.__class__.__name__)

    def memory(self, memory_mb):
        """ Configure memory size for a VM

        Args:
            memory_mb (int): memory size in MB to be configured

        Returns:
            Task

        """

        config_spec = vim.vm.ConfigSpec()
        config_spec.memoryMB = memory_mb
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def cpus(self, num_of_cpus):
        """ Configure number of CPUs for a VM

        Args:
            num_of_cpus (int): number of CPUs to be configured

        Returns:
            Task

        """

        config_spec = vim.vm.ConfigSpec()
        config_spec.numCPUs = num_of_cpus
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def cpu_shares(self, shares):
        """ Configure CPU shares for a VM

        Args:
            shares (int): CPU shares to be configured

        Returns:
            Task

        """
        assert shares >= 0
        config_spec = vim.vm.ConfigSpec()
        shares_alloc = vim.ResourceAllocationInfo()
        shares_alloc.shares = vim.SharesInfo(level="custom", shares=shares)
        config_spec.cpuAllocation = shares_alloc
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def memory_shares(self, shares):
        """ Configure memory shares for a VM

        Args:
            shares (int): memory shares to be configured

        Returns:
            Task

        """

        assert shares >= 0
        config_spec = vim.vm.ConfigSpec()
        shares_alloc = vim.ResourceAllocationInfo()
        shares_alloc.shares = vim.SharesInfo(level="custom", shares=shares)
        config_spec.memoryAllocation = shares_alloc
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def memory_reservation(self, reser=0):
        """ Configure memory reservation for a VM

        Args:
            reser (int): 0 (clear reservation) or
                        non-0 (reserve all memory that is configured)

        Returns:
            Task

        """

        config_spec = vim.vm.ConfigSpec()
        mem_alloc = vim.ResourceAllocationInfo()
        if reser:
            mem_alloc.reservation = self.vm_obj.config.hardware.memoryMB
            config_spec.memoryReservationLockedToMax = True
        else:
            mem_alloc.reservation = 0
            config_spec.memoryReservationLockedToMax = False
        config_spec.memoryAllocation = mem_alloc
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def cpu_reservation(self, host_cpu_mhz=None, reser=0):
        """ Configure CPU reservation for a VM

        Args:
            host_cpu_mhz (int): if to reser, host_cpu_mhz must have a value
            reser (int): 0 (clear reservation) or
                         non-0 (reserve all vCPUs that is configured)

        Returns:
                Task

        """

        config_spec = vim.vm.ConfigSpec()
        cpu_alloc = vim.ResourceAllocationInfo()
        if reser:
            assert host_cpu_mhz is not None
            vm_cpu = self.vm_obj.config.hardware.numCPU
            cpu_alloc.reservation = int(vm_cpu * host_cpu_mhz)
        else:
            cpu_alloc.reservation = 0
        config_spec.cpuAllocation = cpu_alloc
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def cpu_hotadd(self, enable_hotadd=True):
        """ Enable/disable CPU hotadd

        Args:
            enable_hotadd (bool)

        Returns:
                Task

        """

        config_spec = vim.vm.ConfigSpec()
        config_spec.cpuHotAddEnabled = enable_hotadd
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def mem_hotadd(self, enable_hotadd=True):
        """ Enable/disable memory hotadd

        Args:
            enable_hotadd (bool)

        Returns:
            Task

        """

        config_spec = vim.vm.ConfigSpec()
        config_spec.memoryHotAddEnabled = enable_hotadd
        return self.vm_obj.ReconfigVM_Task(config_spec)

    def power_on(self):
        """ Power on VM

        Returns:
            Task

        """

        return self.vm_obj.PowerOn()

    def power_off(self):
        """ Power off VM

        Returns:
            Task

        """

        return self.vm_obj.PowerOff()

    def latency(self, level):
        """ Configure Latency Sensitivity for a VM

        Args:
            level (str): the Latency Sensitivity Level,
                             available: 'high' and 'normal'

        Returns:
            Task

        """

        latency_levels = ["high", "normal"]
        if level not in latency_levels:
            self.logger.error(
                "Wrong Latency Sensitivity level. "
                "Available: {0}".format(str(latency_levels).strip("[]"))
            )
            raise SystemExit
        else:
            config_spec = vim.vm.ConfigSpec()
            lat_sens = vim.LatencySensitivity()
            lat_sens.level = level
            config_spec.latencySensitivity = lat_sens
            return self.vm_obj.ReconfigVM_Task(config_spec)

    def destroy(self):
        """ Destroy a VM

        Returns:
            Task

        """

        return self.vm_obj.Destroy()

    def add_network_adapter(self, network_obj):
        """ Add a network adapter for a VM
            The device spec uses vim.vm.device.VirtualVmxnet3() by default,
            which is recommended for best performance.

        Args:
            network_obj (vim.Network): network object accessible
                                           by either hosts or virtual machines

        Returns:
            Task

        References:
            pyvmomi/docs/vim/Network.rst
            pyvmomi/docs/vim/vm/device/VirtualDeviceSpec.rst

        """

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        nic_spec.device = vim.vm.device.VirtualVmxnet3()
        nic_spec.device.wakeOnLanEnabled = True
        nic_spec.device.addressType = "assigned"
        nic_spec.device.deviceInfo = vim.Description()
        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_spec.device.backing.network = network_obj
        nic_spec.device.backing.deviceName = network_obj.name
        nic_spec.device.backing.useAutoDetect = False
        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.connected = True
        nic_spec.device.connectable.allowGuestControl = True
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [nic_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def remove_network_adapter(self, network_obj):
        """ Remove a network adapter for a VM

        Args:
            network_obj (vim.Network): network object accessible by either
            hosts or virtual machines

        Returns:
            Task

        References:
            pyvmomi/docs/vim/Network.rst
            pyvmomi/docs/vim/vm/device/VirtualDeviceSpec.rst

        """

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        nic_spec.device = network_obj
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [nic_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def add_sriov_adapter(self, network_obj, pf_obj, dvs_obj):
        """ Add a network adapter with SR-IOV adapter type for a VM
            Adding SR-IOV adapter requires a back-up physical adapter.

        Args:
            dvs_obj (vim.dvs.VmwareDistributedVirtualSwitch):
                                        distributed virtual switch object type
            network_obj (vim.Network): network object accessible
                                           by either hosts or virtual machines
            pf_obj (vim.host.PciDevice): a PCI object type describes info
                                        about of a single PCI device for
                                        backing up SR-IOV configuration

        Returns:
            Task

        References:
            pyvmomi/docs/vim/Network.rst
            pyvmomi/docs/vim/vm/device/VirtualDeviceSpec.rst
            pyvmomi/docs/vim/host/PciDevice.rst

        """

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        nic_spec.device = vim.vm.device.VirtualSriovEthernetCard()
        nic_spec.device.wakeOnLanEnabled = True
        nic_spec.device.addressType = "assigned"
        nic_spec.device.deviceInfo = vim.Description()
        if dvs_obj:
            nic_spec.device.backing = (
                vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
            )
            nic_spec.device.backing.port = vim.dvs.PortConnection(
                switchUuid=dvs_obj.summary.uuid, portgroupKey=network_obj.config.key
            )
        else:
            nic_spec.device.backing = (
                vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            )
            nic_spec.device.backing.network = network_obj
            nic_spec.device.backing.deviceName = network_obj.name
            nic_spec.device.backing.useAutoDetect = False
        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.connected = True
        nic_spec.device.connectable.allowGuestControl = True
        nic_spec.device.sriovBacking = (
            vim.vm.device.VirtualSriovEthernetCard.SriovBackingInfo()
        )
        nic_spec.device.allowGuestOSMtuChange = False
        # convert decimal to hex for the device ID of physical adapter
        device_id = hex(pf_obj.deviceId % 2 ** 16).lstrip("0x")
        sys_id = GetVM(self.vm_obj).pci_id_sys_id_sriov()
        backing = vim.VirtualPCIPassthroughDeviceBackingInfo(
            deviceId=device_id,
            id=pf_obj.id,
            systemId=sys_id[pf_obj.id],
            vendorId=pf_obj.vendorId,
            deviceName=pf_obj.deviceName,
        )
        nic_spec.device.sriovBacking.physicalFunctionBacking = backing
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [nic_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def remove_sriov_adapter(self, network_obj):
        """ Remove a SR-IOV network adapter for a VM.
            Same as removing a regular network adapter

        Args:
            network_obj (vim.Network): network object accessible
                                           by either hosts or virtual machines

        Returns:
                Task

        """

        task = self.remove_network_adapter(network_obj)
        return task

    def add_pvrdma(self, dvs_obj, network_obj, label="pvRDMA Network Adapter"):
        """ Add a network adapter with pvrdma adapter type for a VM
                Adding pvrdma adapter requires a port group from a DVS, which
                has uplinks mapped from host RDMA NICS.

        Args:
            dvs_obj (vim.dvs.VmwareDistributedVirtualSwitch):
                                        distributed virtual switch object type
            network_obj (vim.Network): network object accessible
                                        by either hosts or virtual machines
            label (str): adapter label

        Returns:
            Task

        API References:
            pyvmomi/docs/vim/Network.rst
            pyvmomi/docs/vim/vm/device/VirtualDeviceSpec.rst
            pyvmomi/docs/vim/dvs/VmwareDistributedVirtualSwitch/ConfigInfo.rst

        References:
            For more pvrdma configuration details,
            please refer to VMware Docs for PVRDMA Support and Configuration

        """

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        nic_spec.device = vim.vm.device.VirtualVmxnet3Vrdma()
        nic_spec.device.deviceInfo = vim.Description(label=label)
        nic_spec.device.addressType = "generated"
        nic_spec.device.backing = (
            vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        )
        nic_spec.device.backing.port = vim.dvs.PortConnection(
            switchUuid=dvs_obj.summary.uuid, portgroupKey=network_obj.config.key
        )
        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.connected = True
        nic_spec.device.connectable.allowGuestControl = True
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [nic_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def remove_pvrdma(self, network_obj):
        """ Remove a PVRDMA network adapter for a VM. Basically same as
            removing a regular network adapter

        Args:
            network_obj (vim.Network): network object accessible
                                           by either hosts or virtual machines
        Returns:
            Task

        """

        self.remove_network_adapter(network_obj)

    def config_networking(
        self, network_obj, ip, netmask, gateway, domain, dns, guest_hostname
    ):
        """ Configure network properties for a VM

        Args:
            network_obj (vim.Network): network object accessible
                                       by either hosts or virtual machines.
            ip(str): static IP address (IPv4 format) or None (DHCP)
            netmask (str): Should in IPv4 address format
            gateway (str): Should in IPv4 address format
            domain (str)
            dns (str or list of str)
            guest_hostname (str): if None, the default is VM name

        Returns:
            Task

        References:
            pyvmomi/docs/vim/Network.rst
            pyvmomi/docs/vim/vm/customization/Specification.rst

        """

        global_ip = vim.vm.customization.GlobalIPSettings()
        adapter_map = vim.vm.customization.AdapterMapping()
        adapter_map.adapter = vim.vm.customization.IPSettings()
        adapter_map.macAddress = network_obj.macAddress
        if ip:
            adapter_map.adapter.ip = vim.vm.customization.FixedIp()
            adapter_map.adapter.ip.ipAddress = ip
        else:
            adapter_map.adapter.ip = vim.vm.customization.DhcpIpGenerator()
        adapter_map.adapter.subnetMask = netmask
        adapter_map.adapter.gateway = gateway
        global_ip.dnsServerList = dns
        adapter_map.adapter.dnsDomain = domain
        ident = vim.vm.customization.LinuxPrep()
        ident.hostName = vim.vm.customization.FixedName()
        if guest_hostname:
            ident.hostName.name = guest_hostname
        else:
            ident.hostName.name = self.vm_obj.name
        custom_spec = vim.vm.customization.Specification()
        custom_spec.nicSettingMap = [adapter_map]
        custom_spec.identity = ident
        custom_spec.globalIPSettings = global_ip
        return self.vm_obj.Customize(spec=custom_spec)

    def enable_fork_parent(self):
        """ Enable fork parent for a VM

        Returns:
            None

        """

        self.vm_obj.EnableForkParent()

    def disable_fork_parent(self):
        """ Disable fork parent for a VM

        Returns:
                Task

        """

        self.vm_obj.DisableForkParent()

    def full_clone(
        self,
        dest_vm_name,
        host_obj,
        datastore_obj,
        vm_folder_obj,
        resource_pool_obj,
        cpu,
        mem,
    ):
        """ Clone a VM via full clone

        Args:
            dest_vm_name (str): Name of destination VM
            host_obj(vim.HostSystem): VM host destination
            datastore_obj (vim.Datastore): VM datastore destination
            vm_folder_obj (vim.Folder): VM folder destination
            resource_pool_obj (vim.ResourcePool): Resource Pool destination
            cpu (int): number of CPUs
            mem (int): memory size in MB

        Returns:
            Task

        """

        self.logger.info("Full cloning VM %s to %s" % (self.vm_obj.name, dest_vm_name))
        relocation_spec = vim.vm.RelocateSpec()
        relocation_spec.pool = resource_pool_obj
        relocation_spec.datastore = datastore_obj
        relocation_spec.host = host_obj
        clone_spec = vim.vm.CloneSpec()
        clone_spec.location = relocation_spec
        if cpu or mem:
            config_spec = vim.vm.ConfigSpec()
            config_spec.numCPUs = cpu
            config_spec.memoryMB = mem
            clone_spec.config = config_spec
        else:
            self.logger.debug("No hardware customization for the cloned VM")
        task = self.vm_obj.Clone(
            folder=vm_folder_obj, name=dest_vm_name, spec=clone_spec
        )
        return task

    def linked_clone(
        self, dest_vm, host_obj, folder_obj, resource_pool_obj, cpu, mem, power_on=True
    ):
        """ Clone a VM via linked clone

        Args:
            dest_vm (str): Name of destination VM
            host_obj (vim.HostSystem): VM host destination
            folder_obj (vim.Folder): VM folder destination
            resource_pool_obj (vim.ResourcePool): Resource Pool destination
            power_on (bool): whether enable power on after cloning

        Returns:
            Task

        """

        self.logger.info(
            "Linked cloning VM {0} to {1}".format(self.vm_obj.name, dest_vm)
        )
        relocation_spec = vim.vm.RelocateSpec()
        relocation_spec.pool = resource_pool_obj
        relocation_spec.host = host_obj
        relocation_spec.diskMoveType = "createNewChildDiskBacking"
        clone_spec = vim.vm.CloneSpec()
        clone_spec.location = relocation_spec
        if len(self.vm_obj.rootSnapshot) < 1:
            self.logger.info(
                "Creating a snapshot for VM for "
                "linked clone {0}".format(self.vm_obj.name)
            )
            task = self.vm_obj.CreateSnapshot_Task(
                name="snapshot0", memory=False, quiesce=False
            )
            GetWait().wait_for_tasks(
                [task],
                task_name="Take snapshot for "
                "template VM for "
                "enabling linked clone",
            )
        clone_spec.powerOn = power_on
        clone_spec.template = False
        clone_spec.snapshot = self.vm_obj.snapshot.rootSnapshotList[0].snapshot
        if cpu or mem:
            config_spec = vim.vm.ConfigSpec()
            config_spec.numCPUs = cpu
            config_spec.memoryMB = mem
            clone_spec.config = config_spec
        else:
            self.logger.debug("No hardware customization for the cloned VM")
        task = self.vm_obj.Clone(folder=folder_obj, name=dest_vm, spec=clone_spec)
        return task

    @staticmethod
    def _find_nearest_power_of_two(x):
        """ find nearest of power of two for a given int number

        Args:
            x (int)

        Returns:
            int: nearest power of two

        """

        return 1 << (x - 1).bit_length()

    def add_pci(self, pci, host_obj, vm_update, vm_status, mmio_size):
        """ Add a PCI device for a VM.
            If a PCI device has large BARs, it requires 64bit MMIO
            support and large enough MMIO mapping space. This method will add
            these two configurations by default and check uEFI installation.
            But haven't evaluated the impacts of
            adding these configurations for a PCI device which doesn't have
            large BARs. For more details, check the reference KB article.

        Args:
            pci (str): pci ID of the PCI device
            host_obj (vim.HostSystem): Host obj to locate the PCI device
            vm_update (ConfigVM): VM update obj
            vm_status (GetVM): VM status obj
            mmio_size (int): 64-bit MMIO space in GB

        Returns:
            list: a list of Task objects

        References:
            https://kb.vmware.com/s/article/2142307

        """

        self.logger.info("Adding PCI device {0} for {1}".format(pci, self.vm_obj.name))
        extra_config_key1 = "pciPassthru.64bitMMIOSizeGB"
        extra_config_key2 = "pciPassthru.use64bitMMIO"
        if mmio_size is None:
            mmio_size = 256
        tasks = []
        pci_obj = GetHost(host_obj).pci_obj(pci)
        # Convert decimal to hex for the device ID of PCI device
        device_id = hex(pci_obj.deviceId % 2 ** 16).lstrip("0x")
        if not vm_status.uefi():
            self.logger.warning(
                "VM {0} is not installed with UEFI. "
                "If PCI device has large BARs, "
                "UEFI installation is required.".format(self.vm_obj.name)
            )
        else:
            self.logger.info(
                "Good. VM {0} has UEFI " "installation.".format(self.vm_obj.name)
            )
        sys_id = vm_status.pci_id_sys_id_passthru()
        backing = vim.VirtualPCIPassthroughDeviceBackingInfo(
            deviceId=device_id,
            id=pci_obj.id,
            systemId=sys_id[pci_obj.id],
            vendorId=pci_obj.vendorId,
            deviceName=pci_obj.deviceName,
        )
        backing_obj = vim.VirtualPCIPassthrough(backing=backing)
        dev_config_spec = vim.VirtualDeviceConfigSpec(device=backing_obj)
        dev_config_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [dev_config_spec]
        tasks.append(self.vm_obj.ReconfigVM_Task(spec=config_spec))
        tasks.append(vm_update.add_extra(extra_config_key1, str(mmio_size)))
        tasks.append(vm_update.add_extra(extra_config_key2, "TRUE"))
        return tasks

    def remove_pci(self, pci, vm_status):
        """ Remove a PCI device from a VM

        Args:
            pci (str): pci ID of the PCI device
            vm_status (GetVM): the VM status obj

        Returns:
            Task

        """

        self.logger.info(
            "Removing PCI {0} from VM " "{1}".format(pci, self.vm_obj.name)
        )
        pci_obj = vm_status.pci_obj(pci)
        dev_config_spec = vim.VirtualDeviceConfigSpec()
        dev_config_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        dev_config_spec.device = pci_obj
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [dev_config_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def add_extra(self, entry, value):
        """ Add an extra advanced vmx entry for a VM

        Args:
            entry (str): extra config key
            value (str): extra config value

        Returns:
            Task

        """

        config_spec = vim.vm.ConfigSpec()
        self.logger.info("Adding/Updating extra config: {0} = {1}".format(entry, value))
        opt = vim.option.OptionValue()
        opt.key = entry
        opt.value = value
        config_spec.extraConfig = [opt]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def remove_extra(self, entry):
        """ Add an extra advanced vmx entry from a VM

        Args:
            entry (str): extra config key

        Returns:
            Task

        """

        config_spec = vim.vm.ConfigSpec()
        self.logger.info("Removing extra config {0}".format(entry))
        opt = vim.option.OptionValue()
        opt.key = entry
        opt.value = ""
        config_spec.extraConfig = [opt]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def add_vgpu(self, vgpu_profile):
        """ Add a vGPU profile for a VM

        Args:
            vgpu_profile (str): the name of vGPU profile to be added into a VM

        Returns:
            Task

        """

        self.logger.info(
            "Adding vGPU {0} for " "VM {1}".format(vgpu_profile, self.vm_obj.name)
        )
        backing = vim.VirtualPCIPassthroughVmiopBackingInfo(vgpu=vgpu_profile)
        backing_obj = vim.VirtualPCIPassthrough(backing=backing)
        dev_config_spec = vim.VirtualDeviceConfigSpec(device=backing_obj)
        dev_config_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [dev_config_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def remove_vgpu(self, vgpu_profile):
        """ Remove a vGPU profile for a VM

        Args:
            vgpu_profile (str): the name of vGPU profile to be removed from a VM

        Returns:
            Task

        """

        self.logger.info(
            "Removing vGPU %s from VM %s" % (vgpu_profile, self.vm_obj.name)
        )
        vm_status = GetVM(self.vm_obj)
        vgpu_obj = vm_status.vgpu_obj(vgpu_profile)
        dev_config_spec = vim.VirtualDeviceConfigSpec()
        dev_config_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        dev_config_spec.device = vgpu_obj
        config_spec = vim.vm.ConfigSpec()
        config_spec.deviceChange = [dev_config_spec]
        return self.vm_obj.ReconfigVM_Task(spec=config_spec)

    def execute_script(self, process_manager, script, username, password):
        """ Execute a post script for a VM
            First copy local script content to remote VM
            Then execute the script in remote VM
            Only works for Linux system

        Args:
            process_manager (GuestProcessManager):  A singleton managed object
                        that provides methods for guest process operations.
                        Retrieved from service content.
            script (str): the script to be executed. Should be in Path
            username (str): username for authentication
            password (str): password for authentication

        Returns:
            tuple:  pid, auth, self.vm_obj
                    where pid (long) is the pid of the program started
                    auth (vim.vm.guest.NamePasswordAuthentication) contains
                    guest OS authentication info
                    self.vm_obj (vim.VirtualMachine): the VM object

        References:
             pyvmomi/docs/vim/vm/guest/GuestOperationsManager.rst

        """

        auth = vim.vm.guest.NamePasswordAuthentication()
        auth.username = username
        auth.password = password
        try:
            copy_content = (
                "'"
                + open(script).read().replace("'", '"\'"')
                + "' >> "
                + os.path.basename(script)
            )
            program_spec = vim.vm.guest.ProcessManager.ProgramSpec()
            program_spec.programPath = "/bin/echo"
            program_spec.arguments = copy_content
            pid = process_manager.StartProgramInGuest(self.vm_obj, auth, program_spec)
            assert pid > 0
            program_spec.programPath = "/bin/sh"
            log_file = "/var/log/vhpc_toolkit.log"
            execute_content = os.path.basename(script) + " 2>&1 | tee " + log_file
            program_spec.arguments = execute_content
            pid = process_manager.StartProgramInGuest(self.vm_obj, auth, program_spec)
            assert pid > 0
            self.logger.info(
                "Script {0} is being executed in VM {1} guest OS "
                "and PID is {2}".format(os.path.basename(script), self.vm_obj.name, pid)
            )
        except IOError:
            self.logger.error("Can not open script {0}".format(script))
            raise SystemExit
        except AssertionError:
            self.logger.error("Script is not launched successfully.")
            raise SystemExit
        except vim.fault.InvalidGuestLogin as e:
            self.logger.error(e.msg)
            raise SystemExit
        else:
            return pid, auth, self.vm_obj


class ConfigHost(object):
    """
    A class for configuring host properties.

    """

    def __init__(self, host_obj):
        """

        Args:
            host_obj (vim.HostSystem): The HostSystem managed object type

        References:
            pyvmomi/docs/vim/HostSystem.rst

        """

        self.host_obj = host_obj
        self.logger = log.my_logger(name=self.__class__.__name__)

    def create_svs(self, svs_name, vmnic, num_ports=8):
        """ Create a standard virtual switch
            It calls AddVirtualSwitch method from HostNetworkSystem. It
            doesn't return a Task to track

        Args:
            svs_name (str): The name of SVS to be created.
            vmnic (str): The name of physical adapter to create the SVS
            num_ports (int): number of ports for the SVS

        Returns:
            None

        References:
            pyvmomi/docs/vim/host/NetworkSystem.rst

        """

        svs = vim.host.VirtualSwitch.Specification()
        svs.numPorts = num_ports
        svs.bridge = vim.host.VirtualSwitch.BondBridge(nicDevice=[vmnic])
        host_network_obj = self.host_obj.configManager.networkSystem
        host_network_obj.AddVirtualSwitch(vswitchName=svs_name, spec=svs)

    def destroy_svs(self, svs_name):
        """ Destroy a standard virtual switch

        Args:
            svs_name (str): The name of SVS to be destroyed

        Returns:
            None

        References:
            pyvmomi/docs/vim/host/NetworkSystem.rst

        """

        host_network_obj = self.host_obj.configManager.networkSystem
        host_network_obj.RemoveVirtualSwitch(vswitchName=svs_name)

    def create_pg_in_svs(self, svs_name, pg_name, vlan_id=0):
        """ Create a Port Group within standard virtual switch

        Args:
            svs_name (str): The name of SVS to create a port group
            pg_name (str): The name of port group to be created
            vlan_id (int): The VLAN ID for ports using this port group.

        Returns:
            None

        References:
            pyvmomi/docs/vim/host/NetworkSystem.rst
            pyvmomi/docs/vim/host/PortGroup.rst

        """

        pg_spec = vim.host.PortGroup.Specification()
        pg_spec.name = pg_name
        pg_spec.vlanId = vlan_id
        pg_spec.vswitchName = svs_name
        security_policy = vim.host.NetworkPolicy.SecurityPolicy()
        security_policy.allowPromiscuous = True
        security_policy.forgedTransmits = True
        security_policy.macChanges = False
        pg_spec.policy = vim.host.NetworkPolicy(security=security_policy)
        host_network_obj = self.host_obj.configManager.networkSystem
        host_network_obj.AddPortGroup(portgrp=pg_spec)

    def destroy_pg(self, pg_name):
        """ Destroy a Port Group from a Host

        Args:
            pg_name (str): The name of port group to be destroyed

        Returns:
            None

        API References:
            pyvmomi/docs/vim/host/NetworkSystem.rst
            pyvmomi/docs/vim/host/PortGroup.rst

        """

        host_network_obj = self.host_obj.configManager.networkSystem
        host_network_obj.RemovePortGroup(pgName=pg_name)


class ConfigDatacenter(object):
    """
    A class for configuring datacenter properties

    """

    def __init__(self, datacenter_obj):
        """

        Args:
            datacenter_obj (vim.Datacenter): the Datacenter managed object type

        API References:
            pyvmomi/docs/vim/Datacenter.rst

        """

        self.datacenter_obj = datacenter_obj
        self.logger = log.my_logger(name=self.__class__.__name__)

    def create_dvs(self, host_vmnics, dvs_name, num_uplinks=4):
        """ Create a distributed virtual switch within the datacenter

        Args:
            host_vmnics (dict): A dictionary storing {host_obj: vmnics}
                                where host_obj is vim.HostSystem type and
                                vmnics is a list of str for the names of
                                physical adapters.
            dvs_name (str): The name of the DVS to be created
            num_uplinks (int): Number of active uplinks

        Returns:
            Task

        References:
            pyvmomi/docs/vim/host/NetworkSystem.rst
            pyvmomi/docs/vim/host/PortGroup.rst

        """

        for network_obj in GetDatacenter(self.datacenter_obj).network_resources():
            if network_obj.name == dvs_name:
                self.logger.info("DVS {0} already exists".format(dvs_name))
                return
        host_cfgs = []
        for host_obj, vmnics in host_vmnics.items():
            uplinks = []
            if host_obj.runtime.connectionState != "connected":
                self.logger.error(
                    "Host {0} is not connected. Skipped".format(host_obj.name)
                )
                continue
            host_cfg = vim.dvs.HostMember.ConfigSpec()
            host_cfg.operation = vim.ConfigSpecOperation.add
            host_cfg.host = host_obj
            host_cfg.backing = vim.dvs.HostMember.PnicBacking()
            for pnic in GetHost(host_obj).pnics():
                for vmnic in vmnics:
                    if pnic.device == vmnic:
                        pnic_spec = vim.dvs.HostMember.PnicSpec()
                        pnic_spec.pnicDevice = pnic.device
                        uplinks.append(pnic_spec)
            host_cfg.backing.pnicSpec = uplinks
            host_cfgs.append(host_cfg)
        uplink_port_policy = vim.DistributedVirtualSwitch.NameArrayUplinkPortPolicy()
        uplnk_port_order = []
        for i in range(num_uplinks):
            name = "uplink%d" % (i + 1)
            uplink_port_policy.uplinkPortName.append(name)
            uplnk_port_order.append(name)
        string_policy = vim.StringPolicy()
        string_policy.value = "failover_explicit"
        uplink_port_order_policy = (
            vim.dvs.VmwareDistributedVirtualSwitch.UplinkPortOrderPolicy()
        )
        # activeUplinkPort: list of active uplink ports used for load balancing
        uplink_port_order_policy.activeUplinkPort = uplnk_port_order
        team = vim.dvs.VmwareDistributedVirtualSwitch.UplinkPortTeamingPolicy()
        team.policy = string_policy
        team.uplinkPortOrder = uplink_port_order_policy
        port_config_policy = (
            vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
        )
        port_config_policy.uplinkTeamingPolicy = team
        dvs_config_spec = vim.dvs.VmwareDistributedVirtualSwitch.ConfigSpec()
        dvs_config_spec.name = dvs_name
        dvs_config_spec.host = host_cfgs
        dvs_config_spec.defaultPortConfig = port_config_policy
        dvs_config_spec.lacpApiVersion = (
            vim.dvs.VmwareDistributedVirtualSwitch.LacpApiVersion.multipleLag
        )
        dvs_config_spec.numStandalonePorts = num_uplinks
        dvs_create_spec = vim.DistributedVirtualSwitch.CreateSpec(
            configSpec=dvs_config_spec
        )
        task = self.datacenter_obj.networkFolder.CreateDVS_Task(dvs_create_spec)
        return task


class ConfigDVS(object):
    """
    A class for configuring distributed virtual switch (DVS) properties

    """

    def __init__(self, dvs_obj):
        """

        Args:
            dvs_obj (vim.dvs.VmwareDistributedVirtualSwitch):
                    distributed virtual switch object

        References:
            pyvmomi/docs/vim/DistributedVirtualSwitch.rst

        """

        self.dvs_obj = dvs_obj

    def create_pg_in_dvs(self, dvs_pg_name, num_ports=1):
        """ Create a port group in the DVS.

        Args:
            dvs_pg_name (str): the port group name to be created
            num_ports (int): number of ports in this port group

        Returns:
            Task

        """

        dpg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
        dpg_spec.name = dvs_pg_name
        dpg_policy = vim.dvs.DistributedVirtualPortgroup.PortgroupPolicy()
        dpg_spec.policy = dpg_policy
        dpg_spec.numPorts = num_ports
        dpg_spec.type = "earlyBinding"
        task = self.dvs_obj.AddDVPortgroup_Task(spec=[dpg_spec])
        return task

    def destroy_dvs(self):
        """ Destroy the DVS

        Returns:
            Task

        """

        task = self.dvs_obj.Destroy_Task()
        return task


class ConfigCluster(object):
    """
    A class for configuring cluster properties

    """

    def __init__(self, cluster_obj):
        """

        Args:
            cluster_obj [vim.Cluster]: a Cluster object

        """

        self.cluster_obj = cluster_obj

    def enable_drs(self):
        """ enable DRS for the cluster

        Todo:
           To be implemented

        """

        pass

    def disable_drs(self):
        """ disable DRS for the cluster

        Todo:
           To be implemented

        """

        pass
