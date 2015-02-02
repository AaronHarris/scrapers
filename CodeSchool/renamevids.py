import json, os, ast
from pprint import pprint

namesjson = []
with open("names.json") as json_file:
    json_data = json.load(json_file,'utf-8')
    namesjson = ast.literal_eval(json.dumps(json_data))

def jsonToTitles(json):
    outarr = []
    for level in json:
        name = level['title']
        if len(level['sublevels']) > 1:
            for i, sublevel in enumerate(level['sublevels']):
                title = "%s.%d%s - %s.mp4" % (name[0], i+1,name[3:],sublevel)
                outarr.append(escapename(title))
        elif level['sublevels'][0] == 'Part 1':
            outarr.append(escapename(name+".mp4"))
        else:
            title = "%s - %s.mp4" % (name,level['sublevels'][0])
            outarr.append(escapename(title))
        
    return outarr

def escapename(text):
    return text.replace('/','&').replace(':','-').replace('?','!').replace('<','(').replace('>',')').replace('*','^')

names = jsonToTitles(namesjson)
oldnames = [x for x in sorted(os.listdir('.')) if x not in set([".","..","names.json"])]
if len(names) != len(oldnames):
    print "[WARNING]: Unequal names list detected"

pprint(zip(oldnames,names))

pause = raw_input("Press any key to continue")

for oldname, newname in zip(oldnames, names):
    os.rename(oldname, newname)

