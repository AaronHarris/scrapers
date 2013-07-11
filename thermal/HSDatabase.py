#! /usr/bin/python
from robot.api import logger
import unittest
import sqlite3 as sqlite
import xlrd
import base64
import struct
import time
import sys
import random
import collections
import pickle
import os
from Utils import *
from Database import *

HSFieldInfo = collections.namedtuple('HSFieldInfo','name type offsetBit sizeInBits')

class HSDatabase(Database):
    tableName = "hsTable"
    offsetTableName = "offsetTable"
    hsFieldInfoDict = {}
    hsFieldInfoFilename = "hsFieldInfo.pkl"

    def load_schema(self,filename,sheet,force=False,rowsToSkip=3):
        if not os.path.isfile(self.hsFieldInfoFilename) or force:
            logger.info("Creating HS databasefrom %s: sheet %s" % (filename, sheet))
            self.load_schema_from_dict(filename,sheet,rowsToSkip)
        else:
            logger.info("Loading HS from %s " % (self.hsFieldInfoFilename))
            self.unpickle_fields_dict()

    def load_schema_from_dict(self,filename,sheet,rowsToSkip=3):
        """
        Load the HS database schema from the sheet "sheet" in the spreadsheet "filename"

        Optional argument rowsToSkip is a number rows to skip processing on the sheet
        In addition to creating the schema this function also creates an array of 
        named tuples that contain metadata about the size and offset of fields 
        (db columns) in a bytearray packet
        """
        
        nameColIndex = 4; typeColIndex = 8; sizeColIdx = 9; offsetColIdx=20
        
        self.schema.update({'epochTimestamp':'REAL'})
        self.schema.update({'seqNum':'INT'})

        workBook = xlrd.open_workbook(filename,on_demand=True)
        hsDict = workBook.sheet_by_name(sheet)
        for rowIndex, row in enumerate(hsDict.col(nameColIndex)):
            validRow = rowIndex > rowsToSkip+1 and row.value
            if not validRow:
                continue

            name = row.value
            dictType = hsDict.cell(rowIndex,typeColIndex).value
            size = int(hsDict.cell(rowIndex,sizeColIdx).value)
            octetOffset = int(hsDict.cell(rowIndex,offsetColIdx).value) - 1
            octetStartBit = int(hsDict.cell(rowIndex,offsetColIdx+1).value)
            offsetBit = (octetOffset * 2)*8 + octetStartBit
            
            if dictType == "SUND":
                dbType = 'BLOB'
                size = size*8
            elif dictType == "TISS":
                dbType = 'INT'
            else:
                dbType = 'INT'
            
            fieldInfo = HSFieldInfo(name,dbType,offsetBit,size)
            self.hsFieldInfoDict.update({name:fieldInfo})
            self.schema.update({name:dbType})
        
        self.pickle_fields_dict()        
        workBook.release_resources()
        logger.info("HS database created")

    def unpickle_fields_dict(self):
        hsFieldInfoFile = open(self.hsFieldInfoFilename,'r')
        self.hsFieldInfoDict = pickle.load(hsFieldInfoFile)
        hsFieldInfoFile.close()
    
    def pickle_fields_dict(self):
        hsFieldInfoFile = open(self.hsFieldInfoFilename,'w')
        pickle.dump(self.hsFieldInfoDict,hsFieldInfoFile)
        hsFieldInfoFile.close()
    
    def insert_packet(self,epochTimestamp,seqNum,buf):
        insertDict = {}

        insertDict.update({"epochTimestamp":epochTimestamp})
        insertDict.update({"seqNum":seqNum})

        for fieldInfo in self.hsFieldInfoDict.values():
            offset = fieldInfo.offsetBit
            size = fieldInfo.sizeInBits
            name = fieldInfo.name
            type = fieldInfo.type
            if type == 'BLOB':
                offset = offset/8
                size = size/8
                data = buffer(buf[offset:size+offset])
            else:
                data = unpack_from_bytearray(buf,size,offset)
            
            insertDict.update({name:data})

        Database.insert(self,insertDict)

    def read_hs_field(self,name,seqNum=None):
        if seqNum:
            cond = Cond('seqNum', '=', str(seqNum))
            ret = self.select((name,),cond)
        else:
            ret = self.select_from_last_row((name,))
        if ret is None:
            raise RuntimeError("Field %s not in database!" % name)
        elif not ret:
            raise RuntimeError("No data at field %s" % name)
        else:
            return ret[0][0]

    def get_hs_field_names(self):
        return self.hsFieldInfoDict.keys()

    def gen_fake_hs_packet(self,epochTime,fieldsToInsert=[]):
        timeFieldLen = 40
        buf = bytearray()
        buf = zero_pad(375*2)
        ISSTimeCoarse,ISSTimeFine = convert_time_to_ISS(epochTime, leapSecs=0, 
                            gpsEpochStart=( 1970,1,1,0,0,0,3,6,-1))        
        
        fieldNames=[aField[0] for aField in fieldsToInsert]

        for fieldInfo in self.hsFieldInfoDict.values():
            offset = fieldInfo.offsetBit
            size = fieldInfo.sizeInBits
            name = fieldInfo.name
            if size==timeFieldLen:
                buf=pack_into_bytearray(buf,ISSTimeCoarse,32,offset)
                buf=pack_into_bytearray(buf,ISSTimeFine,8,offset+32)
            elif name in fieldNames:
                fieldIndex = fieldNames.index(name)
                data = fieldsToInsert[fieldIndex][1]
                buf=pack_into_bytearray(buf,data,size,offset)
            else:
                buf=pack_into_bytearray(buf,1,size,offset)
        return buf

class TestHSDatabase(unittest.TestCase):

    def setUp(self):
        self.sutHS = HSDatabase(":memory:")
        self.sutHS.drop_table()
        self.sutHS.load_schema("test/testDict.xlsx","A3_A4_A23")
        self.sutHS.create_table()

    def test_load_schema(self):
        self.sutHS.close_db()

    def test_get_hs_field_names(self):
        ret=self.sutHS.get_hs_field_names()
        print ret
        assert("A2D Timeout" in ret)

    def test_insert_and_get(self):

        #for row in self.sutHS.dump_table_info():
        #   print row

        for i in range(10):
            # UTC time since Epoch
            currTime = time.time() 
            fieldsToInsert = (("Commands received",2+i),("Valid Command Count",1+i))
            buf=self.sutHS.gen_fake_hs_packet(currTime,fieldsToInsert)
            self.sutHS.insert_packet(currTime,i,buf)

        ret = self.sutHS.read_hs_field("Commands received",1)
        print ret
        assert(3==ret)
        
        ret = self.sutHS.read_hs_field("Valid Command Count",1)
        print ret
        assert(2==ret)

        ret=self.sutHS.read_hs_field("Commands received",2)
        print ret
        assert(4==ret)

        ret=self.sutHS.read_hs_field("Valid Command Count",2)
        print ret
        assert(3==ret)

        ret = self.sutHS.read_hs_field("Spacecraft time")
        ret = bytearray(ret)
        ret =  unpack_ISS_time(ret)
        print ret[0], ret[1]        
        ISSTimeCoarse,ISSTimeFine = convert_time_to_ISS(currTime)
        print ISSTimeCoarse,ISSTimeFine
        assert(ret[1]==ISSTimeCoarse)
        assert(ret[0]==ISSTimeFine)

        ret = self.sutHS.read_hs_field("Relay Status Group A - K13 SES On/Off PB-4",1)
        print ret
        assert(ret == 1)


if __name__ == '__main__':
    unittest.main() 


