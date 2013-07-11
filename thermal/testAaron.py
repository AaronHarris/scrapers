#! /usr/bin/python

from ISSSimIfaceLib import *
import subprocess
import sys

def main():
    cmdip = "127.0.0.1"
    hsip = cmdip
    telmip = cmdip
    cmdSchema = "../data/cmd_db_schema.txt"
    cmdDict = "../data/testDict.xlsx"
    cmdSheet = "A24_A29"
    telmSchema = "../data/telm_db_schema.txt"
    simIf = ISSSimIfaceLib(cmdSchema,cmdDict,cmdSheet,cmdDict,"A3_A4_A23",telmSchema)
    simIf.set_cmd_port("2200")
    simIf.set_cmd_ip(cmdip)
    simIf.set_hs_port("2201")
    simIf.set_hs_ip(hsip)
    simIf.set_telm_port("2205")
    simIf.set_telm_ip(telmip)
    simIf.load_cmd_database()
    simIf.load_hs_database()
    simIf.load_telm_database()
    
    # Do your object instatiation here
    
    #Set the viewer object
    #simIf.set_viewer()

    # This kicks it off
    simIf.start_session()

    #This starts a small test program that sends packets. Sending packets
    # triggers the Recv Event
    testerPopen = subprocess.Popen(['./testIface.py'])

    while True:
        try:
            simIf.wait_for_hs_packet(10)
        except KeyboardInterrupt:
            print "exiting"
            testerPopen.kill()
            simIf.terminate_session()
            sys.exit()

if __name__ == '__main__':
    main() 

