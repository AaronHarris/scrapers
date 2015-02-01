import json, os

namesjson = []
with open("names.json") as json_file:
    json_data = json.load(json_file)
    print(json_data)
    namesjson = json_data

def jsonToTitles(json):
    var outarr = []
    for level in json:
        var name = level.title
        if len(level.sublevels) > 1:
            for i, sublevel in enumerate(level.sublevels):
                str = name[0]+"."+(i+1)+name.substring[3:]
                str += " - " + sublevel
                str += ".mp4"
                outarr.append(str)
        else:
            outarr.append(name + ".mp4")
    return outarr

names = jsonToTitles(namesjson)
oldnames = [x for x in sorted(os.listdir('.')) if x not in set([".","..","names.json"])]

from pprint import pprint; pprint(zip(oldnames,names))

pause = raw_input("Press any key to continue")

for oldname, newname in zip(oldnames, names):
    os.rename(oldname, newname)

