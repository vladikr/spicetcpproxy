import multiprocessing
import select
import SimpleHTTPServer
import socket
import SocketServer
from gluesockets import gluesockets
import logging
import sys

frm = """%(process)s::%(name)s::%(asctime)s - %(message)s"""
logging.basicConfig(level=logging.DEBUG, format=frm)
LOG = logging.getLogger("Proxy")

class MultiProcessingMixIn:
    """Mix-in class to handle each request in a new process."""

    LOG = logging.getLogger("MPM")
    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

    def process_request_child(self, request, client_address):
        """Same as in BaseServer but as a process.

        In addition, exception handling is done here.

        """
        try:
            LOG.debug("b4 req")
            self.finish_request(request, client_address)
            LOG.debug("AFTER finish_request")
        except:
            LOG.error("ERROR")
            self.handle_error(request, client_address)
        finally:
            LOG.debug('Shutdown req: %s' % request)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        p = multiprocessing.Process(
                target=self.process_request_child,
                args=(request, client_address))
        p.start()
        self.shutdown_request(request)


class HTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    LOG = logging.getLogger("RQH")
    def do_GET(self):
        try:
            pos = self.path.rfind(':')
            host = self.path[:pos]
            port = int(self.path[pos+1:])
            LOG.debug('host: %s, port: %s' % (host, port))
        except Exception:
            print "RQH - Ex"
            self.send_response(400)
            self.end_headers()

        try:
            #dest_sock = socket.create_connection((host, port))
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_sock.bind(('', 0))
            self.wfile.write(self.protocol_version + ' 200 Connection established - port: %s\n' % listen_sock.getsockname()[1])
            self._start_read_write(listen_sock, host, port)

        except Exception as exp:
            self.send_response(500)
            self.end_headers()
            LOG.error('failed %s' % exp)

    def _start_read_write(self, listen_sock, host, port):

        p = multiprocessing.Process(
                target=self.process_request_child,
                args=(listen_sock, host, port))
        p.start()

    def process_request_child(self, listen_sock, host, port):
        try:
            listen_sock.listen(300)
        except socket.error:
            sys.exit()

        #src_sock, address = listen_sock.accept()
        #dest_sock.setblocking(0)
        listen_sock.setblocking(0)
        print "calling gluesockets src: %s, host: %s, port: %s" % (listen_sock, host, port)
        gluesockets(listen_sock, host, port)


#class ProcessingTCPSocketServer(MultiProcessingMixIn, SocketServer.TCPServer):
class ProcessingTCPSocketServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    HOST, PORT = "", 54321

    Handler = HTTPRequestHandler
    server = ProcessingTCPSocketServer((HOST, PORT), Handler)
    ip, port = server.server_address
    server.serve_forever()

