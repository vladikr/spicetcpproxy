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
        rule.dst = str(src)
        match = iptc.Match(rule, protocol)
        match.dport = sport
        rule.add_match(match)
        target = iptc.Target(rule, "DNAT")
        target.to_destination = "%s:%s" % (dst, dport)
        rule.target = target
        self.pre_route_chain.insert_rule(rule)

    def _setup_snat(self, protocol, dst, dport, src, sport):
        rule = iptc.Rule()
        rule.protocol = protocol
        rule.src = str(dst)
        match = iptc.Match(rule, protocol)
        match.sport = dport
        rule.add_match(match)
        target = iptc.Target(rule, "SNAT")
        target.to_source = "%s:%s" % (src, sport)
        rule.target = target
        self.post_route_chain.insert_rule(rule)

    def _setup_forward(self, dst, dport, src, sport, protocol):
        rule = iptc.Rule()
        print "I got dst: %s" % dst
        rule.dst = str(dst)
        rule.dport = dport
        rule.protocol = protocol
        target = iptc.Target(rule, "ACCEPT")
        match = iptc.Match(rule, "state")
        match.state = "NEW,ESTABLISHED,RELATED"
        rule.add_match(match)
        match1 = iptc.Match(rule, protocol)
        match1.dport = dport
        rule.add_match(match1)
        rule.target = target
        self.forward_chain.insert_rule(rule)

    def setup_forwarding(self, dst, dport, src, sport, protocol='tcp'):
        print 'dst: %s, dport: %s, src: %s, sport: %s' % (dst, dport,
                                                          src, sport)
        try:
            self._setup_dnat(protocol, dst, str(dport), src, str(sport))
            self._setup_forward(dst, str(dport), src, str(sport), protocol)
            self._setup_snat(protocol, dst, str(dport), src, str(sport))
            self.nat_table.commit()
            self.filter_table.commit()
        except Exception as exp:
            self.log.error('failed - %s' % exp, exc_info=True)
            raise
#
#        rules = chain.rules
#        for rule in rules:
#            chain.delete_rule(rule)
#        table.commit()
#        table.close()
