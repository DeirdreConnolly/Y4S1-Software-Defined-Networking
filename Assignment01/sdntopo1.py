# !/usr/bin/python


# Information
__author__ = "Deirdre Connolly"
__studentNumber__ = "R00112962"
__project__ = "Assignment01"

# Imports
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, RemoteController
from mininet.link import TCLink, Link
from mininet.util import irange, dumpNodeConnections
from mininet.log import setLogLevel
from mininet.topo import Topo
from mininet.util import irange


# Function to create topology
class CustomTopo(Topo):
    "Simple Data Center Topology"

    "linkopts - (1:core, 2:aggregation, 3: edge) parameters"
    "fanout - number of child switch per parent switch"

    def __init__(self, fanout):
        # Initialize topology and default options
        Topo.__init__(self)

        # JS logic ...
        #
        # We need one core switch, then 'fanout' Aggregation switches,
        #   'fanout' Edge switches per Aggregation switch, and 'fanout'
        #   hosts per Edge switch... and of course links between child
        #   devices at each layer and their respective parent.
        #
        # Device numbering as follows:
        #   S1 to S{2} 		    - Aggregation switches
        #   S{2 + 1} upwards 	- Edge switches
        #   H1 upwards 			- Hosts

        # Create topology
        host_num = 1  # Starting at H1
        for i in irange(1, fanout):
            aggr_switch = self.addSwitch('S%s' % i)
            if i == 2:  # After S1 and S2 have been created
                self.addLink('S%s' % (i - 1), 'S%s' % i)  # Link S1 and S2
            for j in irange(1, fanout + 1):
                edge_switch_num = i * (fanout + 1) + j  # (fanout + 1) otherwise it creates S5 twice
                edge_switch = self.addSwitch(
                    'S%s' % (edge_switch_num - 1))  # (edge_switch_num - 1) other range is S4-S9
                self.addLink(aggr_switch, edge_switch)
                for k in irange(1, fanout):
                    host = self.addHost('H%s' % host_num)
                    host_num += 1
                    self.addLink(edge_switch, host)


# Main
if __name__ == '__main__':
    setLogLevel('info')

    fanout = 2  # Aggregation switches S1-S2

    # Create topology
    topo = CustomTopo(fanout)

    # Add ONOS controller
    controllerIP = '192.168.10.186'

    # Create ONOS remote controller object with name and IP
    ONOS = RemoteController('ONOS', controllerIP)

    # Create network by calling Mininet with topology
    network = Mininet(topo=topo, controller=None, link=Link)

    # Add controller object to network
    network.addController(ONOS)

    # Start network
    network.start()

    print
    "Dumping host connections"
    dumpNodeConnections(network.hosts)
    print
    "Testing network connectivity"
    network.pingAll()
    print

    # Create CLI
    cli = CLI(network)

    network.stop()
