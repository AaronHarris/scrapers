import urllib2

for i in range(500):
	r = urllib2.urlopen('http://web-app.usc.edu/ws/eo2/json/%s/list' % i).read()
	if r != "[]\n":
		print i

cals = [8,13,32,47,57,63,69,73,81,92,103,105,106,109,113,127,145,173,207,209,220,222,225,230,231,234,241,242,243,246,247,249,250,254,259]
http://web-app.usc.edu/ws/eo2/calendars