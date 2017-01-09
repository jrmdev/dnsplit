#!/usr/bin/env python
import sys
import time
import json
import threading
import netifaces
import SocketServer

from random import choice
from fnmatch import fnmatch
from netaddr import IPAddress, IPSet
from dnslib import *

__program__ = 'dnsplit'
__version__ = 0.2

class DNSForwarder():

	# Parse a raw DNS packet.
	def parse(self, request):

		response = ""
	
		try: d = DNSRecord.parse(request)
		except: pass

		# Only Process DNS Queries
		if QR[d.header.qr] == "QUERY":  
				 
			# Gather query parameters
			qname = str(d.q.qname).strip('.')

			# Forward the query to the right server
			response = self.proxyrequest(qname, request)

		return response

	# Find which DNS server to use according to the rules.
	def find_ns(self, qname):
		
		for rule in self.server.cfg.rules:

			if 'match' in rule:
				for match in rule['match']:

						if fnmatch(qname, match):
							# The rule matches the current query
							# If there is no condition, return the nameserver directly.
							# Otherwise check if the condition is met
							if 'condition' not in rule or is_condition_met(rule):
								return choice(rule['nameservers'])

			else:
				# This rule has no "match" parameter
				# so it must have a condition.
				if is_condition_met(rule):
					return choice(rule['nameservers'])

		# No rule match, use one of the default ns
		return choice(self.server.cfg.default_nameservers)

	# Obtain a response from a DNS server.
	def proxyrequest(self, qname, request):
		reply = None

		ns = self.find_ns(qname)

		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.settimeout(3.0)
			sock.sendto(request, (ns, 53))
			reply = sock.recv(1024)
			sock.close()

			d = DNSRecord.parse(reply)
			print "[i] Forwarded query for '%s' to '%s' and got reply '%s' " % (qname, ns, d.rr[0].rdata)

		except Exception, e:
			print "[!] Could not proxy request %s to %s: %s" % (qname, ns, e)
		else:
			return reply

# UDP DNS Handler for incoming requests
class UDPHandler(DNSForwarder, SocketServer.BaseRequestHandler):

	def handle(self):

		(data, socket) = self.request
		response = self.parse(data)
		
		if response:
			socket.sendto(response, self.client_address)

class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):

	# Override SocketServer.UDPServer to add extra parameters
	def __init__(self, server_address, RequestHandlerClass, cfg):
		self.cfg = cfg
		
		SocketServer.UDPServer.__init__(self, server_address, RequestHandlerClass) 

def is_condition_met(rule):

	if rule['interface'] not in netifaces.interfaces():
		return False

	if rule['type'] == 'state':

		addr = netifaces.ifaddresses(rule['interface'])
		
		if rule['state'] == 'up' and netifaces.AF_INET in addr:
			return True

		if rule['state'] == 'down' and netifaces.AF_INET not in addr:
			return True

	elif rule['type'] == 'network':

		addresses = netifaces.ifaddresses(rule['interface'])
		for addr in addresses[netifaces.AF_INET]:
			if addr['addr'] in rule['network']:
				return True

	return False

class Config:

	def __init__(self):

		self.config_file = os.path.join('/', 'etc', '%s.conf' % __program__)

		if not os.path.exists(self.config_file):
			sys.exit('[!] error: configuration file "%s" not found.' % self.config_file)

		with open(self.config_file) as f:

			config = '\n'.join(l for l in f.read().split('\n') if not l.strip().startswith('//'))

			try:
				config = json.loads(config)
			except Exception, e:
				sys.exit("[!] error: configuration file could not be parsed as valid JSON."+ str(e))

			self.bind = (config['listen-addr'], config['listen-port'])
			self.default_nameservers = config['default-nameservers']
			self.rules = config['rules']

			# Some consistency checks to validate the rules
			for rule in self.rules:

				if not isinstance(rule['match'], list):
					rule['match'] = list(rule['match'])

				if 'condition' not in rule and 'match' not in rule:
					sys.exit('[!] error: rule "%s" needs at least a "match" or a "condition" parameter.' % rule['name'])

				if 'condition' in rule:
					try:
						intf, param = rule['condition'].split()
					except:
						sys.exit('[!] error: rule "%s": wrong condition format.' % rule['name'])

					rule['interface'] = intf

					if param not in ['up', 'down']:
						try:
							rule['type'] = 'network'
							rule['network'] = IPSet([param])

						except netaddr.core.AddrFormatError:
							sys.exit('[!] error: rule "%s": invalid network specification.' % rule['name'])
					else:
						rule['type'] = 'state'
						rule['state'] = param

		f.close()

def main():

	cfg = Config()

	server = ThreadedUDPServer(cfg.bind, UDPHandler, cfg)

	# Start the main server thread
	server_thread = threading.Thread(target=server.serve_forever)
	server_thread.daemon = True
	server_thread.start()

	print "%s v%.2f started" % (__program__, __version__)

	# Loop in the main thread
	while True:
		try: time.sleep(100)
		except KeyboardInterrupt: break

	server.shutdown()

if __name__ == '__main__':
	main()