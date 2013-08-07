import time
import urllib2

def gmail_response(name):
	return urllib2.urlopen('http://www.google.com/accounts/CheckAvailability?Email=%s' % name).read()

def gmail_available(name):
	if not 6 <= len(name) <= 30:
		raise "Invalid name. Must be between 6 and 30 characters"
	r = urllib2.urlopen('http://www.google.com/accounts/CheckAvailability?Email=%s' % name).read()
	if r.rfind("is available") > -1:
		return True
	elif r.find("Sorry, we are unable to present username suggestions at this time.") > -1:
		return None
	else:
		return False

def whether(name):
	return gmail_available(name)
