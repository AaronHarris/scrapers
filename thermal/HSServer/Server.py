import sys
import time
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
# from HSDatabase import *


HOST_NAME = 'localhost'
PORT_NUMBER = 8189

class Server(BaseHTTPServer.BaseHTTPRequestHandler):

	def do_HEAD(s):
		s.send_response(200)
		s.send_header("Content-type", "text/html")
		s.end_headers()
	def do_GET(s):
		s.send_response(200)
		s.send_header("Content-type", "text/html")
		s.end_headers()
		fin = open('gui.html')
		for line in fin:
			s.wfile.write(line) 
		s.wfile.write("<p>Value: %s</p>" % "hello")
		s.wfile.write("</html>")

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), Server)
    print time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER)

class BASE(HSDatabase)
	def __init__(self, dbFilename=":memory:", hsRecvEvent):
		HSDatabase.__init__(self)
		self.event = hsRecvEvent
		self.sutHS = HSDatabase(dbFilename)
		# event.isSet()
		
        self.sutHS.drop_table()
        self.sutHS.load_schema("test/testDict.xlsx","A3_A4_A23")
        self.sutHS.create_table()

	def run():
		event.wait(5000)
		head_hs_field(field_name)
		

		if self._stop.isSet():
			raise


		