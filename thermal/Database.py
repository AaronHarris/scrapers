#! /usr/bin/python
from robot.api import logger
import unittest
import random
import string
import sqlite3 as sqlite
from Utils import sanitizeString
import collections

def dictValuePad(key):
    return '%(\"' + str(key) + '\")'

def insertFromDict(table, dict):
    """Take dictionary object dict and produce sql for 
    inserting it into the named table"""
    sql = 'INSERT INTO ' + table
    sql += ' ('
    sql += ', '.join(dict)
    sql += ') VALUES ('
    sql += ', '.join(map(dictValuePad, dict))
    sql += ');'
    return sql

Cond = collections.namedtuple('Cond','arg1 operator arg2')

class Database:
    """
    Sqlite3 database interface using pysqlite
    Author: Phillip Marks <phillip.marks@jpl.nasa.gov>

    This class encapsulates an sqlite3 database interface by providing functions to create, 
    insert, select, dump, drop, and execute other statements on a database. Except for 
    execute, each method abstacts the database interface and instead uses dictionarys, 
    tuples, or other python objects as the interface. Methods that access the database raise 
    RuntimeError if the database or resource within the database are not available.

    More information about sqlite3 and python <http://docs.python.org/2/library/sqlite3.html>
    
    Simple usage:
        
        import Database

        exampleDatabase = Database("DatabaseFileName")
        exampleDatabase.load_schema()
        exampleDatabase.create_database()

        aDict = {'column1:42','column2:42'}
        exampleDatabase.insert_from_dict(aDict)

        columnToGet = 'column1'
        cond = Cond('column', '<=', '42')
        foo = exampleDatabase.select(columnToGet,select)

    Copyright 2013, by the California Institute of Technology.  ALL RIGHTS
    RESERVED.  United States Government Sponsorship acknowledged.  Any
    commercial use must be negotiated with the Office of Technology Transfer
    at the California Institute of Technology.
    
    This software may be subject to U.S. export control laws.  By accepting
    this software, the user agrees to comply with all applicable U.S. export
    laws and regulations.  User has the responsibility to obtain export 
    licenses, or other export authority as may be required before exporting
    such information to foreign countries or providing access to foreign
    persons.
    
    """

    schema = {}
    dbFilename = "robotSCATdb.db"
    con = None
    tableName = ""

    def __init__(self,filename=None):
        """
        Set database filename if provided
        """
        if filename:
            self.dbFilename = filename

    def load_schema(self,filename):
        """
        Load a schema from a text file.

        Can be sub-classed to load a schema from other formats such as XML.

        Text schema format:

            TABLE_NAME
            COLUMN_NAME SQLITE_TYPE
            COLUMN_NAME SQLITE_TYE
            ....

        Raises RuntimeError if there is an issue reading the file
        """
        logger.info("Loading schema from file %s" % filename)
        try:
            schemaFile =  open(filename)

            self.tableName =  schemaFile.readline().strip('\n')
            for line in schemaFile:
                line = line.strip('\n')
                columnName,type = line.split(' ')
                self.schema.update({columnName:type})

            schemaFile.close()
        except IOError,e:
             raise RuntimeError("Error reading schema! error %s file %s" \
                    % (e.args[0],filename))
    
    def set_db(self,filename):
        """
        Set database filename
        """

        self.dbFilename = filename

    def open_db(self):
        """
        Connect to database and raise RuntimeError if sqlite gives an error
        """
        if self.con is None:
            try:
                self.con = sqlite.connect(self.dbFilename, check_same_thread=False)
            except sqlite.Error, e:
                raise RuntimeError("Error opening database!: error: %s"  % e.args[0])
            self.con.row_factory = sqlite.Row
            self.con.text_factory = str

    def get_cursor(self):
        """
        Return the cursor if the database connection is open
        """
        if self.con:
            try:
                cur = self.con.cursor()
            except sqlite.Error, e:
                raise RuntimeError("Error obtaining cursor!: error: %s"  % e.args[0])

            return cur
        else:
            return None
    
    def close_db(self):
        """
        Close an open database connection.

        Closing a connection doesn't commit any transactions!
        """
        if self.con:
            try:
                self.con.close()
            except sqlite.Error,e:
                raise RuntimeError("Error closing database!: error: %s" % e.args[0])
            self.con = None
    
    def commit_db(self):
        """
        Commit on an open connection. Raises RuntimeError for any sqlite error
        """
        if self.con:
            try:
                self.con.commit()
            except sqlite.Error, e:
                raise RuntimeError("Error commiting to database!: error: %s"  % e.args[0])

    def execute(self,statements,parameters=None,commit=True):
        """
        Open and perform the list of sqlite statements in statements on the databases.

        If optional argument commit is provided commit after all statements have 
        been executed. Raises RuntimeError on an sqlite error

        Returns a list of any values that are a result of the statement
        """
        ret = None
        try:
            self.open_db()
            cur = self.get_cursor()
            if isinstance(statements, (list, tuple)):
                ret = []
                for aStatement in statements:
                    cur.execute(aStatement)
                    ret.append(cur.fetchall())
            else:
                ret = None
                if parameters:
                    cur.execute(statements,parameters)
                else:
                    cur.execute(statements)
                ret = cur.fetchall()
            if commit==True:
                self.commit_db()
        except sqlite.Error, e:
            print "Error in statement %s: %s" % (statements,e.args[0])
            raise RuntimeError("Error executing sqlite statement!: error %s statements %s" \
                    % (e.args[0],statements))
        finally:
            return ret
         
    def create_table(self):
        """
        Create the database if it doesn't not exists using the dictionary in self.schema

        Raises RuntimeError if schema hasn't been loaded
        """
        logger.debug("Creating database")
        if self.schema is None:
            raise RuntimeError("No schema loaded! Can't create table!")
        
        dbCreateStr = "CREATE TABLE IF NOT EXISTS "
        dbCreateStr+= self.tableName + "("
        for colName in self.schema.keys():
            type = self.schema[colName]
            sanitizedColName = sanitizeString(colName)
            dbCreateStr+= "%s %s," % (sanitizedColName, type)
       
        dbCreateStr = dbCreateStr[:-1]
        dbCreateStr+= ")"

        self.execute(dbCreateStr)

    def drop_table(self,tableName=None):
        """
        Drop the table tableName

        If the optional argument name is not given use the tableName set by 
        load_schema.
        """
        if tableName is None:
            tableName = self.tableName
        self.execute("DROP TABLE IF EXISTS " + tableName)

    def list_tables(self):
        """
        List all tables in the database file.

        This can include tables not created by the particular instance of Database
        that this method is called on
        """
        tableList = []
        rawList=self.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for table in rawList:
            tableList.append(table[0])
        logger.debug("List of tables " + ", ".join(map(str, tableList)))
        return tableList

    def is_valid_table(self,table):
        """
        Return True if table in the list of tables in the database

        Table does not need to be a table created by the instance of this class
        """
        tables = self.list_tables()
        return table in tables

    def dump_table(self,name=None):
        """
        Dump all the values in a table as list of dictionaries for each row

        If the optional argument name is not given uses the tableName set by 
        load_schema.
        """
        if name is None:
            name = self.tableName
        table = self.execute("SELECT * FROM %s" % name)
        return table

    def dump_table_info(self,name=None):
        """
        Dump all the columns in a table as list of tuples

        If the optional argument name is not given uses the tableName set by 
        load_schema.
        """
        if name is None:
            name = self.tableName
        table = self.execute("PRAGMA TABLE_INFO(%s)" % name)
        return table

    def insert(self,dict,name=None):
        """
        Insert the dictionary of columns to value into the database

        If the optional argument name is not given uses the tableName set by 
        load_schema.
        """
        if name is None:
            name = self.tableName

        columnNames = [sanitizeString(x) for x in dict.keys()]
        values = [sanitizeString(x) if isinstance(x,str) else x for x in dict.values()]

        columns = ', '.join(columnNames)
        placeholders = ', '.join(['?'] * len(dict))
        insertStr = 'INSERT INTO %s ' % name
        insertStr += '(%s) VALUES ( %s )' % (columns,placeholders) 
        self.execute(insertStr,values)

    def select(self,cols,cond=None,name=None):
        """
        Select an item or set of items from the database 

        The optional parameter cond is a named tuple consisiting of two as arguments
        as strings and a comparison operator to perform on them. if cond is passed in
        the named tuple's strings are sanitized and it's turned into a conditional 
        string to use with "WHERE". See below for a list of 
        valid comparison operators:

        if cond is not given then all of the rows of each column in cols are returned

        http://www.sqlite.org/lang_expr.html#binaryops

        If the optional argument name is not given, uses the tableName set by 
        load_schema.
        """
        if name is None:
            name = self.tableName

        colNames = [sanitizeString(x) for x in cols]
        
        selectStr = "SELECT " + ','.join(colNames) + " "
        selectStr += "from " + name + " "

        if cond:
            operand1 = sanitizeString(cond.arg1)
            operand2 = cond.arg2
            if not operand2.isdigit():
                operand2 = sanitizeString(operand2)
                operand2 = "\"" + operand2 + "\""
            op = cond.operator

            selectStr += "where " 
            selectStr += operand1
            selectStr += op
            selectStr += operand2
        return self.execute(selectStr)

    def select_from_last_row(self,cols,name=None):
        """
        Select an item or set of items from the last row in the table

        If the optional argument name is not given, uses the tableName set by 
        load_schema.
        """
        if name is None:
            name = self.tableName

        colNames = [sanitizeString(x) for x in cols]
        
        # In order to support somewhat multi-threaded support get the last
        # row using MAX(rowid) instead of last_insert_rowid()
        lastInsertRow = self.execute("SELECT MAX(rowid) from " + name)[0][0]
        selectStr = "SELECT " + ','.join(colNames) + " "
        selectStr += "from " + name + " "
        selectStr += "WHERE rowid="+ str(lastInsertRow)

        return self.execute(selectStr)

class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.sut = Database(":memory:")

    def test_load_schema(self):
        self.sut.load_schema("test/foo.txt")
        assert('cmdTable' == self.sut.tableName)
        assert('INT' == self.sut.schema['opcode'])
    
    def test_create_table(self):
        self.sut.load_schema("test/foo.txt")
        self.sut.create_table()
        self.assertNotEqual(self.sut.list_tables(),[])

    def test_drop_table(self):
        self.sut.load_schema("test/foo.txt")
        self.sut.create_table()

        self.sut.drop_table("cmdTable")
        self.assertEqual(self.sut.list_tables(),[])

    def test_list_tables(self):
        self.sut.load_schema("test/foo.txt")
        self.sut.create_table()
        tables=self.sut.list_tables()
        self.assertEqual(tables,['cmdTable'])

    def test_is_valid_table(self):
        self.sut.load_schema("test/foo.txt")
        self.sut.create_table()
        ret=self.sut.is_valid_table("foo")
        self.assertFalse(ret)
        ret=self.sut.is_valid_table("cmdTable")
        self.assertTrue(ret)

    def test_insert(self):
        dict = {"opcode":42,"opcodeString":"42","name":"Slartibartfast",
                "ccn":"World%Builder&","length":67, "numparams":45,"params":"foo"}

        self.sut.load_schema("test/foo.txt")
        self.sut.create_table()

        self.sut.insert(dict)
        
        assert(self.sut.dump_table()[0]['opcode'] == 42)

    def test_select(self):
        dict = {"opcode":42,"opcodeString":"42","name":"Slartibartfast",
                "ccn":"World%Builder&","length":67, "numparams":45,"params":"foo"}

        self.sut.load_schema("test/foo.txt")
        self.sut.create_table()

        self.sut.insert(dict)
        
        ret = self.sut.select(('length',))
        print ret[0][0]
        assert(ret[0][0] == 67)

        ret = self.sut.select(('length', 'numparams'))
        print ret[0]
        assert(ret[0][0] == 67)
        assert(ret[0][1] == 45)

        cond = Cond('opcode', '=', '42')
        ret = self.sut.select(('length',), cond)
        print ret[0][0]
        assert(ret[0][0] == 67)

        cond = Cond('ccn', '=', 'World%Builder&')
        ret = self.sut.select(('params',), cond)
        print ret[0][0]
        assert(ret[0][0] == 'foo')

if __name__ == '__main__':
    unittest.main() 
