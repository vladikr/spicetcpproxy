import errno
import multiprocessing
import select
import SimpleHTTPServer
import socket
import SocketServer
import BaseHTTPServer


class MultiProcessingMixIn:
    """Mix-in class to handle each request in a new process."""

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

    def process_request_child(self, request, client_address):
        """Same as in BaseServer but as a process.

        In addition, exception handling is done here.

        """
        try:
            self.finish_request(request, client_address)
        except:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        p = multiprocessing.Process(
                target=self.process_request_child,
                args=(request, client_address))
        p.start()


#class HTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_CONNECT(self):
        try:
            pos = self.path.rfind(':')
            host = self.path[:pos]
            port = int(self.path[pos + 1:])
            print 'host: %s, port: %s' % (host, port)
            print self.request.getpeername()
            print self.request.getsockname()
        except Exception as ex:
            print ex
            self.send_response(400)
            self.end_headers()
            raise

        try:
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.connect((host, port))
            #new_sock = socket.create_connection((host, port))
            self.send_response(200, 'Connection established')
            #self.end_headers()
            try:
                self._start_read_write(new_sock)
            except IOError as e:
                if e.errno != errno.EPIPE:
                    raise
        except Exception as exp:
            #self.send_response(500)
            #self.end_headers()
            print 'failed %s' % exp
        finally:
            new_sock.close()
            self.connection.close()

    def _start_read_write(self, sock):
        #sock.setblocking(1)
        #self.request.setblocking(1)
        conns = {self.request: sock, sock: self.request}
        expl = {self.request: 'source', sock: 'destrination'}
        print "calling gluesockets %s" % conns
        close_conn = False
        while True:
            reads, writes, excepts = select.select(conns.keys(), [],
                                                   conns.keys(), 1)
            if excepts or not reads:
                print 'excepts: %s' % excepts
                print 'reads: %s' % reads
                print 'writes: %s' % writes
                break
            if reads:
                print 'rl: %s' % reads
                for conn in reads:
                    print 'getting from %s' % expl[conn]
                    data = conn.recv(1024)  # 8192
                    if data:
                        print 'len: %s' % len(data)
                        print 'data: %s' % repr(data)
                        print 'sending to: %s' % expl[conns[conn]]
                        conns[conn].send(data)
                    else:
                        close_conn = True
                        print "closing"
                        break


#class ProcessingTCPSocketServer(MultiProcessingMixIn, SocketServer.TCPServer):
#class ProcessingTCPSocketServer(MultiProcessingMixIn,
#                                BaseHTTPServer.HTTPServer):
class ProcessingTCPSocketServer(SocketServer.ThreadingMixIn,
                                SocketServer.TCPServer):
    pass


if __name__ == "__main__":
    HOST, PORT = "", 54321

    Handler = HTTPRequestHandler
    server = ProcessingTCPSocketServer((HOST, PORT), Handler)
    ip, port = server.server_address
    server.serve_forever()
