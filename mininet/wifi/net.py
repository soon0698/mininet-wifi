"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)"""

import os
import random
import re
import sys
import select
import signal
from time import sleep
from itertools import chain, groupby
from math import ceil
from six import string_types
from sys import version_info as py_version_info

from mininet.cli import CLI
from mininet.term import cleanUpScreens, makeTerms
from mininet.net import Mininet
from mininet.node import (Node, Host, OVSKernelSwitch,
                          DefaultController, Controller)
from mininet.util import (quietRun, fixLimits, numCores, ensureRoot,
                          macColonHex, ipStr, ipParse, netParse, ipAdd,
                          waitListening)
from mininet.link import Link, Intf, TCLink, TCULink
from mininet.nodelib import NAT
from mininet.log import info, error, debug, output, warn

from mininet.wifi.node import AccessPoint, AP, Station, Car, \
    OVSKernelAP, physicalAP
from mininet.wifi.wmediumdConnector import WmediumdStarter, WmediumdServer, \
    error_prob, snr, interference
from mininet.wifi.link import wirelessLink, wmediumd, Association, \
    _4address, TCWirelessLink, TCLinkWirelessStation,\
    wifiDirectLink, adhoc, mesh, physicalMesh, physicalWifiDirectLink
from mininet.wifi.devices import GetRate, GetRange, GetTxPower
from mininet.wifi.mobility import mobility
from mininet.wifi.plot import plot2d, plot3d, plotGraph
from mininet.wifi.module import module
from mininet.wifi.propagationModels import propagationModel
from mininet.wifi.vanet import vanet
from mininet.sixLoWPAN.net import Mininet_6LoWPAN
from mininet.sixLoWPAN.module import module as sixLoWPAN_module
from mininet.sixLoWPAN.link import sixLoWPANLink

sys.path.append(str(os.getcwd()) + '/mininet/')
from mininet.sumo.runner import sumo


class Mininet_wifi(Mininet):

    def __init__(self, topo=None, switch=OVSKernelSwitch,
                 accessPoint=OVSKernelAP, host=Host, station=Station,
                 car=Car, controller=DefaultController,
                 link=TCWirelessLink, intf=Intf, build=True, xterms=False,
                 ipBase='10.0.0.0/8', inNamespace=False,
                 autoSetMacs=False, autoStaticArp=False, autoPinCpus=False,
                 listenPort=None, waitConnected=False, ssid="new-ssid",
                 mode="g", channel="1", wmediumd_mode=snr,
                 fading_coefficient=0, autoAssociation=True,
                 allAutoAssociation=True, driver='nl80211',
                 autoSetPositions=False, configureWiFiDirect=False,
                 configure4addr=False, defaultGraph=False,
                 noise_threshold=-91, cca_threshold=-90,
                 rec_rssi=False, disable_tcp_checksum=False, ifb=False,
                 max_sector=4, sector=0, side_dB = -5, main_dB = -20):
        """Create Mininet object.
           topo: Topo (topology) object or None
           switch: default Switch class
           host: default Host class/constructor
           controller: default Controller class/constructor
           link: default Link class/constructor
           intf: default Intf class/constructor
           ipBase: base IP address for hosts,
           build: build now from topo?
           xterms: if build now, spawn xterms?
           cleanup: if build now, cleanup before creating?
           inNamespace: spawn switches and controller in net namespaces?
           autoSetMacs: set MAC addrs automatically like IP addresses?
           autoStaticArp: set all-pairs static MAC addrs?
           autoPinCpus: pin hosts to (real) cores (requires CPULimitedHost)?
           listenPort: base listening port to open; will be incremented for
               each additional switch in the net if inNamespace=False"""
        self.topo = topo
        self.switch = switch
        self.host = host
        self.station = station
        self.accessPoint = accessPoint
        self.car = car
        self.controller = controller
        self.link = link
        self.intf = intf
        self.ipBase = ipBase
        self.ipBaseNum, self.prefixLen = netParse(self.ipBase)
        self.nextIP = 1  # start for address allocation
        self.nextPosition = 1 # start for position allocation
        self.repetitions = 1 # mobility: number of repetitions
        self.inNamespace = inNamespace
        self.xterms = xterms
        self.autoSetMacs = autoSetMacs
        self.autoSetPositions = autoSetPositions
        self.autoStaticArp = autoStaticArp
        self.autoPinCpus = autoPinCpus
        self.numCores = numCores()
        self.nextCore = 0  # next core for pinning hosts to CPUs
        self.listenPort = listenPort
        self.waitConn = waitConnected
        self.ssid = ssid
        self.mode = mode
        self.wmediumd_mode = wmediumd_mode
        self.channel = channel
        self.nameToNode = {}  # name to Node (Host/Switch) objects
        self.aps = []
        self.controllers = []
        self.hosts = []
        self.links = []
        self.cars = []
        self.carsSW = []
        self.carsSTA = []
        self.switches = []
        self.stations = []
        self.sixLP = []
        self.walls = []
        self.terms = []  # list of spawned xterm processes
        self.driver = driver
        self.autoAssociation = autoAssociation # does not include mobility
        self.allAutoAssociation = allAutoAssociation # includes mobility
        self.mobilityKwargs = ''
        self.isMobilityModel = False
        self.isMobility = False
        self.ppm_is_set = False
        self.alreadyPlotted = False
        self.DRAW = False
        self.ifb = ifb #Support to Intermediate Functional Block (IFB) Devices
        self.isVanet = False
        self.cca_threshold = cca_threshold
        self.configureWiFiDirect = configureWiFiDirect
        self.configure4addr = configure4addr
        self.fading_coefficient = fading_coefficient
        self.noise_threshold = noise_threshold
        self.mobilityparam = dict()
        self.AC = None
        self.alt_module = None
        self.rec_rssi = rec_rssi
        self.disable_tcp_checksum = disable_tcp_checksum
        self.plot = plot2d
        self.seed = 1
        self.n_radios = 0
        self.min_x = 0
        self.min_y = 0
        self.min_z = 0
        self.max_x = 0
        self.max_y = 0
        self.max_z = 0
        self.nroads = 0
        self.conn = {}
        self.wlinks = []
	self.max_sector = 0
        self.sector = 0
        self.side_dB = 0
        slef.main_dB = 0
        Mininet_wifi.init()  # Initialize Mininet if necessary

        if not allAutoAssociation:
            self.autoAssociation = False
            mobility.allAutoAssociation = False

        if defaultGraph:
            self.defaultGraph()

        self.built = False
        if topo and build:
            self.build()

    def waitConnected(self, timeout=None, delay=.5):
        """wait for each switch to connect to a controller,
           up to 5 seconds
           timeout: time to wait, or None to wait indefinitely
           delay: seconds to sleep per iteration
           returns: True if all switches are connected"""
        info('*** Waiting for switches/aps to connect\n')
        time = 0
        L2nodes = self.switches + self.aps
        remaining = list(L2nodes)
        while True:
            for switch in tuple(remaining):
                if switch.connected():
                    info('%s ' % switch)
                    remaining.remove(switch)
            if not remaining:
                info('\n')
                return True
            if timeout is not None and time > timeout:
                break
            sleep(delay)
            time += delay
        warn('Timed out after %d seconds\n' % time)
        for switch in remaining:
            if not switch.connected():
                warn('Warning: %s is not connected to a controller\n'
                     % switch.name)
            else:
                remaining.remove(switch)
        return not remaining

    def delNode(self, node, nodes=None):
        """Delete node
           node: node to delete
           nodes: optional list to delete from (e.g. self.hosts)"""
        if nodes is None:
            nodes = (self.hosts if node in self.hosts else
                     (self.switches if node in self.switches else
                      (self.controllers if node in self.controllers else [])))
        node.stop(deleteIntfs=True)
        node.terminate()
        nodes.remove(node)
        del self.nameToNode[node.name]

    def addStation(self, name, cls=None, **params):
        """Add Station.
           name: name of station to add
           cls: custom host class/constructor (optional)
           params: parameters for station
           returns: added station"""
        # Default IP and MAC addresses
        defaults = {'ip': ipAdd(self.nextIP,
                                ipBaseNum=self.ipBaseNum,
                                prefixLen=self.prefixLen) +
                          '/%s' % self.prefixLen,
                    'channel': self.channel,
                    'mode': self.mode,
                    'max_sector': self.max_sector,
                    'sector': self.sector,
                    'main_dB': self.main_dB,
                    'side_dB': self.side_dB
                   }
        defaults.update(params)

        if self.autoSetPositions:
            defaults['position'] = ('%s,0,0' % self.nextPosition)
        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP)
        if self.autoPinCpus:
            defaults['cores'] = self.nextCore
            self.nextCore = (self.nextCore + 1) % self.numCores
        self.nextIP += 1
        self.nextPosition += 1

        if not cls:
            cls = self.station
        sta = cls(name, **defaults)

        self.addParameters(sta, self.autoSetMacs, defaults)

        if 'type' in params and params['type'] is 'ap':
            sta.func[0] = 'ap'
            if 'ssid' in params:
                sta.params['ssid'] = []
                sta.params['ssid'].append('')
                sta.params['ssid'][0] = params['ssid']

        self.stations.append(sta)
        self.nameToNode[name] = sta
        return sta

    def add6LoWPAN(self, name, cls=None, **params):
        node = Mininet_6LoWPAN.add6LoWPAN(name, cls, **params)
        self.sixLP.append(node)
        self.nameToNode[name] = node
        return node

    def addCar(self, name, cls=None, **params):
        """Add Car.
           name: name of vehicle to add
           cls: custom host class/constructor
           params: parameters for car
           returns: added car"""
        # Default IP and MAC addresses
        defaults = {'ip': ipAdd(self.nextIP,
                                ipBaseNum=self.ipBaseNum,
                                prefixLen=self.prefixLen) +
                          '/%s' % self.prefixLen,
                    'channel': self.channel,
                    'mode': self.mode,
                    'ssid': self.ssid}

        if self.autoSetMacs:
            defaults['mac'] = macColonHex(self.nextIP)
        if self.autoPinCpus:
            defaults['cores'] = self.nextCore
            self.nextCore = (self.nextCore + 1) % self.numCores
        defaults.update(params)

        self.nextIP += 1
        if not cls:
            cls = self.car
        car = cls(name, **defaults)

        self.nameToNode[name] = car
        self.addParameters(car, self.autoSetMacs, defaults)

        carsta = self.addStation(name + 'STA', **defaults)
        carsta.pexec('ip link set lo up')
        car.params['carsta'] = carsta
        self.carsSTA.append(carsta)
        switchName = car.name + 'SW'
        carsw = self.addSwitch(switchName, inband=True)
        self.carsSW.append(carsw)
        self.cars.append(car)

        if 'func' in car.params and car.params['func'] is 'adhoc':
            car.params['ssid'] = 'adhoc-ssid'
            car.func.append('adhoc')
        else:
            car.params['ssid'] = 'mesh-ssid'
            car.func.append('mesh')
        self.isVanet = True
        return car

    def addAccessPoint(self, name, cls=None, **params):
        """Add AccessPoint.
           name: name of accesspoint to add
           cls: custom switch class/constructor (optional)
           returns: added acesspoint
           side effect: increments listenPort var ."""
        defaults = {'listenPort': self.listenPort,
                    'inNamespace': self.inNamespace,
                    'ssid': self.ssid,
                    'channel': self.channel,
                    'mode': self.mode,
                    'max_sector': self.max_sector,
                    'sector': self.sector,
                    'main_dB': self.main_dB,
                    'side_dB': self.side_dB
                   }

        defaults.update(params)

        if self.autoSetPositions:
            defaults['position'] = ('0,%s,0' % self.nextPosition)
            self.nextPosition += 1

        wlan = None
        if cls == physicalAP:
            wlan = ("%s" % params.pop('phywlan', {}))
            cls = self.accessPoint
        if not cls:
            cls = self.accessPoint
        ap = cls(name, **defaults)

        if not self.inNamespace and self.listenPort:
            self.listenPort += 1

        if self.inNamespace or ('inNamespace' in params
                                and params['inNamespace'] is True):
            ap.params['inNamespace'] = True

        self.nameToNode[name] = ap

        if wlan:
            ap.params['phywlan'] = wlan

        self.addParameters(ap, self.autoSetMacs, defaults, mode='master')
        if 'type' in params and params['type'] is 'mesh':
            ap.func[1] = 'mesh'
            ap.ifaceToAssociate = 1

        self.aps.append(ap)
        return ap

    def addNAT(self, name='nat0', connect=True, inNamespace=False,
               **params):
        """Add a NAT to the Mininet network
           name: name of NAT node
           connect: switch to connect to | True (s1) | None
           inNamespace: create in a network namespace
           params: other NAT node params, notably:
               ip: used as default gateway address"""
        nat = self.addHost(name, cls=NAT, inNamespace=inNamespace,
                           subnet=self.ipBase, **params)
        # find first switch and create link
        if connect:
            if not isinstance(connect, Node):
                # Use first switch if not specified
                connect = self.switches[0]
            # Connect the nat to the switch
            self.addLink(nat, connect)
            # Set the default route on hosts
            natIP = nat.params['ip'].split('/')[0]
            for host in self.hosts:
                if host.inNamespace:
                    host.setDefaultRoute('via %s' % natIP)
        return nat

    # BL: We now have four ways to look up nodes
    # This may (should?) be cleaned up in the future.
    def getNodeByName(self, *args):
        "Return node(s) with given name(s)"
        if len(args) is 1:
            return self.nameToNode[args[0]]
        return [self.nameToNode[n] for n in args]

    def get(self, *args):
        "Convenience alias for getNodeByName"
        return self.getNodeByName(*args)

    # Even more convenient syntax for node lookup and iteration
    def __getitem__(self, key):
        "net[ name ] operator: Return node with given name"
        return self.nameToNode[key]

    def __delitem__(self, key):
        "del net[ name ] operator - delete node with given name"
        self.delNode(self.nameToNode[key])

    def __iter__(self):
        "return iterator over node names"
        for node in chain(self.hosts, self.switches, self.controllers,
                          self.stations, self.carsSTA, self.aps, self.sixLP):
            yield node.name

    def __len__(self):
        "returns number of nodes in net"
        return (len(self.hosts) + len(self.switches) +
                len(self.controllers) + len(self.stations) +
                len(self.carsSTA) + len(self.aps) + len(self.sixLP))

    def __contains__(self, item):
        "returns True if net contains named node"
        return item in self.nameToNode

    def keys(self):
        "return a list of all node names or net's keys"
        return list(self)

    def values(self):
        "return a list of all nodes or net's values"
        return [self[name] for name in self]

    def items(self):
        "return (key,value) tuple list for every node in net"
        return zip(self.keys(), self.values())

    @staticmethod
    def randMac():
        "Return a random, non-multicast MAC address"
        return macColonHex(random.randint(1, 2 ** 48 - 1) & 0xfeffffffffff |
                           0x020000000000)

    def setModule(self, moduleDir):
        "set an alternative module rather than mac80211_hwsim"
        self.alt_module = moduleDir

    def addLink(self, node1, node2=None, port1=None, port2=None,
                cls=None, **params):
        """"Add a link from node1 to node2
            node1: source node (or name)
            node2: dest node (or name)
            port1: source port (optional)
            port2: dest port (optional)
            cls: link class (optional)
            params: additional link params (optional)
            returns: link object"""

        # Accept node objects or names
        node1 = node1 if not isinstance(node1, string_types) else self[node1]
        node2 = node2 if not isinstance(node2, string_types) else self[node2]
        options = dict(params)
        self.conn.setdefault('src', [])
        self.conn.setdefault('dst', [])
        self.conn.setdefault('ls', [])

        cls = self.link if cls is None else cls

        if cls == mesh or cls == physicalMesh:
            isAP=False
            if isinstance(node1, AP):
                isAP=True
            cls(node=node1, isAP=isAP, **params)
        elif cls == adhoc:
            cls(node=node1, link=self.link, **params)
        elif cls == wifiDirectLink or cls == physicalWifiDirectLink:
            link = cls(node=node1, port=port1, **params)
            return link
        elif cls == sixLoWPANLink:
            link = cls(node=node1, port=port1, **params)
            self.links.append(link)
            return link
        elif cls == _4address:
            if 'position' in node1.params and 'position' in node2.params:
                self.conn['src'].append(node1)
                self.conn['dst'].append(node2)
                self.conn['ls'].append('--')

            if self.wmediumd_mode == interference:
                link = cls(node1, node2)
                self.links.append(link)
                return link
            else:
                dist = node1.get_distance_to(node2)
                if dist <= node1.params['range'][0]:
                    link = cls(node1, node2)
                    self.links.append(link)
                    return link
        elif ((node1 in self.stations and node2 in self.aps)
              or (node2 in self.stations and node1 in self.aps)) and \
                        'link' not in options:

            sta = node2
            ap = node1
            sta_wlan = None
            ap_wlan = 0

            if port2:
                sta_wlan = port2
            if port1:
                ap_wlan = port1

            if node1 in self.stations and node2 in self.aps:
                sta = node1
                ap = node2
                if port1:
                    sta_wlan = port1
                if port2:
                    ap_wlan = port2

            wlan = sta.ifaceToAssociate
            if sta_wlan:
                wlan = sta_wlan
            # If sta/ap have position
            doAssociation = True
            if 'position' in sta.params and 'position' in ap.params:
                dist = sta.get_distance_to(ap)
                if dist > ap.params['range'][ap_wlan]:
                    doAssociation = False
            if doAssociation:
                sta.params['mode'][wlan] = ap.params['mode'][ap_wlan]
                sta.params['channel'][wlan] = ap.params['channel'][ap_wlan]
                enable_wmediumd = False
                enable_interference = False
                if self.link == wmediumd:
                    enable_wmediumd = True
                if self.wmediumd_mode == interference:
                    enable_interference = True
                Association.associate(sta, ap, enable_wmediumd,
                                      enable_interference, wlan, ap_wlan)
                if 'TCWirelessLink' in str(self.link.__name__):
                    if 'bw' not in params and 'bw' not in str(cls) and \
                            not self.ifb:
                        value = self.getDataRate(sta, ap, wlan)
                        bw = value.rate
                        params['bw'] = bw
                    # tc = True, this is useful only to apply tc configuration
                    link = cls(name=sta.params['wlan'][wlan], node=sta,
                               tc=True, **params)
                    #self.links.append(link)
                    return link
            if self.link == wmediumd:
                if self.wmediumd_mode == error_prob:
                    wmediumd.wlinks.append([sta, ap, params['error_prob']])
                elif self.wmediumd_mode != interference:
                    wmediumd.wlinks.append([sta, ap])
        else:
            if 'link' in options:
                options.pop('link', None)

            if 'position' in node1.params and 'position' in node2.params:
                self.conn['src'].append(node1)
                self.conn['dst'].append(node2)
                self.conn['ls'].append('-')
            # Port is optional
            if port1 is not None:
                options.setdefault('port1', port1)
            if port2 is not None:
                options.setdefault('port2', port2)

            # Set default MAC - this should probably be in Link
            options.setdefault('addr1', self.randMac())
            options.setdefault('addr2', self.randMac())

            if not cls or cls == wmediumd or cls == TCWirelessLink:
                cls = TCLink
            if self.disable_tcp_checksum:
                cls = TCULink

            cls = self.link if cls is None else cls
            link = cls(node1, node2, **options)
            self.links.append(link)
            return link

    def delLink(self, link):
        "Remove a link from this network"
        link.delete()
        self.links.remove(link)

    def linksBetween(self, node1, node2):
        "Return Links between node1 and node2"
        return [link for link in self.links
                if (node1, node2) in (
                    (link.intf1.node, link.intf2.node),
                    (link.intf2.node, link.intf1.node))]

    def delLinkBetween(self, node1, node2, index=0, allLinks=False):
        """Delete link(s) between node1 and node2
           index: index of link to delete if multiple links (0)
           allLinks: ignore index and delete all such links (False)
           returns: deleted link(s)"""
        links = self.linksBetween(node1, node2)
        if not allLinks:
            links = [links[index]]
        for link in links:
            self.delLink(link)
        return links

    def configHosts(self):
        "Configure a set of hosts."
        hosts = self.hosts + self.stations
        for host in hosts:
            # info( host.name + ' ' )
            intf = host.defaultIntf()
            if intf:
                host.configDefault()
            else:
                # Don't configure nonexistent intf
                host.configDefault(ip=None, mac=None)
                # You're low priority, dude!
                # BL: do we want to do this here or not?
                # May not make sense if we have CPU lmiting...
                # quietRun( 'renice +18 -p ' + repr( host.pid ) )
                # This may not be the right place to do this, but
                # it needs to be done somewhere.
                # info( '\n' )

    def buildFromTopo(self, topo=None):
        """Build mininet from a topology object
           At the end of this function, everything should be connected
           and up."""
        Association.printCon = False

        info('*** Creating network\n')
        if not self.controllers and self.controller:
            # Add a default controller
            info('*** Adding controller\n')
            classes = self.controller
            if not isinstance(classes, list):
                classes = [classes]
            for i, cls in enumerate(classes):
                # Allow Controller objects because nobody understands partial()
                if isinstance(cls, Controller):
                    self.addController(cls)
                else:
                    self.addController('c%d' % i, cls)

        info('*** Adding hosts/stations:\n')
        for hostName in topo.hosts():
            if 'wifi' in str(self.topo):
                self.addStation(hostName, **topo.nodeInfo(hostName))
            else:
                self.addHost(hostName, **topo.nodeInfo(hostName))
            info(hostName + ' ')

        info('\n*** Adding switches/access points:\n')
        for switchName in topo.switches():
            # A bit ugly: add batch parameter if appropriate
            params = topo.nodeInfo(switchName)
            cls = params.get('cls', self.switch)
            if hasattr(cls, 'batchStartup'):
                params.setdefault('batch', True)
            if 'ap' in str(switchName):
                self.addAccessPoint(switchName, **params)
            else:
                self.addSwitch(switchName, **params)
            info(switchName + ' ')

        info('\n*** Configuring wifi nodes...\n')
        self.configureWifiNodes()

        info('\n*** Adding link(s):\n')
        for srcName, dstName, params in topo.links(
                sort=True, withInfo=True):
            self.addLink(**params)
            info('(%s, %s) ' % (srcName, dstName))
        info('\n')

    def configureControlNetwork(self):
        "Control net config hook: override in subclass"
        raise Exception('configureControlNetwork: '
                        'should be overriden in subclass', self)

    def create_vanet_link(self):
        for idx, car in enumerate(self.cars):
            self.addLink(self.carsSTA[idx], self.carsSW[idx])
            self.addLink(car, self.carsSW[idx])

    def build(self):
        "Build mininet."
ble_tcp_checksum=False, ifb=False,
                 sector=0, side):

        if (self.configure4addr or self.configureWiFiDirect
                or self.wmediumd_mode == error_prob) and self.link == wmediumd:
            wmediumd(self.fading_coefficient, self.noise_threshold,
                     self.stations, self.aps, propagationModel)
            if self.configure4addr:
                for sta in self.stations:
                    x = sta.params['position'][0]
                    y = sta.params['position'][1]
                    z = sta.params['position'][2]
                    sta.setPosition('%s,%s,%s' % (x,y,z))

        if self.inNamespace:
            self.configureControlNetwork()
        info('*** Configuring nodes\n')
        self.configHosts()
        if self.xterms:
            self.startTerms()
        if self.autoStaticArp:
            self.staticArp()

        nodes = self.stations
        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                if not isinstance(node, AP) and node.func[0] != 'ap' and \
                        node.func[wlan] != 'mesh' and \
                                node.func[wlan] != 'adhoc' and \
                                node.func[wlan] != 'wifiDirect':
                    if not node.autoTxPower:
                        node.params['range'][wlan] = \
                            int(node.params['range'][wlan]) / 5

        if self.allAutoAssociation:
            if self.autoAssociation and not self.isMobility:
                self.auto_association()
        if self.isMobility:
            if self.isMobilityModel or self.isVanet:
                self.mobilityKwargs['mobileNodes'] = self.getMobileNodes()
                self.start_mobility(**self.mobilityKwargs)
            else:
                self.mobilityKwargs['plotNodes'] = self.plot_nodes()
                self.stop_mobility(**self.mobilityKwargs)
        else:
            if self.getPropagationModel() is 'logNormalShadowing':
                import threading
                thread = threading.Thread(target=self.plot_dynamic)
                thread.daemon = True
                thread.start()
            elif self.DRAW and not self.alreadyPlotted:
                plotNodes = self.plot_nodes()
                self.plotCheck(plotNodes)
        self.built = True

    def plot_nodes(self):
        other_nodes = self.hosts + self.switches + self.controllers
        plotNodes = []
        for node in other_nodes:
            if hasattr(node, 'plotted') and node.plotted is True:
                plotNodes.append(node)
        return plotNodes

    def startTerms(self):
        "Start a terminal for each node."
        if 'DISPLAY' not in os.environ:
            error("Error starting terms: Cannot connect to display\n")
            return
        info("*** Running terms on %s\n" % os.environ['DISPLAY'])
        cleanUpScreens()
        self.terms += makeTerms(self.controllers, 'controller')
        self.terms += makeTerms(self.switches, 'switch')
        self.terms += makeTerms(self.hosts, 'host')
        self.terms += makeTerms(self.stations, 'station')
        self.terms += makeTerms(self.aps, 'ap')
        self.terms += makeTerms(self.sixLP, 'sixLP')

    def stopXterms(self):
        "Kill each xterm."
        for term in self.terms:
            os.kill(term.pid, signal.SIGKILL)
        cleanUpScreens()

    def staticArp(self):
        "Add all-pairs ARP entries to remove the need to handle broadcast."
        for src in self.hosts:
            for dst in self.hosts:
                if src != dst:
                    src.setARP(ip=dst.IP(), mac=dst.MAC())

    def start(self):
        "Start controller and switches."
        if not self.built:
            self.build()
        info('*** Starting controller(s)\n')
        for controller in self.controllers:
            info(controller.name + ' ')
            controller.start()
        info('\n')

        info('*** Starting switches and/or access points\n')
        nodesL2 = self.switches + self.aps
        for switch in nodesL2:
            info(switch.name + ' ')
            switch.start(self.controllers)

        started = {}
        for swclass, switches in groupby(
                sorted(nodesL2, key=type), type):
            switches = tuple(switches)
            if hasattr(swclass, 'batchStartup'):
                success = swclass.batchStartup(switches)
                started.update({s: s for s in success})
        info('\n')
        if self.waitConn:
            self.waitConnected()

    def roads(self, nroads):
        "Number of roads"
        self.nroads = nroads

    def stop(self):
        'Stop Mininet-WiFi'
        self.stopGraphParams()
        info('*** Stopping %i controllers\n' % len(self.controllers))
        for controller in self.controllers:
            info(controller.name + ' ')
            controller.stop()
        info('\n')
        if self.terms:
            info('*** Stopping %i terms\n' % len(self.terms))
            self.stopXterms()
        info('*** Stopping %i links\n' % len(self.links))
        for link in self.links:
            info('.')
            link.stop()
        info('\n')
        info('*** Stopping switches/access points\n')
        stopped = {}
        nodesL2 = self.switches + self.aps
        if py_version_info < (3, 0):
            for swclass, switches in groupby(
                    sorted(nodesL2, key=type), type):
                switches = tuple(switches)
                if hasattr(swclass, 'batchShutdown'):
                    success = swclass.batchShutdown(switches)
                    stopped.update({s: s for s in success})
        else:
            for swclass, switches in groupby(
                    sorted(nodesL2, key=lambda x: str(type(x))), type):
                switches = tuple(switches)
                if hasattr(swclass, 'batchShutdown'):
                    success = swclass.batchShutdown(switches)
                    stopped.update({s: s for s in success})
        for switch in nodesL2:
            info(switch.name + ' ')
            if switch not in stopped:
                switch.stop()
            switch.terminate()
        info('\n')
        info('*** Stopping nodes\n')
        nodes = self.hosts + self.stations + self.sixLP
        for node in nodes:
            info(node.name + ' ')
            node.terminate()
        info('\n')
        if self.aps is not []:
            self.kill_hostapd()
        self.closeMininetWiFi()
        if self.sixLP:
            sixLoWPAN_module.stop()
        if self.link == wmediumd:
            self.kill_wmediumd()
        info('\n*** Done\n')

    def run(self, test, *args, **kwargs):
        "Perform a complete start/test/stop cycle."
        self.start()
        info('*** Running test\n')
        result = test(*args, **kwargs)
        self.stop()
        return result

    def monitor(self, hosts=None, timeoutms=-1):
        """Monitor a set of hosts (or all hosts by default),
           and return their output, a line at a time.
           hosts: (optional) set of hosts to monitor
           timeoutms: (optional) timeout value in ms
           returns: iterator which returns host, line"""
        if hosts is None:
            hosts = self.hosts
        poller = select.poll()
        h1 = hosts[0]  # so we can call class method fdToNode
        for host in hosts:
            poller.register(host.stdout)
        while True:
            ready = poller.poll(timeoutms)
            for fd, event in ready:
                host = h1.fdToNode(fd)
                if event & select.POLLIN:
                    line = host.readline()
                    if line is not None:
                        yield host, line
            # Return if non-blocking
            if not ready and timeoutms >= 0:
                yield None, None

    @staticmethod
    def _parsePing(pingOutput):
        "Parse ping output and return packets sent, received."
        # Check for downed link
        if 'connect: Network is unreachable' in pingOutput:
            return 1, 0
        r = r'(\d+) packets transmitted, (\d+)( packets)? received'
        m = re.search(r, pingOutput)
        if m is None:
            error('*** Error: could not parse ping output: %s\n' %
                  pingOutput)
            return 1, 0
        sent, received = int(m.group(1)), int(m.group(2))
        return sent, received

    def ping(self, hosts=None, timeout=None):
        """Ping between all specified hosts.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: ploss packet loss percentage"""
        # should we check if running?
        packets = 0
        lost = 0
        ploss = None
        if not hosts:
            hosts = self.hosts + self.stations
            output('*** Ping: testing ping reachability\n')
        for node in hosts:
            output('%s -> ' % node.name)
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    if dest.intfs:
                        result = node.cmdPrint('ping -c1 %s %s'
                                               % (opts, dest.IP()))
                        sent, received = self._parsePing(result)
                    else:
                        sent, received = 0, 0
                    packets += sent
                    if received > sent:
                        error('*** Error: received too many packets')
                        error('%s' % result)
                        node.cmdPrint('route')
                        exit(1)
                    lost += sent - received
                    output(('%s ' % dest.name) if received else 'X ')
            output('\n')
        if packets > 0:
            ploss = 100.0 * lost / packets
            received = packets - lost
            output("*** Results: %i%% dropped (%d/%d received)\n" %
                   (ploss, received, packets))
        else:
            ploss = 0
            output("*** Warning: No packets sent\n")
        if self.sixLP:
            nodes = self.sixLP
            Mininet_6LoWPAN.ping6(nodes, timeout)
        return ploss

    @staticmethod
    def _parseFull(pingOutput):
        "Parse ping output and return all data."
        errorTuple = (1, 0, 0, 0, 0, 0)
        # Check for downed link
        r = r'[uU]nreachable'
        m = re.search(r, pingOutput)
        if m is not None:
            return errorTuple
        r = r'(\d+) packets transmitted, (\d+)( packets)? received'
        m = re.search(r, pingOutput)
        if m is None:
            error('*** Error: could not parse ping output: %s\n' %
                  pingOutput)
            return errorTuple
        sent, received = int(m.group(1)), int(m.group(2))
        r = r'rtt min/avg/max/mdev = '
        r += r'(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms'
        m = re.search(r, pingOutput)
        if m is None:
            if received is 0:
                return errorTuple
            error('*** Error: could not parse ping output: %s\n' %
                  pingOutput)
            return errorTuple
        rttmin = float(m.group(1))
        rttavg = float(m.group(2))
        rttmax = float(m.group(3))
        rttdev = float(m.group(4))
        return sent, received, rttmin, rttavg, rttmax, rttdev

    def pingFull(self, hosts=None, timeout=None):
        """Ping between all specified hosts and return all data.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: all ping data; see function body."""
        # should we check if running?
        # Each value is a tuple: (src, dsd, [all ping outputs])
        all_outputs = []
        if not hosts:
            hosts = self.hosts
            output('*** Ping: testing ping reachability\n')
        for node in hosts:
            output('%s -> ' % node.name)
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    result = node.cmd('ping -c1 %s %s' % (opts, dest.IP()))
                    outputs = self._parsePingFull(result)
                    sent, received, rttmin, rttavg, rttmax, rttdev = outputs
                    all_outputs.append((node, dest, outputs))
                    output(('%s ' % dest.name) if received else 'X ')
            output('\n')
        output("*** Results: \n")
        for outputs in all_outputs:
            src, dest, ping_outputs = outputs
            sent, received, rttmin, rttavg, rttmax, rttdev = ping_outputs
            output(" %s->%s: %s/%s, " % (src, dest, sent, received))
            output("rtt min/avg/max/mdev %0.3f/%0.3f/%0.3f/%0.3f ms\n" %
                   (rttmin, rttavg, rttmax, rttdev))
        return all_outputs

    def pingAll(self, timeout=None):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        sleep(3)
        return self.ping(timeout=timeout)

    def pingPair(self):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        sleep(3)
        nodes = self.hosts + self.stations
        hosts = [nodes[0], nodes[1]]
        return self.ping(hosts=hosts)

    def pingAllFull(self):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        sleep(3)
        return self.pingFull()

    def pingPairFull(self):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        sleep(3)
        nodes = self.hosts + self.stations
        hosts = [nodes[0], nodes[1]]
        return self.pingFull(hosts=hosts)

    @staticmethod
    def _parseIperf(iperfOutput):
        """Parse iperf output and return bandwidth.
           iperfOutput: string
           returns: result string"""
        r = r'([\d\.]+ \w+/sec)'
        m = re.findall(r, iperfOutput)
        if m:
            return m[-1]
        else:
            # was: raise Exception(...)
            error('could not parse iperf output: ' + iperfOutput)
            return ''

    def iperf(self, hosts=None, l4Type='TCP', udpBw='10M', fmt=None,
              seconds=5, port=5001):
        """Run iperf between two hosts.
           hosts: list of hosts; if None, uses first and last hosts
           l4Type: string, one of [ TCP, UDP ]
           udpBw: bandwidth target for UDP test
           fmt: iperf format argument if any
           seconds: iperf time to transmit
           port: iperf port
           returns: two-element array of [ server, client ] speeds
           note: send() is buffered, so client rate can be much higher than
           the actual transmission rate; on an unloaded system, server
           rate should be much closer to the actual receive rate"""
        sleep(3)
        nodes = self.hosts + self.stations
        hosts = hosts or [nodes[0], nodes[-1]]
        assert len(hosts) is 2
        client, server = hosts

        conn1 = 0
        conn2 = 0
        if isinstance(client, Station) or isinstance(server, Station):
            if isinstance(client, Station):
                while conn1 is 0:
                    conn1 = int(client.cmd('iw dev %s link '
                                           '| grep -ic \'Connected\''
                                           % client.params['wlan'][0]))
            if isinstance(server, Station):
                while conn2 is 0:
                    conn2 = int(server.cmd('iw dev %s link | grep -ic '
                                           '\'Connected\''
                                           % server.params['wlan'][0]))
        output('*** Iperf: testing', l4Type, 'bandwidth between',
               client, 'and', server, '\n')
        server.cmd('killall -9 iperf')
        iperfArgs = 'iperf -p %d ' % port
        bwArgs = ''
        if l4Type is 'UDP':
            iperfArgs += '-u '
            bwArgs = '-b ' + udpBw + ' '
        elif l4Type != 'TCP':
            raise Exception('Unexpected l4 type: %s' % l4Type)
        if fmt:
            iperfArgs += '-f %s ' % fmt
        server.sendCmd(iperfArgs + '-s')
        if l4Type is 'TCP':
            if not waitListening(client, server.IP(), port):
                raise Exception('Could not connect to iperf on port %d'
                                % port)
        cliout = client.cmd(iperfArgs + '-t %d -c ' % seconds +
                            server.IP() + ' ' + bwArgs)
        debug('Client output: %s\n' % cliout)
        servout = ''
        # We want the last *b/sec from the iperf server output
        # for TCP, there are two of them because of waitListening
        count = 2 if l4Type is 'TCP' else 1
        while len(re.findall('/sec', servout)) < count:
            servout += server.monitor(timeoutms=5000)
        server.sendInt()
        servout += server.waitOutput()
        debug('Server output: %s\n' % servout)
        result = [self._parseIperf(servout), self._parseIperf(cliout)]
        if l4Type is 'UDP':
            result.insert(0, udpBw)
        output('*** Results: %s\n' % result)
        return result

    def runCpuLimitTest(self, cpu, duration=5):
        """run CPU limit test with 'while true' processes.
        cpu: desired CPU fraction of each host
        duration: test duration in seconds (integer)
        returns a single list of measured CPU fractions as floats.
        """
        cores = int(quietRun('nproc'))
        pct = cpu * 100
        info('*** Testing CPU %.0f%% bandwidth limit\n' % pct)
        hosts = self.hosts
        cores = int(quietRun('nproc'))
        # number of processes to run a while loop on per host
        num_procs = int(ceil(cores * cpu))
        pids = {}
        for h in hosts:
            pids[h] = []
            for _core in range(num_procs):
                h.cmd('while true; do a=1; done &')
                pids[h].append(h.cmd('echo $!').strip())
        outputs = {}
        time = {}
        # get the initial cpu time for each host
        for host in hosts:
            outputs[host] = []
            with open('/sys/fs/cgroup/cpuacct/%s/cpuacct.usage'
                      % host, 'r') as f:
                time[host] = float(f.read())
        for _ in range(duration):
            sleep(1)
            for host in hosts:
                with open('/sys/fs/cgroup/cpuacct/%s/cpuacct.usage'
                          % host, 'r') as f:
                    readTime = float(f.read())
                outputs[host].append(((readTime - time[host])
                                      / 1000000000) / cores * 100)
                time[host] = readTime
        for h, pids in pids.items():
            for pid in pids:
                h.cmd('kill -9 %s' % pid)
        cpu_fractions = []
        for _host, outputs in outputs.items():
            for pct in outputs:
                cpu_fractions.append(pct)
        output('*** Results: %s\n' % cpu_fractions)
        return cpu_fractions

    def get_distance(self, src, dst):
        """Gets the distance between two nodes

        :params src: source node
        :params dst: destination node
        :params nodes: list of nodes"""
        nodes = self.stations + self.cars + self.aps
        try:
            for host1 in nodes:
                if src == str(host1):
                    src = host1
                    for host2 in nodes:
                        if dst == str(host2):
                            dst = host2
                            dist = src.get_distance_to(dst)
                            info("The distance between %s and %s is %.2f "
                                 "meters\n" % (src, dst, float(dist)))
        except:
            info("node %s or/and node %s does not exist or there is no " \
                 "position defined" % (dst, src))

    def mobility(self, *args, **kwargs):
        "Configure mobility parameters"
        self.configureMobility(*args, **kwargs)

    def startMobility(self, **kwargs):
        "Starts Mobility"
        self.isMobility = True
        if 'repetitions' in kwargs:
            self.repetitions = kwargs['repetitions']
        if 'seed' in kwargs:
            self.seed = kwargs['seed']
        if 'associationControl' in kwargs:
            self.AC = kwargs['associationControl']
        if 'model' in kwargs:
            self.isMobilityModel = True
            kwargs['mobileNodes'] = self.getMobileNodes()
        self.mobilityKwargs = kwargs
        kwargs['stations'] = self.stations
        kwargs['aps'] = self.aps
        self.setMobilityParams(**kwargs)

    def stop_mobility(self, **kwargs):
        'Set Mobility Args'
        self.mobilityKwargs.update(kwargs)
        params = self.setMobilityParams(**kwargs)
        mobility.stop(**params)

    def getMobileNodes(self):
        mobileNodes = []
        nodes = self.stations + self.aps + self.cars
        for node in nodes:
            if 'position' not in node.params:
                mobileNodes.append(node)
        return mobileNodes

    @staticmethod
    def setBgscan(module='simple', s_inverval=30, signal=-45,
                  l_interval=300,
                  database='/etc/wpa_supplicant/network1.bgscan'):
        """Set Background scanning
        :params module: module
        :params s_inverval: short bgscan interval in second
        :params signal: signal strength threshold
        :params l_interval: long interval
        :params database: database file name"""
        if module is 'simple':
            bgscan = 'bgscan=\"%s:%d:%d:%d\"' % \
                     (module, s_inverval, signal, l_interval)
        else:
            bgscan = 'bgscan=\"%s:%d:%d:%d:%s\"' % \
                     (module, s_inverval, signal, l_interval, database)

        Association.bgscan = bgscan

    def defaultGraph(self):
        "Default values for graph"
        self.plotGraph(min_x=0, min_y=0, min_z=0,
                       max_x=100, max_y=100, max_z=0)

    def propagationModel(self, **kwargs):
        "Propagation Model Attr"
        self.ppm_is_set = True
        kwargs['noise_threshold'] = self.noise_threshold
        kwargs['cca_threshold'] = self.cca_threshold
        self.propagation_model(**kwargs)

    def configWirelessLinkStatus(self, src, dst, status):

        sta = self.nameToNode[dst]
        ap = self.nameToNode[src]

        if isinstance(self.nameToNode[src], Station):
            sta = self.nameToNode[src]
            ap = self.nameToNode[dst]

        if status == 'down':
            for wlan in range(0, len(sta.params['wlan'])):
                if sta.params['associatedTo'][wlan] != '':
                    sta.cmd('iw dev %s disconnect' % sta.params['wlan'][wlan])
                    sta.params['associatedTo'][wlan] = ''
                    ap.params['associatedStations'].remove(sta)
        else:
            for wlan in range(0, len(sta.params['wlan'])):
                if sta.params['associatedTo'][wlan] == '':
                    sta.pexec('iw dev %s connect %s %s'
                              % (sta.params['wlan'][wlan],
                                 ap.params['ssid'][0], ap.params['mac'][0]))
                    sta.params['associatedTo'][wlan] = ap
                    ap.params['associatedStations'].append(sta)

    # BL: I think this can be rewritten now that we have
    # a real link class.
    def configLinkStatus(self, src, dst, status):
        """Change status of src <-> dst links.
           src: node name
           dst: node name
           status: string {up, down}"""
        if src not in self.nameToNode:
            error('src not in network: %s\n' % src)
        elif dst not in self.nameToNode:
            error('dst not in network: %s\n' % dst)
        if isinstance(self.nameToNode[src], Station) \
                and isinstance(self.nameToNode[dst], AP) or \
                        isinstance(self.nameToNode[src], AP) \
                        and isinstance(self.nameToNode[dst], Station):
            self.configWirelessLinkStatus(src, dst, status)
        else:
            src = self.nameToNode[src]
            dst = self.nameToNode[dst]
            connections = src.connectionsTo(dst)
            if len(connections) is 0:
                error('src and dst not connected: %s %s\n' % (src, dst))
            for srcIntf, dstIntf in connections:
                result = srcIntf.ipLink(status)
                if result:
                    error('link src status change failed: %s\n' % result)
                result = dstIntf.ipLink(status)
                if result:
                    error('link dst status change failed: %s\n' % result)

    def interact(self):
        "Start network and run our simple CLI."
        self.start()
        result = CLI(self)
        self.stop()
        return result

    inited = False

    @classmethod
    def init(cls):
        "Initialize Mininet"
        if cls.inited:
            return
        ensureRoot()
        fixLimits()
        cls.inited = True

    def addParameters(self, node, autoSetMacs, params, mode='managed'):
        """adds parameters to wireless nodes
        node: node
        autoSetMacs: set MAC addrs automatically like IP addresses
        params: parameters
        defaults: Default IP and MAC addresses
        mode: if interface is running in managed or master mode"""
        node.params['frequency'] = []
        node.params['channel'] = []
        node.params['mode'] = []
        node.params['wlan'] = []
        node.params['mac'] = []
        node.phyID = []
        node.autoTxPower = False

        if 'passwd' in params:
            node.params['passwd'] = []
            passwd_list = params['passwd'].split(',')
            for passwd in passwd_list:
                node.params['passwd'].append(passwd)

        if 'scan_freq' in params:
            node.params['scan_freq'] = []
            scan_freq_list = params['scan_freq'].split(',')
            for scan_freq in scan_freq_list:
                node.params['scan_freq'].append(scan_freq)

        if 'freq_list' in params:
            node.params['freq_list'] = []
            freq_list_list = params['freq_list'].split(',')
            for freq_list in freq_list_list:
                node.params['freq_list'].append(freq_list)

        if 'encrypt' in params:
            node.params['encrypt'] = []
            encrypt_list = params['encrypt'].split(',')
            for encrypt in encrypt_list:
                node.params['encrypt'].append(encrypt)

        if mode == 'managed':
            node.params['apsInRange'] = []
            node.params['associatedTo'] = []
            if self.wmediumd_mode != interference:
                node.params['rssi'] = []
            node.ifaceToAssociate = 0
            node.max_x = 0
            node.max_y = 0
            node.min_x = 0
            node.min_y = 0
            node.max_v = 0
            node.min_v = 0

            # max_speed
            node.max_speed = 10
            if 'max_speed' in params:
                node.max_speed = int(params['max_speed'])

            # min_speed
            node.min_speed = 1
            if 'min_speed' in params:
                node.min_speed = int(params['min_speed'])

        # speed
        if 'speed' in params:
            node.speed = int(params['speed'])

        # max_x
        if 'max_x' in params:
            node.max_x = float(params['max_x'])

        # max_y
        if 'max_y' in params:
            node.max_y = float(params['max_y'])

        # min_x
        if 'min_x' in params:
            node.min_x = float(params['min_x'])

        # min_y
        if 'min_y' in params:
            node.min_y = float(params['min_y'])

        # min_v
        if 'min_v' in params:
            node.min_v = float(params['min_v'])

        # max_v
        if 'max_v' in params:
            node.max_v = float(params['max_v'])

        # constantVelocity
        node.constantVelocity = 1
        if 'constantVelocity' in params:
            node.constantVelocity = int(params['constantVelocity'])

        # constantDistance
        node.constantDistance = 1
        if 'constantDistance' in params:
            node.constantDistance = int(params['constantDistance'])

        # position
        if 'position' in params:
            position = params['position']
            position = position.split(',')
            node.params['position'] = [float(position[0]),
                                       float(position[1]),
                                       float(position[2])]
        else:
            if 'position' in node.params:
                position = node.params['position']
                position = position.split(',')
                node.params['position'] = [float(position[0]),
                                           float(position[1]),
                                           float(position[2])]

        wlans = self.countWiFiIfaces(params)

        for wlan in range(wlans):
            self.addParamsToNode(node)
            if mode == 'managed':
                self.appendAssociatedTo(node)

            if mode == 'master':
                node.params['wlan'].append(node.name + '-wlan' +
                                               str(wlan + 1))
            else:
                node.params['wlan'].append(node.name + '-wlan' + str(wlan))
                self.appendRSSI(node)
            node.params.pop("wlans", None)

        if mode == 'managed':
            self.addMacParamToNode(node, wlans, autoSetMacs, params)
            self.addIpParamToNode(node, wlans, autoSetMacs, params)

        self.addAntennaGainParamToNode(node, wlans, params)
        self.addAntennaHeightParamToNode(node, wlans, params)
        self.addTxPowerParamToNode(node, wlans, params)
        self.addChannelParamToNode(node, wlans, params)
        self.addModeParamToNode(node, wlans, params)
        self.addRangeParamToNode(node, wlans, params)

        # Equipment Model
        equipmentModel = ("%s" % params.pop('equipmentModel', {}))
        if equipmentModel != "{}":
            node.equipmentModel = equipmentModel

        if mode == 'master' or 'ssid' in node.params:
            node.params['associatedStations'] = []
            node.params['stationsInRange'] = {}
            node._4addr = False

            if 'config' in node.params:
                config = node.params['config']
                if config != []:
                    config = node.params['config'].split(',')
                    for conf in config:
                        if 'wpa=' in conf or 'wep=' in conf:
                            node.params['encrypt'] = []
                        if 'wpa=' in conf:
                            node.params['encrypt'].append('wpa')
                        if 'wep=' in conf:
                            node.params['encrypt'].append('wep')

            if mode == 'master':
                node.params['mac'] = []
                node.params['mac'].append('')
                if 'mac' in params:
                    node.params['mac'][0] = params[ 'mac' ]

                if 'ssid' in params:
                    node.params['ssid'] = []
                    ssid_list = params['ssid'].split(',')
                    for ssid in ssid_list:
                        node.params['ssid'].append(ssid)

                if 'cliente_isolation' in params:
                    node.params['cliente_isolation'] = []
                    cliente_isolation_list = \
                        params['cliente_isolation'].split(',')
                    for cliente_isolation in cliente_isolation_list:
                        node.params['cliente_isolation'].append(
                            cliente_isolation)

    @staticmethod
    def addParamsToNode(node):
        "Add Frequency, func and phyID"
        node.params['frequency'].append(2.412)
        node.func.append('none')
        node.phyID.append(0)

    @staticmethod
    def appendAssociatedTo(node):
        "Add associatedTo param"
        node.params['associatedTo'].append('')

    def appendRSSI(self, node):
        "Add RSSI param"
        if self.wmediumd_mode != interference:
            node.params['rssi'].append(-60)

    @staticmethod
    def addRangeParamToNode(node, wlans=0, params=None):
        "Add Signal Range Param"
        node.params['range'] = []
        if 'range' in params:
            range_list = str(params['range']).split(',')
            for value in range_list:
                node.params['range'].append(float(value))
                node.setRange(float(value), intf=node.params['wlan'][0])
            if len(range_list) != wlans:
                error('*** Error (%s): signal range length'
                      ' differs from the number of interfaces!' % node.name)
                exit(1)
        else:
            for _ in range(0, wlans):
                if 'equipmentModel' in node.params:
                    range_ = GetRange(node)
                    node.params['range'].append(range_.value)
                else:
                    node.params['range'].append(0)

    @staticmethod
    def addIpParamToNode(node, wlans=0, autoSetMacs=False,
                         params=None, isVirtualIface=False):
        "Add IP Param"
        if isVirtualIface:
            node.params['ip'].append(node.params['ip'][0])
        else:
            node.params['ip'] = []
            if 'ip' in params:
                ip_list = params['ip'].split(',')
                for ip in ip_list:
                    node.params['ip'].append(ip)
                if len(ip_list) != len(node.params['wlan']):
                    for ip_list in range(len(ip_list),
                                         len(node.params['wlan'])):
                        node.params['ip'].append('0/0')
            elif autoSetMacs:
                for n in range(wlans):
                    node.params['ip'].append('0/0')
                    node.params['ip'][n] = params[ 'ip' ]
            else:
                for _ in range(wlans):
                    node.params['ip'].append('')

    @staticmethod
    def addMacParamToNode(node, wlans=0, autoSetMacs=False,
                          params=None, isVirtualIface=False, macID=0):
        "Add Mac Param"
        if isVirtualIface:
            new_mac = list(node.params['mac'][0])
            new_mac[7] = str(macID)
            node.params['mac'].append("".join(new_mac))
        else:
            node.params['mac'] = []
            if 'mac' in params:
                mac_list = params['mac'].split(',')
                for mac in mac_list:
                    node.params['mac'].append(mac)
                if len(mac_list) != wlans:
                    for _ in range(len(mac_list), wlans):
                        node.params['mac'].append('')
            elif autoSetMacs:
                for n in range(wlans):
                    node.params['mac'].append('')
                    node.params['mac'][n] = params[ 'mac' ]
            else:
                for _ in range(wlans):
                    node.params['mac'].append('')

    @staticmethod
    def addAntennaHeightParamToNode(node, wlans=0, params=None,
                                    isVirtualIface=False):
        "Add Antenna Height Param"
        if isVirtualIface:
            node.params['antennaHeight'].append(
                float(node.params['antennaHeight'][0]))
        else:
            node.params['antennaHeight'] = []
            if 'antennaHeight' in params:
                antennaHeight_list = params['antennaHeight'].split(',')
                for antennaHeight in antennaHeight_list:
                    node.params['antennaHeight'].append(float(antennaHeight))
            else:
                for _ in range(wlans):
                    node.params['antennaHeight'].append(1.0)

    @staticmethod
    def addAntennaGainParamToNode(node, wlans=0, params=None,
                                  isVirtualIface=False):
        "Add Antenna Gain Param"
        if isVirtualIface:
            node.params['antennaGain'].append(
                float(node.params['antennaGain'][0]))
        else:
            node.params['antennaGain'] = []
            if 'antennaGain' in params:
                antennaGain_list = params['antennaGain'].split(',')
                for antennaGain in antennaGain_list:
                    node.params['antennaGain'].append(float(antennaGain))
            else:
                for _ in range(wlans):
                    node.params['antennaGain'].append(5.0)

    @staticmethod
    def addModeParamToNode(node, wlans=0, params=None,
                           isVirtualIface=False):
        "Add Mode Param"
        if isVirtualIface:
            node.params['mode'].append(node.params['mode'][0])
        else:
            node.params['mode'] = []
            if 'mode' in params:
                mode_list = params['mode'].split(',')
                for mode in mode_list:
                    node.params['mode'].append(mode)
                if len(mode_list) != len(node.params['wlan']):
                    for mode_list in range(len(mode_list),
                                           len(node.params['wlan'])):
                        node.params['mode'].append(node.params['mode'][0])
            else:
                for _ in range(wlans):
                    node.params['mode'].append(params['mode'])

    @staticmethod
    def addChannelParamToNode(node, wlans=0, params=None,
                              isVirtualIface=False):
        "Add Channel Param"
        if isVirtualIface:
            node.params['channel'].append(node.params['channel'][0])
        else:
            node.params['channel'] = []
            if 'channel' in params:
                channel_list = params['channel'].split(',')
                for channel in channel_list:
                    node.params['channel'].append(channel)
                if len(channel_list) != len(node.params['wlan']):
                    for channel_list in range(len(channel_list),
                                              len(node.params['wlan'])):
                        node.params['channel'].append(node.params['channel'][0])
            else:
                for _ in range(wlans):
                    node.params['channel'].append(1)

    @staticmethod
    def addTxPowerParamToNode(node, wlans=0, params=None,
                              isVirtualIface=False):
        "Add Tx Power Param"
        if isVirtualIface:
            node.params['txpower'].append(node.params['txpower'][0])
        else:
            node.params['txpower'] = []
            if 'txpower' in params:
                txpower_list = params['txpower'].split(',')
                for txpower in txpower_list:
                    node.params['txpower'].append(int(txpower))
            else:
                for _ in range(wlans):
                    if 'equipmentModel' in node.params:
                        txpower_ = GetTxPower(node)
                        node.params['txpower'].append(txpower_.value)
                    else:
                        node.params['txpower'].append(14)

    def countWiFiIfaces(self, params):
        "Count the number of virtual wifi interfaces"
        if 'wlans' in params:
            self.n_radios += int(params['wlans'])
            wlans = int(params['wlans'])
        else:
            wlans = 1
            self.n_radios += 1
        return wlans

    def createVirtualIfaces(self, nodes):
        "Creates virtual wifi interfaces"
        for node in nodes:
            if 'nvif' in node.params:
                nvif = node.params['nvif']
                wlan = 0
                for vif_ in range(0, nvif):
                    vif = node.params['wlan'][wlan] + str(vif_ + 1)
                    node.params['wlan'].append(vif)
                    node.params['range'].append(node.params['range'][0])
                    self.addParamsToNode(node)
                    self.addTxPowerParamToNode(node, isVirtualIface=True)
                    self.addChannelParamToNode(node, isVirtualIface=True)
                    self.addMacParamToNode(node, isVirtualIface=True,
                                           macID=(vif_ + 1))
                    self.appendRSSI(node)
                    self.appendAssociatedTo(node)
                    self.addAntennaGainParamToNode(node, isVirtualIface=True)
                    self.addAntennaHeightParamToNode(node, isVirtualIface=True)
                    self.addModeParamToNode(node, isVirtualIface=True)
                    node.cmd('iw dev %s interface add %s type station'
                             % (node.params['wlan'][wlan], vif))
                    TCLinkWirelessStation(node, intfName1=vif)
                    self.configureMacAddr(node)

    def check_sta_ap_mode(self):
        "check if sta is working in ap mode"
        isApAdhoc = []
        for sta in self.stations:
            if sta.func[0] == 'ap':
                self.aps.append(sta)
                isApAdhoc.append(sta)

        for ap in isApAdhoc:
            self.stations.remove(ap)
            ap.setIP('%s' % ap.params['ip'][0],
                     intf='%s' % ap.params['wlan'][0])
            ap.params.pop('rssi', None)
            ap.params.pop('apsInRange', None)
            ap.params.pop('associatedTo', None)

            for _ in (1, len(ap.params['wlan'])):
                ap.params['mac'].append('')

    @staticmethod
    def kill_hostapd():
        "Kill hostapd"
        module.kill_hostapd()
        sleep(0.1)

    @staticmethod
    def kill_wmediumd():
        "Kill wmediumd"
        info("\n*** Killing wmediumd")
        WmediumdServer.disconnect()
        WmediumdStarter.stop()
        sleep(0.1)

    @staticmethod
    def kill_mac80211_hwsim():
        "Kill mac80211_hwsim"
        module.kill_mac80211_hwsim()
        sleep(0.1)

    def configureWirelessLink(self):
        """Configure Wireless Link

        :param stations: list of stations
        :param aps: list of access points
        :param cars: list of cars"""
        nodes = self.stations + self.cars
        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                link = TCLinkWirelessStation(node,
                                             intfName1=node.params['wlan'][wlan])
                self.links.append(link)
            self.configureMacAddr(node)
        self.check_sta_ap_mode()

    def plotGraph(self, min_x=0, min_y=0, min_z=0,
                  max_x=0, max_y=0, max_z=0):
        """Plots Graph

        :params max_x: maximum X
        :params max_y: maximum Y
        :params max_z: maximum Z"""
        self.DRAW = True
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        if max_z != 0:
            self.min_z = min_z
            self.max_z = max_z
            self.plot = plot3d
            mobility.continuePlot = 'plot3d.graphPause()'

    def checkDimension(self, nodes):
        try:
            plotGraph(self.min_x, self.min_y, self.min_z,
                      self.max_x, self.max_y, self.max_z,
                      nodes, self.conn)
            if not issubclass(self.plot, plot3d):
                self.plot.graphPause()
        except:
            info('Something went wrong. Running without GUI.\n')
            self.DRAW = False

    def start_mobility(self, **kwargs):
        "Starts Mobility"
        self.isMobility = True

        if 'model' in kwargs or self.isVanet:
            mobileNodes = []
            for node in kwargs['mobileNodes']:
                if 'position' not in node.params \
                        or 'position' in node.params \
                                and node.params['position'] == (-1,-1,-1):
                    node.isStationary = False
                    mobileNodes.append(node)
                    node.params['position'] = 0, 0, 0
            kwargs['mobileNodes'] = mobileNodes
            params = self.setMobilityParams(**kwargs)
            if self.nroads == 0:
                mobility.start(**params)
            else:
                vanet(**params)

    def stopMobility(self, **kwargs):
        "Stops Mobility"
        if self.allAutoAssociation:
            self.auto_association()
        self.setMobilityParams(**kwargs)

    def setMobilityParams(self, **kwargs):
        "Set Mobility Parameters"
        if 'model' in kwargs:
            self.mobilityparam.setdefault('model', kwargs['model'])
        if self.nroads != 0:
            self.mobilityparam.setdefault('nroads', self.nroads)
        if 'repetitions' in kwargs:
            self.mobilityparam.setdefault('repetitions', kwargs['repetitions'])
        if 'plotNodes' in kwargs:
            self.mobilityparam.setdefault('plotNodes', kwargs['plotNodes'])

        if 'model' in kwargs:
            stations = kwargs['stations']
            if 'min_x' in kwargs:
                if not self.DRAW:
                    self.min_x = int(kwargs['min_x'])
                for sta in stations:
                    sta.min_x = int(kwargs['min_x'])
            if 'min_y' in kwargs:
                if not self.DRAW:
                    self.min_y = int(kwargs['min_y'])
                for sta in stations:
                    sta.min_y = int(kwargs['min_y'])
            if 'max_x' in kwargs:
                if not self.DRAW:
                    self.max_x = int(kwargs['max_x'])
                for sta in stations:
                    sta.max_x = int(kwargs['max_x'])
            if 'max_y' in kwargs:
                if not self.DRAW:
                    self.max_y = int(kwargs['max_y'])
                for sta in stations:
                    sta.max_y = int(kwargs['max_y'])
            if 'min_v' in kwargs:
                self.mobilityparam.setdefault('min_v', kwargs['min_v'])
            if 'max_v' in kwargs:
                self.mobilityparam.setdefault('max_v', kwargs['max_v'])

        if 'time' in kwargs:
            if 'init_time' not in self.mobilityparam:
                self.mobilityparam.setdefault('init_time', kwargs['time'])
            else:
                self.mobilityparam.setdefault('final_time', kwargs['time'])
        self.mobilityparam.setdefault('seed', self.seed)
        if 'stations' in kwargs:
            self.mobilityparam.setdefault('stations', kwargs['stations'])
        if 'aps' in kwargs:
            self.mobilityparam.setdefault('aps', kwargs['aps'])

        self.mobilityparam.setdefault('DRAW', self.DRAW)
        self.mobilityparam.setdefault('conn', self.conn)
        self.mobilityparam.setdefault('min_x', self.min_x)
        self.mobilityparam.setdefault('min_y', self.min_y)
        self.mobilityparam.setdefault('min_z', self.min_z)
        self.mobilityparam.setdefault('max_x', self.max_x)
        self.mobilityparam.setdefault('max_y', self.max_y)
        self.mobilityparam.setdefault('max_z', self.max_z)
        self.mobilityparam.setdefault('AC', self.AC)
        self.mobilityparam.setdefault('rec_rssi', self.rec_rssi)
        self.mobilityparam.setdefault('ppm', self.getPropagationModel())
        if 'mobileNodes' in kwargs and kwargs['mobileNodes']:
            self.mobilityparam.setdefault('mobileNodes', kwargs['mobileNodes'])
        return self.mobilityparam

    def useExternalProgram(self, program, **params):
        """Opens an external program

        :params program: any program (useful for SUMO)
        :params **params config_file: file configuration"""
        params['stations'] = self.stations
        params['aps'] = self.aps
        params['cars'] = self.cars
        params['program'] = program
        self.autoAssociation = False
        self.isVanet = True
        for car in params['cars']:
            car.params['position'] = 0, 0, 0
        if params['program'] == 'sumo' or params['program'] == 'sumo-gui':
            sumo(**params)

    @staticmethod
    def configureMacAddr(node):
        """Configure Mac Address

        :param node: node"""
        for wlan in range(0, len(node.params['wlan'])):
            iface = node.params['wlan'][wlan]
            if node.params['mac'][wlan] == '':
                node.params['mac'][wlan] = node.getMAC(iface)
            else:
                mac = node.params['mac'][wlan]
                node.setMAC(mac, iface)

    def configureCars(self):
        "Configure Cars"
        for car in self.cars:
            # useful if there no link between sta and any other device
            params = {'nextIP': self.nextIP, 'ipBaseNum':self.ipBaseNum,
                      'prefixLen':self.prefixLen, 'ssid':car.params['ssid']}
            if 'func' in car.params and car.params['func'] == 'adhoc':
                adhoc(car.params['carsta'], **params)
            else:
                mesh(car.params['carsta'], **params)
                self.stations.remove(car.params['carsta'])
                self.stations.append(car)
            if 'position' in car.params:
                if car.params['position'] == (0,0,0):
                    car.lastpos = [0, 0, 0]
                else:
                    car.params['carsta'].params['position'] = \
                        car.params['position']
                    car.lastpos = car.params['position']
            else:
                car.lastpos = [0, 0, 0]
            car.params['wlan'].append(0)
            if self.wmediumd_mode != interference:
                car.params['rssi'].append(0)
            car.params['channel'].append(0)
            car.params['mode'].append(0)
            car.params['txpower'].append(0)
            car.params['antennaGain'].append(0)
            car.params['antennaHeight'].append(0)
            car.params['associatedTo'].append('')
            car.params['frequency'].append(0)

    def configureWmediumd(self, nodes):
        "Configure Wmediumd"
        if self.autoSetPositions:
            self.wmediumd_mode = interference
        self.wmediumd_mode()
        if self.wmediumd_mode == interference:
            mobility.wmediumd_mode = 3
        else:
            mobility.wmediumd_mode = 1
        if not self.configureWiFiDirect and not self.configure4addr and \
            self.wmediumd_mode != error_prob:
            wmediumd(self.fading_coefficient, self.noise_threshold,
                     self.stations, self.aps, propagationModel)

            if self.wmediumd_mode == interference and not self.isVanet:
                for node in nodes:
                    for wlan in range(0, len(node.params['wlan'])):
                        node.setTxPower(node.params['txpower'][wlan],
                                        intf=node.params['wlan'][wlan],
                                        setParam=False)
                        node.setAntennaGain(node.params['antennaGain'][wlan],
                                            intf=node.params['wlan'][wlan],
                                            setParam=False)

    def configureWifiNodes(self):
        "Configure WiFi Nodes"
        if not self.ppm_is_set:
            self.propagationModel()
        params = {}
        if self.ifb:
            wirelessLink.ifb = True
            params['ifb'] = self.ifb
        nodes = self.stations + self.aps + self.cars
        module.start(nodes, self.n_radios, self.alt_module, **params)
        if Mininet_6LoWPAN.n_wpans != 0:
            sixLoWPAN_module.start(self.sixLP, Mininet_6LoWPAN.n_wpans)
        self.configureWirelessLink()
        self.createVirtualIfaces(self.stations)
        AccessPoint(self.aps, self.driver, self.link)
        self.configureCars()

        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                if isinstance(node, Car) and wlan >= 1:
                    node = node.params['carsta']
                    wlan = 0
                if node in self.carsSTA:
                    wlan = 0
                if int(node.params['range'][wlan]) == 0:
                    intf = node.params['wlan'][wlan]
                    node.params['range'][wlan] = node.getRange(intf=intf)
                else:
                    if node.params['txpower'][wlan] == 14 and \
                                    'equipmentModel' not in node.params:
                        node.autoTxPower=True
                        node.params['txpower'][wlan] = \
                            node.get_txpower_prop_model(wlan)
                node.setTxPower(node.params['txpower'][wlan],
                                intf=node.params['wlan'][wlan],
                                setParam=True)

        if self.link == wmediumd:
            self.configureWmediumd(nodes)

        return self.stations, self.aps

    def plotCheck(self, other_nodes):
        "Check which nodes will be plotted"
        self.check_sta_ap_mode()
        nodes = self.stations + self.aps + other_nodes
        self.checkDimension(nodes)

    def plot_dynamic(self):
        "Check which nodes will be plotted dynamically at runtime"
        nodes = self.stations + self.aps
        self.checkDimension(nodes)

        while True:
            for node in nodes:
                intf = node.params['wlan'][0]
                node.params['range'][0] = node.getRange(intf=intf)
                if self.DRAW:
                    if not issubclass(self.plot, plot3d):
                        self.plot.updateCircleRadius(node)
                    self.plot.graphUpdate(node)
            eval(mobility.continuePlot)
            sleep(0.5)

    @staticmethod
    def getPropagationModel():
        return propagationModel.model

    def auto_association(self):
        "This is useful to make the users' life easier"
        nodes = self.stations + self.aps
        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                if isinstance(node, Car) and wlan == 1:
                    node = node.params['carsta']
                    wlan = 0
        ap = []
        for node in self.aps:
            if 'link' in node.params:
                ap.append(node)

        nodes = self.stations + ap

        if self.nroads == 0:
            for node in nodes:
                if node.params['associatedTo'][0] == '':
                    if 'position' in node.params and 'link' not in node.params:
                        mobility.aps = self.aps
                        mobility.configLinks(node)

            for sta in self.stations:
                for wlan in range(0, len(sta.params['wlan'])):
                    for ap in self.aps:
                        if 'position' in sta.params and 'position' in ap.params:
                            dist = sta.get_distance_to(ap)
                            if dist <= ap.params['range'][0]:
                                mobility.handover(sta, ap, wlan, ap_wlan=0)
                                if self.rec_rssi:
                                    os.system('hwsim_mgmt -k %s %s >/dev/null 2>&1'
                                              % (sta.phyID[wlan],
                                                 abs(int(sta.params['rssi'][wlan]))))

    @staticmethod
    def propagation_model(**kwargs):
        "Propagation Model Attr"
        propagationModel.setAttr(**kwargs)

    @staticmethod
    def stop_simulation():
        "Pause the simulation"
        mobility.pause_simulation = True

    @staticmethod
    def start_simulation():
        "Start the simulation"
        mobility.pause_simulation = False

    @staticmethod
    def printDistance(src, dst, nodes):
        """Prints the distance between two points

        :params src: source node
        :params dst: destination node
        :params nodes: list of nodes"""
        try:
            for host1 in nodes:
                if src == str(host1):
                    src = host1
                    for host2 in nodes:
                        if dst == str(host2):
                            dst = host2
                            dist = src.get_distance_to(dst)
                            info("The distance between %s and %s is %.2f "
                                 "meters\n" % (src, dst, float(dist)))
        except:
            info("node %s or/and node %s does not exist or there is no " \
                 "position defined\n" % (dst, src))

    @staticmethod
    def configureMobility(*args, **kwargs):
        "Configure mobility parameters"
        args[0].isStationary = False
        mobility.configure(*args, **kwargs)

    @staticmethod
    def getDataRate(sta=None, ap=None, wlan=0):
        "Set the rate"
        value = GetRate(sta, ap, wlan)
        return value

    @staticmethod
    def setChannelEquation(**params):
        """Set Channel Equation. The user may change the equation defined in
        wifiChannel.py by any other.

        :params bw: bandwidth (mbps)
        :params delay: delay (ms)
        :params latency: latency (ms)
        :params loss: loss (%)"""
        if 'bw' in params:
            wirelessLink.equationBw = params['bw']
        if 'delay' in params:
            wirelessLink.equationDelay = params['delay']
        if 'latency' in params:
            wirelessLink.equationLatency = params['latency']
        if 'loss' in params:
            wirelessLink.equationLoss = params['loss']

    @staticmethod
    def stopGraphParams():
        "Stop the graph"
        mobility.continuePlot = 'exit()'
        mobility.continue_params = 'exit()'
        sleep(0.5)

    def closeMininetWiFi(self):
        "Close Mininet-WiFi"
        self.plot.closePlot()
        module.stop()  # Stopping WiFi Module


class MininetWithControlNet(Mininet_wifi):
    """Control network support:
       Create an explicit control network. Currently this is only
       used/usable with the user datapath.
       Notes:
       1. If the controller and switches are in the same (e.g. root)
          namespace, they can just use the loopback connection.
       2. If we can get unix domain sockets to work, we can use them
          instead of an explicit control network.
       3. Instead of routing, we could bridge or use 'in-band' control.
       4. Even if we dispense with this in general, it could still be
          useful for people who wish to simulate a separate control
          network (since real networks may need one!)
       5. Basically nobody ever used this code, so it has been moved
          into its own class.
       6. Ultimately we may wish to extend this to allow us to create a
          control network which every node's control interface is
          attached to."""

    def configureControlNetwork(self):
        "Configure control network."
        self.configureRoutedControlNetwork()

    # We still need to figure out the right way to pass
    # in the control network location.

    def configureRoutedControlNetwork(self, ip='192.168.123.1',
                                      prefixLen=16):
        """Configure a routed control network on controller and switches.
           For use with the user datapath only right now."""
        controller = self.controllers[0]
        info(controller.name + ' <->')
        cip = ip
        snum = ipParse(ip)
        nodesL2 = self.switches + self.aps
        for switch in nodesL2:
            info(' ' + switch.name)
            # set Link as default since wmediumd doesn't include port1
            self.link = Link
            link = self.link(switch, controller, port1=0)
            sintf, cintf = link.intf1, link.intf2
            switch.controlIntf = sintf
            snum += 1
            while snum & 0xff in [0, 255]:
                snum += 1
            sip = ipStr(snum)
            cintf.setIP(cip, prefixLen)
            sintf.setIP(sip, prefixLen)
            controller.setHostRoute(sip, cintf)
            switch.setHostRoute(cip, sintf)
        info('\n')
        info('*** Testing control network\n')
        while not cintf.isUp():
            info('*** Waiting for', cintf, 'to come up\n')
            sleep(1)
        for switch in nodesL2:
            while not sintf.isUp():
                info('*** Waiting for', sintf, 'to come up\n')
                sleep(1)
            if self.ping(hosts=[switch, controller]) != 0:
                error('*** Error: control network test failed\n')
                exit(1)
        info('\n')
