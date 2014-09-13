import struct
import sys
import signal
import subprocess
import SocketServer
from threading import Thread
from StringIO import StringIO


class ASEHandler(SocketServer.BaseRequestHandler):
   """
   Request handler for ASE
   """
   def handle(self):
    data, socket = self.request
    sys.stderr.write('ASEHandler request from {}: {!r}\n'.format(self.client_address[0], data))
    if data != 's':
     return
    response = StringIO()
    response.write('EYE1')
    def write_string(text):
      if not text:
        response.write('\x00')
        return
      response.write(struct.pack('>B', len(text) + 1))
      response.write(text)
    # Game name
    write_string('FAKE')
    # Port number
    write_string('1234')
    # Server name
    write_string('server name')
    # Game type
    write_string('game type')
    # Map name
    write_string('map name')
    # Version
    write_string('1.6.7')
    # Passworded
    write_string('0')
    # Num players
    write_string('0')
    # Max players
    write_string('16')
    # Send data
    socket.sendto(response.getvalue(), self.client_address)

def main():
  args = sys.argv[1:]
  proc = subprocess.Popen(['./soldatserver'] + args)
  server = SocketServer.UDPServer(('0.0.0.0', 23196), ASEHandler)
  th = Thread(target=server.serve_forever)
  th.daemon = True
  th.start()
  def signal_handler(signum, frame):
    print 'Received signal', signum
    proc.send_signal(signum)
    print 'Shutdown ASE server'
    server.shutdown()
    print 'Wait for child process'
    proc.wait()
    print 'Wait for ASE server'
    th.join()
    print 'Bye'
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  sys.stderr.write('????\n')
  exit_code = proc.wait()
  sys.exit(exit_code)

if __name__ == '__main__':
  main()
