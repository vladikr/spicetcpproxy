import socket
import pyroute2
import iptc
import sys
import time


class ProxyInstance():

    def __init__(self, spice_ip, spice_port):
        self.spice_ip = spice_ip
        self.spice_port = spice_port
        self.packet_count = -1

    def run(self):

        # Reserve a port for this proxy instance by binding a socket
        self.external_socket = socket.socket()
        #TODO Set address explicitely
        self.external_socket.bind(('', 0))
        self.external_ip, self.external_port = map(str, self.external_socket.getsockname())

        # Find the source internal IP that packets to spice_ip will use
        iproute = pyroute2.IPRoute()
        spice_route = iproute.get_routes(socket.AF_INET, dst=self.spice_ip)
        try:
            prefsrc, internal_ip = spice_route[0]['attrs'][3]
            if prefsrc == 'RTA_PREFSRC':
                self.internal_ip = internal_ip
            else:
                raise Exception('Unable to determine internal IP')
        except (IndexError, KeyError, ValueError):
            raise Exception('Unable to determine internal IP')

        # Setup the rules
        self.setup_dnat()
        self.setup_snat()
        self.setup_forward()

        print('Proxy ready on %s:%s' % (self.external_ip, self.external_port))
        sys.stdout.flush()

        # Monitor packet counter and remove rules when inactive
        while self.get_packet_count() > self.packet_count:
            self.packet_count = self.get_packet_count()
            time.sleep(10)
        self.cleanup()

    def setup_dnat(self):
        self.dnat_rule = iptc.Rule()
        self.dnat_rule.protocol = 'tcp'
        self.dnat_rule.create_match('tcp').dport = self.external_port
        self.dnat_rule.create_target('DNAT').\
                to_destination = '%s:%s' % (self.spice_ip, self.spice_port)
        iptc.Chain(iptc.Table(iptc.Table.NAT),
                   'PREROUTING').insert_rule(self.dnat_rule)

    def setup_snat(self):
        self.snat_rule = iptc.Rule()
        self.snat_rule.dst = self.spice_ip
        self.snat_rule.create_target('SNAT').to_source = self.internal_ip
        iptc.Chain(iptc.Table(iptc.Table.NAT),
                   'POSTROUTING').insert_rule(self.snat_rule)

    def setup_forward(self):
        self.forward_rule = iptc.Rule()
        self.forward_rule.protocol = 'tcp'
        self.forward_rule.dst = self.spice_ip
        self.forward_rule.create_match('tcp').dport = self.spice_port
        self.forward_rule.create_target('ACCEPT')
        rule = iptc.Chain(iptc.Table(iptc.Table.FILTER),
                   'FORWARD').insert_rule(self.forward_rule)

    def cleanup(self):
        iptc.Chain(iptc.Table(iptc.Table.NAT),
                   'PREROUTING').delete_rule(self.dnat_rule)
        iptc.Chain(iptc.Table(iptc.Table.NAT),
                   'POSTROUTING').delete_rule(self.snat_rule)
        iptc.Chain(iptc.Table(iptc.Table.FILTER),
                   'FORWARD').delete_rule(self.forward_rule)

    def get_packet_count(self):
        iptc.Table(iptc.Table.FILTER).refresh()
        for rule in iptc.Chain(iptc.Table(iptc.Table.FILTER),
                               'FORWARD').rules:
            if rule == self.forward_rule:
                packet_count, _ = rule.get_counters()
                return packet_count
        raise Exception('Unable to find FORWARD rule')
            


if __name__ == '__main__':
    proxy_instance = ProxyInstance(sys.argv[1], sys.argv[2])
    proxy_instance.run()

