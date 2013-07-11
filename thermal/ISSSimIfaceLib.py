#! /usr/bin/python
import threading
import socket
from robot.api import logger
from HSDatabase import *
from TelmDatabase import *
from CmdDatabase import *
import CCSDS
import select
import time
import Queue
import sys
import time
import unittest
import crcmod

class SessionThread(threading.Thread):
    
    ROBOT_LIBRARY_SCOPE = "TEST SUITE"
    def __init__(self,cmdQ,hs_sock,telm_sock,dbFilename,hsRecvEvent,telmRecvEvent):
        threading.Thread.__init__(self)
        self.cmdQ = cmdQ
        self.cmd_ip = '127.0.0.1'
        self.cmd_port = 2001
        self.hs_sock = hs_sock
        self.telm_sock = telm_sock
        self.rx_socks = [self.hs_sock,self.telm_sock]

        self.dbFilename=dbFilename       
        
        self._stop = threading.Event()
        self._hsRecvEvent = hsRecvEvent
        self._telmRecvEvent = telmRecvEvent
        self.byteSwap = False
        self.hsPacketSize = 1024
        self.telmPacketSize = 1024

        self.txSeqCnt = 0
        self.timeout = 0.1
        self.recvdHsPackets = 0
        self.recvdTelmPackets = 0
        
        self.hsRxSeqCnt = 0
        self.telmRxSeqCnt = 0
        self.hsAPID=0
        self.telmAPID=0
        
        self.telmDataRate = 0.0
        self.telmLastRxTime = 0.0

        self.enableCorruption = False
        self.fieldToCorrupt = ""

    #TODO these need mutexes....
    def set_packet_sizes(self,hsPacketSize,telmPacketSize):
        self.hsPacketSize = hsPacketSize
        self.telmPacketSize = telmPacketSize

    def set_byte_swap(self,byteSwap):
        self.byteSwap=byteSwap

    def set_cmd_addr(self,cmdIp,cmdPort):
        self.cmd_ip = cmdIp
        self.cmd_port = cmdPort

    def set_select_timeout(self,timeout):
        self.timeout = timeout

    def run(self):
        print "Starting thread" 
        self.cmdDatabase = CmdDatabase(self.dbFilename) 
        hsTableValid = self.cmdDatabase.is_valid_table(self.cmdDatabase.tableName)
        if not hsTableValid:
            raise RuntimeError("Table %s not found in %s " 
                                    % (self.cmdDatabase.tableName,self.dbFilename))
        
        self.hsDatabase = HSDatabase(self.dbFilename) 
        hsTableValid = self.hsDatabase.is_valid_table(self.hsDatabase.tableName)
        if not hsTableValid:
            raise RuntimeError("Table %s not found in %s " 
                                    % (self.hsDatabase.tableName,self.dbFilename))
        
        self.telm_database = TelmDatabase(self.dbFilename) 
        telmTableValid = self.telm_database.is_valid_table(self.telm_database.tableName)
        if not telmTableValid:
            raise RuntimeError("Table %s not found in %s!" 
                                    % (self.telm_database.tableName,self.dbFilename))

        while True:
            readable,writable,errord = select.select(self.rx_socks,[],[],self.timeout)
            currTime = time.time()
            
            if self.hs_sock in readable:
                buf,addr = self.hs_sock.recvfrom(self.hsPacketSize)
                buf = bytearray(buf)
                if self.byteSwap:
                    buf = byte_swap_bytearray(buf)
                packet = CCSDS.CCSDSPacket(buf)
                self.hsRxSeqCnt =  packet.get_seq_cnt()
                self.hsAPID = packet.get_APID()
                data = packet.get_data()
                
                self.hsDatabase.insert_packet(currTime,self.hsRxSeqCnt,data)
                
                self.recvdHsPackets+=1
                self._hsRecvEvent.set()

            if self.telm_sock in readable:
                buf,addr = self.telm_sock.recvfrom(self.telmPacketSize)
                buf = bytearray(buf)
                if self.byteSwap:
                    buf = byte_swap_bytearray(buf)
                packet = CCSDS.CCSDSPacket(buf)
                self.telmRxSeqCnt =  packet.get_seq_cnt()
                self.telmAPID = packet.get_APID()
                data = packet.get_data()
                crcRxd = packet.get_crc() 
                crcCalcd = packet.compute_crc_checksum()
                if crcRxd == crcCalcd: 
                    self.telm_database.insert_packet(currTime,self.telmRxSeqCnt,data)
                    
                    self.telmDataRate = 1/(currTime - self.telmLastRxTime)
                    self.telmLastRxTime =  currTime
                    self.recvdTelmPackets+=1
                    self._telmRecvEvent.set()
                else:
                    print "CRC ERROR"
                    logger.warn("CRC ERROR!")

            if self.cmdQ.empty() == False:
                currEpochTime = time.time()
                cmd = self.cmdQ.get()
                cmdPacket = CCSDS.CCSDSPacket(dataLength=len(cmd))

                if self.fieldToCorrupt == "Headers":
                    cmdPacket.set_primary_header(seqCnt=42,version=1,type=0,
                                                APID=1234,secHdrFlag=0,seqFlags=2,
                                                packetLen=10)
                    cmdPacket.set_secondary_header(timeUnix=currEpochTime,chkSumInd=0,spare=1)
                else:
                    cmdPacket.set_primary_header(self.txSeqCnt)
                    cmdPacket.set_secondary_header(timeUnix=currEpochTime)

                if self.fieldToCorrupt == "Data":
                    buf = bytearray("Phillip is a 133t H4x0r")
                    cmdPacket.set_data(buf)
                else:
                    buf = bytearray()
                    buf = zero_pad(4)
                    buf.extend(cmd)
                    cmdPacket.set_data(buf)
                
                if not self.fieldToCorrupt == "Checksum":
                    cmdPacket.compute_checksum()

                if self.enableCorruption:
                    self.fieldToCorrupt = ""

                if self.byteSwap:
                    cmdPacket.raw = byte_swap_bytearray(cmdPacket.raw)
                
                cmdPacket.raw = cmdPacket.raw.ljust(128,"\00")

                cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                cmd_sock.sendto(cmdPacket.raw,(self.cmd_ip,self.cmd_port))
                cmd_sock.close()
                self.cmdQ.task_done()
                self.cmdDatabase.insert(currTime,self.txSeqCnt,cmd)
                self.txSeqCnt+=1

            if self._stop.isSet():
                break

        return

    def stop(self):
        self._stop.set()

    def corrupt_next_cmd(self,fieldToCorrupt):
        self.enableCorruption = True
        self.fieldToCorrupt = fieldToCorrupt


    def wait_for_next_hs_packet(self,timeoutSecs):
        self._hsRecvEvent.clear()
        self._hsRecvEvent.wait(timeoutSecs)
        ret = self._hsRecvEvent.is_set()
        self._hsRecvEvent.clear()
        return ret

    def wait_for_next_telm_packet(self,timeoutSecs):
        self._telmRecvEvent.clear()
        self._telmRecvEvent.wait(timeoutSecs)
        ret = self._hsRecvEvent.is_set()
        self._telmRecvEvent.clear()
        return ret


class ISSSimIfaceLib:
    ROBOT_LIBRARY_SCOPE = "TEST SUITE"
    cmd_port    = 10000
    hs_port     = 11000
    telm_port   = 12000

    cmd_ip  = '127.0.0.1'
    hs_ip   = '127.0.0.1'
    telm_ip = '127.0.0.1' 

    hs_sock     = None
    telm_sock   = None
    txSeqCnt      = 0
     
    session = None

    def __init__(self, cmd_schema_filename, cmd_dict_filename, cmd_dict_sheet, \
            hs_dict_filename, hs_dict_sheet, \
            telm_schema_filename, \
            dbFilename="roboSCAT.db",byteSwap=False):
        logger.info("Loading ISS Sim Interface Library")
        self.dbFilename = dbFilename
        self.cmd_schema_filename = cmd_schema_filename
        self.cmd_dict_filename = cmd_dict_filename
        self.cmd_dict_sheet = cmd_dict_sheet
        self.hs_dict_filename = hs_dict_filename
        self.hs_dict_sheet = hs_dict_sheet
        self.telm_schema_filename = telm_schema_filename

        self.cmd_database = CmdDatabase(self.dbFilename)
        self.hs_database = HSDatabase(self.dbFilename)
        self.telm_database = TelmDatabase(self.dbFilename)
        self.byteSwap = byteSwap

        self.hsPacketSize = 1024
        self.telmPacketSize = 1024

        self.viewer = None

    def load_cmd_database(self,reload='False'):
        cmdDatabaseLoaded = self.cmd_database.is_valid_table(self.cmd_database.tableName)
        if (not cmdDatabaseLoaded) or reload=='RELOAD':
            self.cmd_database.drop_table()
            self.cmd_database.load_schema(self.cmd_schema_filename)
            self.cmd_database.create_table()
            self.cmd_database.load_cmds(self.cmd_dict_filename,self.cmd_dict_sheet,True)
        else:
            self.cmd_database.load_cmds(self.cmd_dict_filename,self.cmd_dict_sheet)
    
    def load_hs_database(self,reload='False'):
        hsDatabaseLoaded = self.hs_database.is_valid_table(self.hs_database.tableName)
        if (not hsDatabaseLoaded) or reload=='RELOAD':
            self.hs_database.drop_table()
            self.hs_database.load_schema(self.hs_dict_filename, self.hs_dict_sheet,True)
            self.hs_database.create_table()
        else:            
            self.hs_database.load_schema(self.hs_dict_filename, self.hs_dict_sheet)

    def load_telm_database(self,reload='False'):
        telmDatabaseLoaded = self.telm_database.is_valid_table(self.telm_database.tableName)
        if (not telmDatabaseLoaded) or reload=='RELOAD':
            self.telm_database.drop_table()
            self.telm_database.load_schema()
            self.telm_database.create_table()

    def set_byte_swap(self,byteSwapEnable):
        if byteSwapEnable == '1':
            logger.info("Enabling byte swapping")
            self.byteSwap = True

    def set_telm_packet_size(self,sizeInBytes):
        self.telmPacketSize = sizeInBytes

    def set_hs_packet_size(self,sizeInBytes):
        self.hsPackdetSize = sizeInBytes

    def drop_tables(self):
        logger.warn("Dropping tables!!!!!!!!!!!!!!!!!!!")
        self.cmd_database.drop_table()
        self.hs_database.drop_table()

    def set_cmd_port(self,cmd_port):
        self.cmd_port = int(cmd_port)
        logger.info("Setting command port to %d" % self.cmd_port)
        
    def set_hs_port(self,hs_port):
        self.hs_port = int(hs_port)
        logger.info("Setting health and status port to %d" % self.hs_port)

    def set_telm_port(self,telm_port):
        self.telm_port = int(telm_port)
        logger.info("Setting telemetry port to %d" % self.telm_port)

    def set_cmd_ip(self,cmd_ip):
        logger.info("Setting command port to %s" % cmd_ip)
        self.cmd_ip = cmd_ip

    def set_hs_ip(self,hs_ip):
        logger.info("Setting health and status port to %s" % hs_ip)
        self.hs_ip = hs_ip

    def set_telm_ip(self,telm_ip):
        logger.info("Setting telemetry port to %s" % telm_ip)
        self.telm_ip = telm_ip

    def corrupt_next_cmd(self,fieldToCorrupt):
        logger.info("Setting cmd packet %s to be corrupted")
        self.session.corrupt_next_cmd(fieldToCorrupt)

    def create_sock(self,ip,port,bind=False,connect=False):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if bind:
                sock.bind((ip,port))
            elif connect:
                sock.connect((ip,port))
        except:
            raise RuntimeError("Can't open socket IP=%s port=%d" % (ip, port))
        return sock

    def set_viewer(self,viewerObj):
        self.viewer = viewerObj

    def start_session(self):
        logger.info("Starting session with the ISS sim")
       
        self.hs_sock = self.create_sock(self.hs_ip,self.hs_port,bind=True)
        self.telm_sock = self.create_sock(self.telm_ip,self.telm_port,bind=True)

        self.cmdQ = Queue.Queue()
        hsRecvEvent = threading.Event()
        telmRecvEvent = threading.Event()
        self.session = SessionThread(self.cmdQ,self.hs_sock,self.telm_sock,\
                                    self.dbFilename,hsRecvEvent,telmRecvEvent)
        self.session.set_cmd_addr(self.cmd_ip,self.cmd_port)
        self.session.set_packet_sizes(self.hsPacketSize,self.telmPacketSize)
        self.session.set_byte_swap(self.byteSwap)

        if self.viewer:
            self.viewer.start()

        self.session.start()
        logger.info("Session started")

    def stop_session(self):
        logger.info("Stopping session with the ISS sim")
        if self.session != None:
            self.session.stop()
            self.session.join()
        logger.info("Session stopped")

    def terminate_session(self):
        logger.info("Terminating session with the ISS sim")
        if self.session != None:
            self.session.stop()
            self.session.join()

        if self.hs_sock != None:
            self.hs_sock.close()

        if self.telm_sock != None:
            self.telm_sock.close()
        logger.info("Session terminated")

    def send_cmd(self,cmd_name,*args):
        cmdFormat = self.cmd_database.get_cmd_format(cmd_name)
        cmd  = self.cmd_database.build_cmd(cmdFormat,args)
        self.cmdQ.put(cmd)
        logger.info("Sending cmd %s" % cmd_name)
 
    def read_hs_field(self,field_name):
        ret = self.hs_database.read_hs_field(field_name)
        return ret

    def get_received_hs_packet_count(self):
        return self.session.recvdHsPackets

    def get_received_telm_packet_count(self):
        return self.session.recvdTelmPackets

    def get_hs_seq_count(self):
        return self.session.hsRxSeqCnt

    def get_telm_seq_count(self):
        return self.session.telmRxSeqCnt

    def get_cmd_seq_count(self):
        return self.session.txSeqCnt
    
    def get_cmd_opCode(self,cmdName):
        return self.cmd_database.get_opCode_from_cmdName(cmdName)
    
    def get_hs_APID(self):
        return self.session.hsAPID

    def get_telm_APID(self):
        return self.session.telmAPID

    def get_telm_data_rate(self):
        return self.session.telmDataRate

    def get_last_telm_packet(self):
        return self.telm_database.read_packet() 

    def wait_for_hs_packet(self,timeoutSecs=60):
        if not self.session.isAlive():
            logger.warn("Can't wait for packet if session not open!")
            raise RuntimeError("Session not open!")
        logger.info("Waiting for HS packet with a timeout of %d s" % timeoutSecs)
        if not self.session.wait_for_next_hs_packet(timeoutSecs):
            raise RuntimeError("Didn't recieve packet in %s secs" % timeoutSecs)
        return True

    def wait_for_telm_packet(self,timeoutSecs=60):
        if not self.session.isAlive():
            logger.warn("Can't wait for packet if session not open!")
            raise RuntimeError("Session not open!")
        logger.info("Waiting for HS packet with a timeout of %d s" % timeoutSecs)
        if not self.session.wait_for_next_telm_packet(timeoutSecs):
            raise RuntimeError("Didn't recieve packet in %s secs" % timeoutSecs)
        return True
   
    def convert_temp_to_celsius(self,value,calibration):
        value =  float(value)
        calibration = float(calibration)
        return convert_to_celsius(value,calibration)

    def convert_ccsds_time_to_unix(self,ccsdsTime):
        ccsdsTime = bytearray(ccsdsTime)
        timeFine,timeCoarse = unpack_ISS_time(ccsdsTime)
        timeUnix = convert_ISS_to_unix_time(timeFine,timeCoarse,leapSecs=0, 
                            gpsEpochStart=( 1970,1,1,0,0,0,3,6,-1))
        return timeUnix
        
class TestIface(unittest.TestCase):

    def setUp(self):
        #cmdip = "192.168.12.131"
        #hsip = "137.79.160.96"
        #telmip = 
        cmdip = "127.0.0.1"
        hsip = cmdip
        telmip = cmdip
        cmdSchema = "../data/cmd_db_schema.txt"
        cmdDict = "../data/testDict.xlsx"
        cmdSheet = "A24_A29"
        telmSchema = "../data/telm_db_schema.txt"
        self.simIf = ISSSimIfaceLib(cmdSchema,cmdDict,cmdSheet,cmdDict,"A3_A4_A23",telmSchema)
        self.simIf.set_cmd_port("2200")
        self.simIf.set_cmd_ip(cmdip)
        self.simIf.set_hs_port("2201")
        self.simIf.set_hs_ip(hsip)
        self.simIf.set_telm_port("2205")
        self.simIf.set_telm_ip(telmip)
        self.simIf.load_cmd_database()
        self.simIf.load_hs_database()
        self.simIf.load_telm_database()
        self.simIf.start_session()

    def test_snd_cmd(self):
        self.simIf.send_cmd("RS_K9_SET")
        time.sleep(0.5)
        ret = self.simIf.cmd_database.select_from_last_row(('opCode',))[0][0]
        print ret
        assert(ret==43713)

    def test_get_cmd_opCode(self):
        self.simIf.send_cmd("RS_K9_SET")
        time.sleep(0.5)
        ret = self.simIf.get_cmd_opCode("RS_K9_SET")
        print ret
        assert(ret==43713)

        
    def test_snd_many_cmds(self):
        self.simIf.send_cmd("RS_K1_SET")
        self.simIf.send_cmd("RS_K2_SET")
        self.simIf.send_cmd("RS_K3_SET")
        self.simIf.send_cmd("RS_K4_SET")
        self.simIf.send_cmd("RS_K5_SET")
        self.simIf.send_cmd("RS_K6_SET")
        self.simIf.send_cmd("RS_K7_SET")
        self.simIf.send_cmd("RS_K8_SET")
        self.simIf.send_cmd("RS_K9_SET")
        self.simIf.send_cmd("RS_K10_SET")
        self.simIf.send_cmd("RS_K11_SET")
        self.simIf.send_cmd("RS_K12_SET")
        self.simIf.send_cmd("RS_K13_SET")
        self.simIf.send_cmd("RS_K14_SET")
        self.simIf.send_cmd("RS_K15_SET")
        self.simIf.send_cmd("RS_K16_SET")
        self.simIf.send_cmd("RS_K17_SET")
        self.simIf.send_cmd("RS_K18_SET")
        time.sleep(10)

    def test_rx_many(self):
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        assert(self.simIf.wait_for_hs_packet(60))
        packetsRxd = self.simIf.get_received_hs_packet_count()

        ret = self.simIf.get_hs_seq_count()
        print ret

    def test_snd_rx(self):
        assert(self.simIf.wait_for_hs_packet(60))
        self.simIf.send_cmd("RS_K1_SET")
        assert(self.simIf.wait_for_hs_packet(60))
        CmdsRxd = self.simIf.read_hs_field("Commands received")
        ValidCmdCnt = self.simIf.read_hs_field("Valid command count")

        print CmdsRxd
        print ValidCmdCnt

    def test_rx_telm(self):
        assert(self.simIf.wait_for_telm_packet(5))
        assert(self.simIf.wait_for_telm_packet(5))

        assert(self.simIf.get_telm_APID() == 1390)

        delta = abs(1 - self.simIf.get_telm_data_rate())
        print self.simIf.get_telm_data_rate()

        assert(delta <= 0.1)
        assert(self.simIf.get_received_telm_packet_count() >= 2)

        print print_buf(self.simIf.get_last_telm_packet())

    def test_corrupt_cmd(self):
        self.simIf.send_cmd("RS_K1_SET")
        time.sleep(0.1)
        self.simIf.corrupt_next_cmd("Headers")
        self.simIf.send_cmd("RS_K1_SET")
        time.sleep(0.1)
        self.simIf.corrupt_next_cmd("Data")
        self.simIf.send_cmd("RS_K1_SET")
        time.sleep(0.1)
        self.simIf.corrupt_next_cmd("Checksum")
        self.simIf.send_cmd("RS_K1_SET")
        time.sleep(0.1)

    def test_time_conv(self):
        currTime = time.time()
        assert(self.simIf.wait_for_hs_packet(60))
        spaceCraftTime = self.simIf.read_hs_field("Spacecraft time")
        
        spaceCraftTime = self.simIf.convert_ccsds_time_to_unix(spaceCraftTime)

        assert (abs(currTime-spaceCraftTime) < 2)

    def tearDown(self):
        self.simIf.terminate_session()
        self.simIf.drop_tables()


if __name__ == '__main__':
    unittest.main() 
