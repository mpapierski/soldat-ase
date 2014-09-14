import struct
import sys
import signal
import subprocess
import SocketServer
import ConfigParser
from threading import Thread
from StringIO import StringIO

def read_gamestat():
    with open('logs/gamestat.txt') as fp:
        log = fp.read().splitlines()
        logdata = {}
        logdata['numplayers'] = int(log[1][9:])
        logdata['mapname'] = log[2][5:]
        logdata['gametype'] = log[3][10:]
        logdata['timeleft'] = log[4][10:]
        teamscores = {}
        if logdata['gametype'] == "Capture the Flag" or logdata['gametype'] == "Infiltration":
            teamscores['alpha'] = int(log[5][8:])
            teamscores['bravo'] = int(log[6][8:])
        elif logdata['gametype'] == "Team Deathmatch":
            teamscores['alpha'] = int(log[5][8:])
            teamscores['bravo'] = int(log[6][8:])
            teamscores['charlie'] = int(log[7][8:])
            teamscores['delta'] = int(log[8][8:])
        logdata['teamscores'] = teamscores
        # And now for individual players.
        numplayers = logdata['numplayers']
        playerdata = []
        players_index = log.index('Players list: (name/kills/deaths/team/ping)') + 1
        for i in xrange(numplayers):
            pos = players_index + (i * 5)
            name = log[pos]
            points = log[pos+1]
            deaths = log[pos+2]
            team = log[pos+3]
            ping = log[pos+4]
            player = {
                'name': name,
                'points': points,
                'deaths': deaths,
                'team': team,
                'ping': ping
            }
            playerdata.append(player)
        logdata['players'] = playerdata
        return logdata

def read_config():
    cfg = ConfigParser.ConfigParser()
    with open('soldat.ini') as fp:
        cfg.readfp(fp)
        return cfg

class ASEHandler(SocketServer.BaseRequestHandler):
    """
    Request handler for ASE
    """
    def handle(self):
        data, socket = self.request
        if data != 's':
            return
        response = StringIO()
        response.write('EYE1')
        def write_string(text):
            response.write(struct.pack('>B', len(text) + 1))
            response.write(text)
        # Read useful data here
        cfg = read_config()
        # Parse game logs
        stat = read_gamestat()
        # Game name
        write_string('Soldat Server')
        # Port number
        write_string(cfg.get('NETWORK', 'Port'))
        # Server name
        write_string(cfg.get('NETWORK', 'Server_Name'))
        # Game type
        write_string(stat['gametype'])
        # Map name
        write_string(stat['mapname'])
        # Version
        write_string('1.6.7')
        # Passworded
        try:
            game_password = cfg.get('NETWORK', 'Game_Password')
            if not game_password:
                game_password = '0'
            write_string(game_password)
        except ConfigParser.NoOptionError:
            write_string('0')
        # Num players
        write_string(str(stat['numplayers']))
        # Max players
        try:
            write_string(cfg.get('NETWORK', 'Max_Players'))
        except ConfigParser.NoOptionError:
            write_string('16')
        # Send raw data (we have no raw data?)
        write_string('')
        # Send players
        for player in stat['players']:
            flags = 0
            flags |= 1 # Name
            flags |= 2 # Team
            # flags |= 4 # Skin
            flags |= 8 # Score
            flags |= 16 # Ping
            # flags |= 32 # Time
            response.write(struct.pack('>B', flags))
            write_string(player['name']) # flags & 1
            write_string(player['team']) # flags & 2
            write_string(player['points']) # flags & 8
            write_string(player['ping']) # flags & 16
        # Send data
        socket.sendto(response.getvalue(), self.client_address)

def main():
    # Startup
    args = sys.argv[1:]
    proc = subprocess.Popen(['./soldatserver'] + args)
    cfg = read_config()
    try:
        ase_port = cfg.getint('NETWORK', 'Port')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        ase_port = 23073
    ase_port += 123
    server = SocketServer.UDPServer(('0.0.0.0', ase_port), ASEHandler)
    th = Thread(target=server.serve_forever)
    th.daemon = True
    th.start()
    def signal_handler(signum, frame):
        proc.send_signal(signum)
        server.shutdown()
        proc.wait()
        th.join()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    exit_code = proc.wait()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
