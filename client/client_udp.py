from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol

import argparse
import socket
import struct
from datetime import datetime
import time
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", type=int, help="Port of the listening Server", default='9999')
parser.add_argument("-i", "--id", type=int, help="ID. of this Client", default='1')
parser.add_argument("-f", "--file", type=str, help="Name of file to request to the server", default="file1Kb.txt")
parser.add_argument("-w", "--window", type=int, help="Window size (N) datagram for Go-back-N algorithm", default="1")

def create_packet(packet_type, window_size,seq_number):
	packet = struct.pack('!bbH', packet_type,window_size, seq_number)
	return packet

class EchoClientDatagramProtocol(DatagramProtocol):
    strings = [b"Hello, world!"]
    port_server = 8000
    expected_seq = 0
    window_base = 0 
    recv_bytes = 0
    seq_number = 0
    id = 0
    N = 1 
    initial_time = datetime.now()
    
    def startProtocol(self):
        self.transport.connect("127.0.0.1", self.port_server)
        self.sendDatagram()

    def sendDatagram(self):
        if len(self.strings):
            datagram = self.strings.pop(0)
            print ("[%s %d]Sent request to server " % (str(datetime.now()), self.id))
            self.transport.write(datagram)
        #else:
        #    reactor.stop()

        

    def datagramReceived(self, datagram, host):
        #Packet type: 0 is for INIT_REQ, 1 is for DATA, 2 for ACK, 3 for FIN
        self.recv_bytes += len(datagram)    
        type_pck, window, seq_number = (struct.unpack('!bbH',datagram[0:4]))
        #print("[%s %d] seq_received=%d, seq_expected=%d" % (str(datetime.now()), self.id, seq_number, self.expected_seq))
        base_win = 0
        if (seq_number != self.expected_seq and type_pck == 1):
            print ("[%s %d]Out-of-order Received num_seq=%d total_recv=%d" % (str(datetime.now()), self.id,
             seq_number, self.recv_bytes))
            # reset the seq of this window
            self.expected_seq = seq_number - (seq_number % window)
            self.recv_bytes += len(datagram)    

        if (seq_number == self.expected_seq and type_pck == 1): # The packet is the one we expected, we can process	
            print ("[%s %d]Received type_pck [%d] %d bytes seq_num=%d exp_seq_num=%d total_recv=%d" % (str(datetime.now()), self.id, type_pck, 
            len(datagram), seq_number, self.expected_seq, self.recv_bytes))
            #print (datagram)
            pck = create_packet(2, self.N, seq_number) # Ackowledging packet seq_number
            time.sleep(0.00001) # To avoid some out of timestamp ack due to testing on localhost
            self.transport.write(pck, ("127.0.0.1", int(self.port_server)))
            self.expected_seq += 1  
        if (type_pck == 3): # Received a FIN connection
            print ("[%s %d]Receivied FIN packet recv_bytes=%d total_recv=%d" % (str(datetime.now()), 
            self.id, len(datagram),self.recv_bytes)) 
            reactor.stop()
            # Calculate statss
            final_time = datetime.now()
            time_diff = (final_time - self.initial_time)
            execution_time_sec = time_diff.total_seconds()
            data_rate_kbps = self.recv_bytes / (1000*(execution_time_sec))
            print ("[%s]Finished: Received %d bytes, in %0.2f secs. Rate[kbps]=%0.2f"%(str(datetime.now()),
            self.recv_bytes, execution_time_sec, data_rate_kbps))
            #f.close()

  
def main(server_,port_,file_, window_, id_):
    protocol = EchoClientDatagramProtocol()
    protocol.port_server = 9999
    protocol.id = id_
    protocol.N = window_
    # Assembly packet to send  request to the server
    #Type: 0 is for INIT_REQ, 1 is for DATA, 2 for ACK, 3 for FIN
    pck = create_packet(0, window_, 0)
    msg = pck + file_.encode()
    protocol.strings = 	[msg]
    # Start reactor
    reactor.listenUDP(port_, protocol)
    reactor.run()


if __name__ == "__main__":
    args = parser.parse_args()
    server_ = args.server
    id_ = args.id
    port_ = int(9010 + int(id_))
    file_ = args.file
    window_ = args.window
    main(server_,port_,file_, window_, id_)