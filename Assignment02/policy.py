# !/usr/bin/python


# Information
__author__ = "Deirdre Connolly"
__studentNumber__ = "R00112962"
__project__ = "Assignment02"

# Instructions
'''
A Pox script to implement the policies listed above.
Your code must be meaningfully commented.

Write an application for the controller to proactively add rules that don’t time out for the following functions:
•	H1 and H2 should be able to exchange any kind of traffic with each other (reachability functionality).
•	H3 and H4 should never be able to communicate with each other (traffic isolation, similar to VLAN functionality).
•	H1 should be able to telnet and SSH to H5, but no other traffic should be allowed through (stateless firewall functionality).
Rules should be reactively configured to achieve the following functions, and the rules should have an idle timeout of 30 seconds:
•	H1 should be able to telnet and SSH to H6, and H6 should be able to send any kind of traffic to H1 (stateful firewall functionality).
•	For HTTP traffic going from H1 to H7/H8, every second flow should go to H7, and every other flow to H8 (load balancer functionality).
You will need to think about ARP. You can set static ARP entries on all hosts, or you can handle ARP requests in your own code, or use an existing controller application to deal with ARP.
ARP consideration (static in Mininet script, dynamic in Pox script, existing Pox application).
'''

# Imports
from pox.core import core                       # Main POX object
import pox.openflow.libopenflow_01 as of        # OpenFlow 1.0 library
import pox.lib.util as poxutil                  # Various util functions
from pox.lib.revent import *                    # Event library
import pox.lib.packet as pkt                    # Packet parsing/construction
from pox.lib.addresses import EthAddr, IPAddr   # Address types
import weakref


########################################################################################################################


# Proactive policy (in ConnectionUp: new rule, match criteria, action + timeout, sent to switches)
#   - Reachability rule
#   - Traffic isolation rule
#   - Stateless firewall rule
"""
Simple POX script to proactively configure a rule blocking ftp packets on
any switch that connects.

"""

# Create a logger for this component
log = core.getLogger()


class SwitchHandler(object):
    """
    Waits for OpenFlow switches to connect and pushes a rule to each
    """

    def __init__(self):
        """
        Initialize
        """
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        """
        Switch connected
        """

        msg = of.ofp_flow_mod()
        msg.match.dl_type = pkt.ethernet.IP_TYPE
        msg.match.nw_proto = pkt.ipv4.TCP_PROTOCOL
        msg.match.tp_dst = 21
        # msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
        msg.out_port = of.OFPP_NONE
        event.connection.send(msg)
        print("Rule configured to block FTP on switch with dpid: %s" %
              (hex(event.dpid)))


def launch():
    core.registerNew(SwitchHandler)


########################################################################################################################


# Reactive policy (in PacketIn: new rule, match criteria, action + timeout, sent to switch)
#   - Stateful firewall rule
#   - Load balancer rule

"""
A POX component to show examples of adding flow rules to switches to
reactively enable communication between hosts as they attempt to
send ip datagrams.

Assumes Mininet topology created with 'sudo mn --topo=linear,3 --controller=remote'. That will
give us:
  H1 connects to S1 port 1
  H2 connects to S2 port 1
  H3 connects to S3 port 1
  S1 port 2 connects to S2 port 2
  S2 port 3 connects to S3 port 2

"""

# Create a logger for this component
log = core.getLogger()


class SwitchHandler(object):
    """
    Waits for OpenFlow switches to connect and keeps a note of the
    connection for each of them.
    """
    switches = []
    # Each path is a list of source IP, destination IP, and a list of
    # tuples specifying how to get from source to destination. Each tuple
    # is a switch DPID and an output port number.
    paths = [["10.0.0.1", "10.0.0.2", [(hex(1), 2), (hex(2), 1)]],
             ["10.0.0.1", "10.0.0.3", [(hex(1), 2), (hex(2), 3), (hex(3), 1)]],
             ["10.0.0.2", "10.0.0.1", [(hex(2), 2), (hex(1), 1)]],
             ["10.0.0.2", "10.0.0.3", [(hex(2), 3), (hex(3), 1)]],
             ["10.0.0.3", "10.0.0.1", [(hex(3), 2), (hex(2), 2), (hex(1), 1)]],
             ["10.0.0.3", "10.0.0.2", [(hex(3), 2), (hex(2), 1)]]]

    def __init__(self):
        """
        Initialize
        """
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        """
        Switch connected - keep track of it by adding to the switches list
        """
        log.debug("Connection %s" % (event.connection,))
        self.switches.append([hex(event.dpid), weakref.ref(event.connection)])

        # Add a rule to flood ARP packets - okay with this linear
        # Topology because there are no loops
        msg = of.ofp_flow_mod()
        msg.priority = 1
        msg.match.dl_type = pkt.ethernet.ARP_TYPE  # 0x806
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        event.connection.send(msg)

        # Add default rule to send packets to the controller
        msg = of.ofp_flow_mod()
        msg.priority = 0  # Lowest priority
        msg.hard_timeout = 0
        msg.idle_timeout = 0  # Never time out (but this is default anyway)
        msg.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
        # If no action added - default would be to drop packets
        event.connection.send(msg)

    def _handle_PacketIn(self, event):
        """
        Packet received
        """

        packet = event.parsed
        if packet.type == pkt.ethernet.IP_TYPE:
            source_ip = str(packet.next.srcip)
            destination_ip = str(packet.next.dstip)
            print("PacketIn: IP pkt - src IP %s, dst IP %s, IP proto %s" % \
                  (source_ip, destination_ip, str(packet.next.protocol)))
            path = next((path for path in self.paths if ((path[0] == source_ip) and
                                                         (path[1] == destination_ip))), None)
            if path != None:
                # Send rules to the switches along the path from source to destination
                for (dpid, port) in path[2]:
                    msg = of.ofp_flow_mod()
                    msg.priority = 10
                    msg.idle_timeout = 30  # Time out after 30 seconds of not matching
                    msg.match.dl_type = pkt.ethernet.IP_TYPE  # 0x800
                    msg.match.nw_src = IPAddr(source_ip)
                    msg.match.nw_dst = IPAddr(destination_ip)
                    msg.actions.append(of.ofp_action_output(port=port))
                    switch = next((switch for switch in self.switches if (switch[0] == dpid)), None)
                    if switch != None:
                        switch[1]().send(msg)
                    else:
                        print("No switch matching %s" % dpid)
                # Now forward the packet we got from the switch back to it to send on the path that we just configured
                # Otherwise the first packet in each flow would be lost
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.actions.append(of.ofp_action_output(port=of.OFPP_TABLE))
                event.connection.send(msg)
        else:
            print("Got a packet type that we didn't expect")


def launch():
    """

    Call this component as, e.g.:
    ./pox.py simplefwd
    """

    core.registerNew(SwitchHandler)


########################################################################################################################


"""
A POX component to print some details of each packet received
via a PACKET_IN message from a switch

Execute this component as:
 ./pox.py pktinfo
"""

# Create a logger for this component
log = core.getLogger()


class PacketInHandler(object):
    """
    Watches for PACKET_IN messages from switches, prints some details
    of each received packet
    """

    def __init__(self):
        """
        Initialize
        """
        core.openflow.addListeners(self)

    def _handle_PacketIn(self, event):
        """
        Packet received
        """

        packet = event.parsed
        if packet.type == pkt.ethernet.ARP_TYPE:
            print("PacketIn: ARP pkt - src mac %s, dst mac %s" % \
                  (str(packet.src), str(packet.dst)))
        else:
            print("PacketIn: IP pkt - src mac %s, dst mac %s, IP proto %s" % \
                  (str(packet.src), str(packet.dst), str(packet.next.protocol)))

        # Being lazy here, just flooding the packet. Don't use on a looped network!
        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        error = event.connection.send(msg)


@poxutil.eval_args
def launch():
    """

  """
    # Execute this component as:
    # ./pox.py pktinfo

    core.registerNew(PacketInHandler)
