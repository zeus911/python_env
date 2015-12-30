# -*- coding: utf-8 -*-


import os
import parted
from errors import *
import utils.sysblock as sysblock
from diskdevice import Disk
from lvmdevice import VolumeGroup, LogicalVolume
from partition import *
import parteddata as parteddata


import logging
log = logging.getLogger("storage")


class Storage(object):
    _devices = []


    def __init__(self):
        self.populate()

    def _vgs(self):
        """ VGs' Name dict to access VG"""
        vgs = {}
        for vg in self.volumeGroups:
            if vg.name in vgs:
                raise ValueError("Duplicate VG in Volume Groups")
            vgs[vg.name] = vg

        return vgs

    def populate(self):
        if sysblock.init_disks():
            for disk in sysblock.disks:
                if isinstance(disk, Disk):
                    self._devices.append(disk)
                else:
                    raise rror("Filling Disk failed!")

        if sysblock.init_vgs():
            print "LVM BULUNDU"
            for vg in sysblock.vgs:
                if isinstance(vg, VolumeGroup):
                    #vg = VolumeGroup(name=info[0], size=info[1], uuid=info[2], maxPV=info[3], pvCount=info[4], peSize=info[5], peCount=info[6], peFree=info[7], freespace=info[8], maxLV=info[9], existing=1)
                    self._devices.append(vg)
                else:
                    raise rror("Filling Volume Group Failed!")

    @property
    def disks(self):
        return [d for d in self._devices if d.type == parteddata.disk]

    @property
    def volumeGroups(self):
        return [d for d in self._devices if d.type == parteddata.volumeGroup]

    @property
    def logicalVolumes(self):
        lvs = []
        for vg in self.volumeGroups:
            lvs.extend(vg.lvs)
        return lvs

    def physicalVolumes(self, disk):
        _physicalVolumes = []

        for part in disk.partitions:
            if parteddata.physicalVolume == part.type:
                print "disk.name %s part.name %s" % (disk.name,part.name)
                _physicalVolumes.append(part)

        return _physicalVolumes



    def diskPartitions(self, disk):
        return disk.partitions

    def getPartition(self, disk, num):
        for part in self.diskPartitions(disk):
            if part.minor == num:
                return part
        return None

    def commitToDisk(self, disk):
        self._diskTable[disk].commit()
        for partition in self.diskPartitions(disk):
            partition.exists = True

    ##
    # Add (create) a new partition to the device
    # @param part: parted partition; must be parted.PARTITION_FREESPACE
    # @param type: parted partition type (eg. parted.PARTITION_PRIMARY)
    # @param fs: filesystem.FileSystem or file system name (like "ext3")
    # @param size_mb: size of the partition in MBs.
    def addPartition(self, disk, partition, artitionType, filesystem, size, flags = [], manualGeomStart = None):

        size = int((size * MEGABYTE) / disk.sectorSize)

        if isinstance(filesystem, str):
            filesystem = getFilesystem(filesystem)

        if isinstance(filesystem, FileSystem):
            filesystemType = filesystem.fileSystemType
        else:
            filesystemType = None

        # Don't set bootable flag if there is already a bootable
        # partition in this disk. See bug #2217
        if (parted.PARTITION_BOOT in flags) and disk.hasBootablePartition():
            flags = list(set(flags) - set([parted.PARTITION_BOOT]))

        if not partition.partition:
            partion = disk.__getLargestFreePartition()

        if not manualGeomStart:
            geom = partition.partition.geometry
            if geom.length >= size:
                if not disk.addPartition(artitionType, filesystem, geom.start, geom.start + size,flags):
                    raise DeviceError, ("Not enough free space on %s to create new partition" % self.getPath())
        else:
            if not disk.addPartition(type,filesystem,manualGeomStart,manualGeomStart + size, flags):
                raise DeviceError, ("Not enough free space on %s to create new partition" % self.getPath())


    def deletePartition(self, disk, partition):
        if not disk.deletePartition(partition.partition):
            raise rror("Partition delete failed!")

        return True

    def deleteAllPartitions(self, disk):
        if not disk.deleteAllPartition():
            raise rror("All Partitions delete failed!")
        return True

    def resizePartition(self, disk, partition, filesystem, size):
        if isinstance(filesystem, str):
            filesystem = getFilesystem(filesystem)
        else:
            filesystem = filesystem

        if not isinstance(filesystem, FileSystem):
            raise rror, "filesystem is None, can't resize"

        if not filesystem.resize(size, partition.path):
            raise rror, "fs.resize ERROR"
        else:
           fileSystem = partition.getFileSystemType()
           if not disk.resizePartition(filesystem,size,partition.partition):
               raise rror("partition.resize failed!")
           else:
               return True

    def removeVG(self, vg):
        pass

    def removeLV(self, lv):
        """
            logicalVolume -- LV' name
        """
        if not isinstance(lv, LogicalVolume):
            raise ValueError("lv parameter must be type of lvmdevice.LogicalVolume")
        else:
            lv.destroy()


