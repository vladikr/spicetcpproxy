import multiprocessing
import pyroute2
import select
import SimpleHTTPServer
import socket
import SocketServer
from gluesockets import gluesockets
import logging
import sys
from forwarding import Forwarding
import threading
import psutil

frm = """%(process)s::%(name)s::%(asctime)s - %(message)s"""
logging.basicConfig(level=logging.DEBUG, format=frm)
LOG = logging.getLogger("Proxy")


class ReservedPorts(object):

    __instance = None

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.__cached_ports = {}
        proxy = Forwarding().get_instance()

    def reserve(self, port, socket):
        self.__cached_ports[port] = socket

    def remove_port(self, port):
        del self.__cached_ports[port]

    def get_all_items(self):
        return self.__cached_ports.iteritems()

    def refresh_ports():
        active_ports = [entry for entry in psutil.net_connections()
                        if entry.status != 'NONE']
        for item in self.__cached_ports.iteritems():
            socc_obj = [entry for entry in active_ports
             if entry.laddr == (str(item[1].getsockname()[0]), item[0])]
            if not socc_obj:
                self.remove_port(item[0])


class HTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    LOG = logging.getLogger("Handler")

    def do_GET(self):
        try:
            pos = self.path.rfind(':')
            dest_host = self.path[:pos]
            dest_port = int(self.path[pos + 1:])
        except Exception:
            self.send_response(400)
            self.end_headers()

        try:
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_ip = self.request.getsockname()[0]
            listen_sock.bind((listen_ip, 0))
            incoming_port_num = listen_sock.getsockname()[1]
            ip = pyroute2.IProute()
            outgoing_ip = ip.get_routes(family=socket.AF_INET,
                                        dst=dest_host)[0]['attr'][3][1]
            outgoing_sock.bind((outgoing_ip, 0))
            outgoing_port = outgoing_sock.getsockname()[1]
            proxy = Forwarding().get_instance()
            proxy.setup_forwarding(dest_host, dest_port,
                                   listen_ip, incoming_port_num,
                                   outgoing_ip)
            reserved_port = ReservedPorts.get_instance()
            reserved_port.reserve(reserved_port_num, listen_sock)

            #TODO: respond with the reserved port
            self.wfile.write(self.protocol_version +
                             ' 200 Connection established - port: %s\n'
                             % reserved_port_num)
        except Exception as exp:
            self.send_response(500)
            self.end_headers()
            LOG.error('failed %s' % exp, exc_info=True)


class ProcessingTCPSocketServer(SocketServer.ThreadingMixIn,
                                SocketServer.TCPServer):
    allow_reuse_address = True


class PeriodicCleanup(threading.Thread):

    LOG = logging.getLogger("PeriodicCleanup")

    PERIODIC_INTERVAL = 1

    def __init__(self):
        threading.Thread.__init__(self)
        self._log = LOG
        self.stopRunning = threading.Event()

    def is_port_active(port):
        pass

    def run(self):
        self.stopRunning.set()
        try:
            LOG.info('Start')
            #time.sleep(PERIODIC_INTERVAL)
            LOG.info('After Sleep')
            while not self.stopRunning.isSet():
                try:
                    reserved_ports = ReservedPorts.get_instance()
                    LOG.info(reserved_ports.get_all_items())
                    #reserved_ports.refresh_ports()
                except:
                    pass
                self.stopRunning.wait(PERIODIC_INTERVAL)
        except:
            pass

    def stop(self):
        self.stopRunning.set()

if __name__ == "__main__":
    HOST, PORT = "", 54321

    Handler = HTTPRequestHandler
    server = ProcessingTCPSocketServer((HOST, PORT), Handler)
    ip, port = server.server_address
    PeriodicCleanup().start()
    server.serve_forever()
