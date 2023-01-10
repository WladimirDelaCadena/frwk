from __future__ import print_function

import socket
from datetime import datetime
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor, defer
from os.path import exists
from datetime import datetime
import struct
import random
import time
import threading
from timer_server import RepeatedTimer
from threading import Timer

BUFFER_SIZE = 1024  ## Buffer size (message is sent in chungs of BUFFER_SIZE bytes)
HOST_IP = "127.0.0.1" ## Local IP is enough for this project
TIMEOUT_SEC = 0.1
PROBABILITY = 0.9 # Success probability
log_pack = True # True for verbose logging at packet level
N_CLIENTS = 2

def create_packet(packet_type, window_size,seq_number):
	packet = struct.pack('!bbH', packet_type,window_size, seq_number)
	return packet

def recv_and_unpack(data):
	# Now lets unpack the data. Two first bytes are headers (type and window size)
	type_pck, window, seq_number = (struct.unpack('!bbH',data[0:4]))
	payload = data[4:]
	return payload, window, type_pck, seq_number

def get_data_from_request(data):
	payload, window, type_pck, seq_number = recv_and_unpack(data)
	if (type_pck == 0):
		data_file = "/home/gina/Documents/networking_project/frwk/server/data/" + (payload).decode("utf-8") 
		#data_file = "/home/mars/Downloads/temp/networking_project/server/data/" + (payload).decode("utf-8") 
		if (exists(data_file) == False):
			print ("File does not exist, exiting...!!!")
			return 0
		#Read first chunck of Buffer bytes.
		file_open = open(data_file, "rb")
		return file_open



		
def wrapper_send(self, datagram, dst_ip, dst_port):
	r = random.uniform(0,1)
	if (r <= PROBABILITY):
		sent_bytes = self.transport.write(datagram, (dst_ip, dst_port))
		return sent_bytes,1
	else:
		return len(datagram),0 # Even if we dont send,
							  #the assumption is that the server 
							  # indeed sent the packes and got lost on the way


def timeout_func(self,id):
	self.expired_timer[id] =  1

def send_udp_packets(self, file_, dst_ip, dst_port):
	
	print("[%s]Starting sending thread to %s:%d [%d]" % (str(datetime.now()),dst_ip, dst_port, self.window_size))
	#Read first chunck of Buffer bytes.
	seq_number = 0
	next_seq = 0 
	id_client = dst_port - 9010 # Dirty way of getting Client ID
	total_sent_bytes = 0
	initial_time = datetime.now()
	n_retransmissions = 0
	# Lets start the timer for this transmission
	pck_buffer = [''] * self.window_size
	# Preparing the window buffer of packets
	for i in range(0,self.window_size):
		f_read = file_.read(BUFFER_SIZE)
		pck_buffer[i] = f_read

	j = 0; k = 0
	self.timer_clients[id_client].start()
	already_moved = 0
	while (True):
		# Send N packets in the window
		if (pck_buffer[k] == b''): # No more packets to send from the file
			break
		while (next_seq < self.base_pos[id_client] + self.window_size):
			already_moved = 0
			if (k >= self.window_size):
				k = self.window_size - 1
				pck_buffer[k] = file_.read(BUFFER_SIZE)
				already_moved = 1
			pck = create_packet(1, self.window_size, seq_number)
			sent_bytes, simul = wrapper_send(self, pck + pck_buffer[k], dst_ip, dst_port)
			total_sent_bytes += sent_bytes
			j += 1
			print("[%s]Sent [%d] %d bytes, to %s:%d seq_number sent=%d total_send=%d" % (str(datetime.now()), simul,
					sent_bytes, dst_ip, dst_port,seq_number, total_sent_bytes))
			if (already_moved == 0):
				pck_buffer[k %  self.window_size] = file_.read(BUFFER_SIZE)
				k += 1
			self.last_sent[id_client] = seq_number
			next_seq += 1
			seq_number +=1
			if (k == 0):
				last_base_sent = seq_number
		if (self.expired_timer[id_client] ==  1):
			#print ("I need to try again all the window")
			n_retransmissions += 1
			self.base_pos[id_client] = self.last_sent[id_client]
			self.timer_clients[id_client].stop()
			self.timer_clients[id_client].start()
			self.expired_timer[id_client] =  0
			k = 0
			seq_number =  self.base_pos[id_client] - (self.base_pos[id_client] % self.window_size)
			next_seq = seq_number

		if (self.expired_timer[id_client] ==  0 and k == self.window_size):
			k = 0
 		
	# Sending FIN packet
	pck = create_packet(3, self.window_size, next_seq)
	sent_bytes = self.transport.write(pck, (dst_ip, dst_port))
	total_sent_bytes += sent_bytes
	final_time = datetime.now()
	time_diff = (final_time - initial_time)
	execution_time_sec = time_diff.total_seconds()
	data_rate_kbps = total_sent_bytes / (1000*(execution_time_sec))
	print ("[%s]Sent %d bytes (FIN) to %s:%d total_sent=%d in %d secs. Rate[kbps]=%0.2f Retransm=%d"%
	(str(datetime.now()), sent_bytes, dst_ip, dst_port,total_sent_bytes, execution_time_sec,data_rate_kbps, n_retransmissions))




class Echo(DatagramProtocol):
	received_acks = N_CLIENTS
	N = 2
	window_size = 0
	last_acks = [-1] * 1000
	timer_clients = [0] * 1000
	base_pos = [0] * 1000
	last_sent = [-1] * 1000
	expired_timer = [0]*1000
	def datagramReceived(self, data, addr):
		#print("[%s]Pck received %r from %s" % (str(datetime.now()),data, addr))	
		_, self.window_size, type_pck, seq_number_rx = recv_and_unpack (data)
		id_client = addr[1] - 9010 # Dirty way to get the ID, can be improved
		if (type_pck == 0): # This is an INIT_REQ from a client
			#Start timer for this client
			rt = RepeatedTimer(TIMEOUT_SEC, timeout_func, self,id_client,)
			self.timer_clients[id_client] = rt
			file2send = get_data_from_request(data)
			if (file2send): # Start send thread	
				thr = threading.Thread(target=send_udp_packets, args=(self, file2send, addr[0], addr[1],))
				thr.start()
		if (type_pck == 2): #An ack has arrived, store the acked seq_number on the per-client memory
			#print ("Ack recieved for packet",datetime.now(), seq_number_rx,self.last_acks[id_client])
			if (seq_number_rx == self.last_acks[id_client] + 1):
				self.base_pos[id_client] += 1
				self.timer_clients[id_client].stop()
				self.timer_clients[id_client].start()
			self.last_acks[id_client] = seq_number_rx




# Create new socket that will be passed to reactor later.
portSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Make the port non-blocking and start it listening.
portSocket.setblocking(False)
portSocket.bind(('127.0.0.1', 9999))

# Now pass the port file descriptor to the reactor.
port = reactor.adoptDatagramPort(portSocket.fileno(), socket.AF_INET, Echo())

# The portSocket should be cleaned up by the process that creates it.
portSocket.close()

reactor.run()
