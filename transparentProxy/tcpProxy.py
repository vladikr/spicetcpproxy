import multiprocessing
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
        #proxy = Forwarding().get_instance()
        #proxy.discover()

    def reserve(self, port, socket):
        self.__cached_ports[port] = socket

    def remove_port(self, port):
        del self.__cached_ports[port]

    def get_all_items(self):
        return self.__cached_ports.iteritems()


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
            reserved_port = listen_sock.getsockname()[1]
            proxy = Forwarding().get_instance()
            proxy.setup_forwarding(dest_host, dest_port,
                                   listen_ip, reserved_port)
            reserved_port = ReservedPorts.get_instance()
            reserved_port.reserve(reserved_port, listen_sock)

            #TODO: respond with the reserved port
            self.wfile.write(self.protocol_version +
                             ' 200 Connection established - port: %s\n'
                             % reserved_port)
        except Exception as exp:
            self.send_response(500)
            self.end_headers()
            LOG.error('failed %s' % exp, exc_info=True)


class ProcessingTCPSocketServer(SocketServer.ThreadingMixIn,
                                SocketServer.TCPServer):
    allow_reuse_address = True


class PeriodicCleanup(threading.Thread):

    PERIODIC_INTERVAL = 10

    def __init__(self):
        threading.Thread.__init__(self)
        self._log = log
        self.stopRunning = threading.Event()

    def is_port_active(port):
        pass

    def run(self):
        try:
            time.sleep(PERIODIC_INTERVAL)
            while not self.stopRunning.isSet():
                try:
                    reserved_ports = ReservedPorts.get_instance()
                    for port in reserved_port.get_all_items():
                        pass
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
    #PeriodicCleanup().start()
    server.serve_forever()
