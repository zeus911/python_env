# -*- coding: utf-8 -*-
import logging
import os

class vlan():
    @staticmethod
    def add_vlan(id, iface="eth0"):
        os.popen("vconfig add %s %s" % (iface, id)).read()
        logging.debug("add %s.%s" % (iface, id))

    @staticmethod
    def set_ip_vlan(id, ip, iface="eth0"):
        iface = "%s.%s" % (iface, id)
        res = os.popen("ifconfig %s %s" % (iface, ip)).read()
        logging.debug("configure ip for %s" % res)

    @staticmethod
    def set_arp_ignore(iface="eth0"):
        ignore_cmd = "echo 1 > /proc/sys/net/ipv4/conf/all/arp_ignore"
        os.popen(ignore_cmd).read()
        logging.debug("set arp_ignore of %s" % iface)

    @staticmethod
    def remove_vlan(id, iface="eth0"):
        rem_vlan_cmd = "if [[ -e /proc/net/vlan/%s ]];then vconfig rem %s;fi"
        iface = "%s.%s" % (iface, id)
        os.popen(rem_vlan_cmd % (iface, iface)).read()
        logging.debug("remove vlan %s" % iface)