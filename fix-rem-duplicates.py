import fileinput

lastline = "\n"
import pdb; pdb.set_trace()
for line in fileinput.input(inplace=1):
	if not lastline == "\n" and not line == "\n":
		print(line[2:]),
	else:
		print(line),
	lastline = line