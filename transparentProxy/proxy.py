import socket
import pyroute2
import iptc
import sys
import threading


class ProxyInstance():

    def __init__(self, spice_ip, spice_port):
        self.spice_ip = spice_ip
        self.spice_port = spice_port

    def run(self):

        # Reserve a port for this proxy instance by binding a socket
        self.external_socket = socket.socket()
        #TODO Set address explicitely
        self.external_socket.bind(('', 0))
        _, self.external_port = map(str, self.external_socket.getsockname())

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

        self.setup_dnat()
        self.setup_snat()

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
        self.snat_rule.destination = self.spice_ip
        self.snat_rule.create_target('SNAT').to_source = self.internal_ip
        iptc.Chain(iptc.Table(iptc.Table.NAT),
                   'POSTROUTING').insert_rule(self.snat_rule)


if __name__ == '__main__':
    proxy_instance = ProxyInstance(sys.argv[1], sys.argv[2])
#    proxy_thread = threading.Thread(None, proxy_instance.run)
#    proxy_thread.start()
    proxy_instance.run()

