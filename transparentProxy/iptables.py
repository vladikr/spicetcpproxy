import iptc
import logging


class IPTablesManager(object):

    log = logging.getLogger("IPTables")

    def __init__(self):
        self.nat_table = iptc.Table('nat')
        self.nat_table.autocommit = False
        self.filter_table = iptc.Table('filter')
        self.filter_table.autocommit = False
        self.pre_route_chain = iptc.Chain(self.nat_table, 'PREROUTING')
        self.post_route_chain = iptc.Chain(self.nat_table, 'POSTROUTING')
        self.forward_chain = iptc.Chain(self.filter_table, 'FORWARD')

    def _setup_dnat(self, protocol, dst, dport, src, sport):
        rule = iptc.Rule()
        rule.protocol = protocol
        rule.dport = str(sport)
        match = iptc.Match(rule, protocol)
        match.dport = sport
        rule.add_match(match)
        target = iptc.Target(rule, "DNAT")
        target.to_destination = "%s:%s" % (dst, dport)
        rule.target = target
        self.pre_route_chain.insert_rule(rule)
        return rule

    def _setup_snat(self, protocol, dst, src):
        rule = iptc.Rule()
        rule.protocol = protocol
        rule.src = str(dst)
        match = iptc.Match(rule, protocol)
        match.sport = dport
        rule.add_match(match)
        target = iptc.Target(rule, "SNAT")
        target.to_source = "%s" % (src)
        rule.target = target
        self.post_route_chain.insert_rule(rule)
        return rule

    def _setup_forward(self, dst, dport, src, sport, protocol):
        rule = iptc.Rule()
        rule.dst = str(dst)
        rule.dport = dport
        rule.protocol = protocol
        self.forward_chain.insert_rule(rule)

    def setup_forwarding(self, dest_ip, dest_port,
                               incoming_ip, incoming_port,
                               outgoing_ip,
                               protocol='tcp'):
        try:
            # incoming to host
            dnat_rule = self._setup_dnat(protocol, dest_ip, str(dest_port),
                                         incoming_ip, str(incoming_port))
            snat_rule = self._setup_snat(protocol, dest_ip, outgoing_ip)
            self._setup_forward(dest_ip, str(dest_port), incoming_ip,
                                str(incoming_port), protocol)
            self.nat_table.commit()
            self.filter_table.commit()
        except Exception as exp:
            self.log.error('failed - %s' % exp, exc_info=True)
            raise

    def discover(self):
        rules = self.pre_route_chain.rules
        for rule in rules:
            return rule
