#!/usr/bin/python


# Information
__author__ = "Deirdre Connolly"
__studentNumber__ = "R00112962"
__project__ = "Assignment02"

# Instructions
'''
A script to create the Mininet topology.

Write a Mininet script in Python to create a small data centre network using a spine-leaf topology.
The script should take a parameter ‘n’, which corresponds to the number of switches at each level of the topology.
The topology should include 2 hosts connected to each leaf switch, and a remote controller.
Name the switches ‘S1’, ‘S2’, etc, and the hosts ‘H1’, ‘H2’, etc.
The switches should be Open vSwitch instances, and the remote controller must be Pox.
Example topology in assignment brief, n = 4.
ARP consideration (static in Mininet script, dynamic in Pox script, existing Pox application).
'''

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

    def __init__(self, n):
        # Initialize topology and default options
        Topo.__init__(self)

        # Create topology
        host_num = 1  # Starting at H1

        # Loop for S1 to S4 (top row in diagram)
        for i in irange(1, n):
            switchesTopRow = self.addSwitch('S%s' % i)  # Create S1 to S4

        # Loop for S5 to S8
        for i in irange(n + 1, n * 2):
            switchesBottomRow = self.addSwitch('S%s' % i)  # Create S5 to S8

            # Loop to connect each of the bottom row to S1 to S4
            # Add links as the switches are being created (as the loop is iterating)
            # Here, n = 4, i = 5, j = 1
            for j in irange(1, n):
                # Have to call top row by given name, because variable switchesTopRow is outside the scope of its loop
                self.addLink(switchesBottomRow, 'S%s' % j)

            # Create pair of hosts per bottom switch, add links
            for k in irange(1, n / 2):  # Start at 1, end at 2 (H1 to H2, H3 to H4, etc.)
                host = self.addHost('H%s' % host_num)
                host_num += 1
                self.addLink(switchesBottomRow, host)


# Main
if __name__ == '__main__':
    setLogLevel('info')

    n = 4  # Switches S1 to S4 in top row

    # Create topology
    topo = CustomTopo(n)

    # Add POX controller
    controllerIP = '0.0.0.0:6633'

    # Create POX remote controller object with name and IP
    POX = RemoteController('POX', controllerIP)

    # Create network by calling Mininet with topology
    network = Mininet(topo=topo, controller=None, link=Link)

    # Add controller object to network
    network.addController(POX)

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
