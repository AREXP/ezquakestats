#!/usr/bin/python
import pdb
import time, sys
from datetime import timedelta, date, datetime
import time
import re
import subprocess
from operator import itemgetter, attrgetter, methodcaller

from optparse import OptionParser,OptionValueError

import fileinput
import os.path

import ezstatslib
from ezstatslib import Team,Player
from ezstatslib import enum,checkNew,htmlLink
from ezstatslib import NEW_GIF_TAG as newGifTag

import HTML

import random

# TODO use ezstatslib.readLineWithCheck
# TODO skip lines separate log
# TODO make index file

COMMAND_LOG_LOCAL_SMALL_DELIM = "__________";
COMMAND_LOG_LOCAL_BIG_DELIM   = "___________________________________";

COMMAND_LOG_NET_SMALL_DELIM   = "(========)";
COMMAND_LOG_NET_BIG_DELIM     = "(=================================)";

teammateTelefrags = [] # array of names who was telegragged by teammates

def fillH2H(who,whom):
    try:
        for elem in headToHead[who]:
            if elem[0] == whom:
                elem[1] += 1
    except Exception, ex:
        ezstatslib.logError("fillH2H: who=%s, whom=%s, ex=%s\n" % (who, whom, ex))

plPrevFragsDict = {}

def getFragsLine(players):
    playersByFrags = sorted(players, key=methodcaller("frags"), reverse=True)
    s = "[%s]" % (players1[0].teamname)
    
    fragsSum = 0
    for pl in playersByFrags:
        fragsSum += pl.frags()
    s += " {0:3d}: ".format(fragsSum)

    for pl in playersByFrags:        
        if not pl.name in plPrevFragsDict.keys():
            plFragsDelta = pl.frags()
        else:
            plFragsDelta = pl.frags() - plPrevFragsDict[pl.name]        
        plPrevFragsDict[pl.name] = pl.frags()

        if plFragsDelta == 0:
            deltaStr = "<sup>0  </sup>"
        else:
            if plFragsDelta > 0:
                deltaStr = "<sup>+%d%s</sup>" % (plFragsDelta, " " if plFragsDelta < 10 else "")
            else:
                deltaStr = "<sup>%d%s</sup>"  % (plFragsDelta, " " if plFragsDelta < 10 else "")
                
        s += ( "{0:%ds}" % (20+len(deltaStr)) ).format(pl.name + "(" + str(pl.frags()) + ")" + deltaStr)
    s = s[:-1]
    
    return s

def fillExtendedBattleProgress():
    s = getFragsLine(players1)
    s += " vs. "
    s += getFragsLine(players2)
    extendedProgressStr.append(s)

usageString = "" 
versionString = ""
parser = OptionParser(usage=usageString, version=versionString)

parser.add_option("-f",        action="store",       dest="inputFile",      type="str",  metavar="LOG_FILE", help="")
parser.add_option("--net-log", action="store_true",  dest="netLog",         default=False,                   help="")
parser.add_option("--scripts", action="store_false",   dest="withScripts", default=True,   help="")

(options, restargs) = parser.parse_args()

# check rest arguments
if len(restargs) != 0:
    parser.error("incorrect parameters count(%d)" % (len(restargs)))
    exit(0)

if options.inputFile:
    f = fileinput.input(options.inputFile)
else:
    f = sys.stdin

matchdate = ""
matchlog = []
isStart = False
isEnd = False

teamNames = []
matchProgressDict = []
matchProgressPlayers1Dict = []
matchProgressPlayers2Dict = []

matchProgressDictEx = []
matchProgressPlayers1DictEx = []
matchProgressPlayers2DictEx = []

matchProgressDictEx2 = []

players1 = []
players2 = []
allplayers = []
disconnectedplayers = []

smallDelimiter = COMMAND_LOG_NET_SMALL_DELIM if options.netLog else COMMAND_LOG_LOCAL_SMALL_DELIM;
bigDelimiter   = COMMAND_LOG_NET_BIG_DELIM   if options.netLog else COMMAND_LOG_LOCAL_BIG_DELIM;

line = f.readline() 
#while not "matchdate" in line:
#    line = f.readline()
#matchdate = line.split("matchdate: ")[1].split("\n")[0]


while not ezstatslib.isMatchStart(line):
    if "telefrag" in line and not "teammate" in line: # telefrags before match start
        matchlog.append(line)
        
    if "matchdate" in line:
        if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:
            matchStartStamp = int( line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[0] )
            line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
            
        matchdate = line.split("matchdate: ")[1].split("\n")[0]            

    line = f.readline()

line = f.readline()

matchMinutesCnt = 1
while not ezstatslib.isMatchEnd(line):
    matchlog.append(line)
    line = f.readline()
    
    if "remaining" in line or "overtime" in line:  # [9] minutes remaining
        matchMinutesCnt += 1
    
# team 1
while not "Team [" in line:
    line = f.readline()
teamName1 = line.split('[')[1].split(']')[0]


line = f.readline()
while not "Team [" in line:
    while not smallDelimiter in line:
        line = f.readline()

        if "Team [" in line:
            break

    if "Team [" in line:
        break

    line = f.readline()
    
    if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:
        line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
    
    playerName = line.split(' ')[1].split(':')[0]
    
    if playerName[0] == "_" or playerName[0] == "#":
        playerName = playerName[1:]
        disconnectedplayers.append(playerName)

    line = f.readline()
    if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:
        line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]

    #"  24 (-25) 10 32.9%"
    stats = line.split(' ')
    pl = Player( teamName1, playerName, int(stats[2]), int( stats[3].split('(')[1].split(')')[0]), int(stats[4]) )
    pl.initPowerUpsByMinutes(matchMinutesCnt)
    
    line = f.readline() # Wp: rl52.1% sg12.2%
    pl.parseWeapons(line)

    line = f.readline() # RL skill: ad:82.2 dh:25
    pl.rlskill_ad = float(line.split("ad:")[1].split(" ")[0])
    pl.rlskill_dh = float(line.split("dh:")[1].split(" ")[0])

    line = f.readline() # Armr&mhs: ga:0 ya:4 ra:1 mh:1
    pl.ga = int(line.split("ga:")[1].split(" ")[0])
    pl.ya = int(line.split("ya:")[1].split(" ")[0])
    pl.ra = int(line.split("ra:")[1].split(" ")[0])
    pl.mh = int(line.split("mh:")[1].split(" ")[0])

    line = f.readline() # Powerups: Q:0 P:0 R:0
    line = f.readline() # RL: Took:30 Killed:15 Dropped:28

    line = f.readline() # Damage: Tkn:4279 Gvn:4217 Tm:284
    pl.tkn = int(line.split("Tkn:")[1].split(" ")[0])
    pl.gvn = int(line.split("Gvn:")[1].split(" ")[0])
    pl.tm  = int(line.split("Tm:")[1].split(" ")[0])

    line = f.readline() # Streaks: Frags:3 QuadRun:0
    pl.streaks = int(line.split("Streaks: Frags:")[1].split(" ")[0])

    line = f.readline() # SpawnFrags: 4
    pl.spawnfrags = int(line.split("SpawnFrags: ")[1].split(" ")[0])

    players1.append(pl)
    allplayers.append(pl)

    line = f.readline()


# team 2
#while not "Team [" in line:
#    line = f.readline()
teamName2 = line.split('[')[1].split(']')[0]


line = f.readline()
while not bigDelimiter in line:
    while not smallDelimiter in line:
        line = f.readline()

        if bigDelimiter in line:
            break

    if bigDelimiter in line:
        break

    line = f.readline()
    if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:
        line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
    
    playerName = line.split(' ')[1].split(':')[0]

    if playerName[0] == "_" or playerName[0] == "#":
        playerName = playerName[1:]
        disconnectedplayers.append(playerName)

    line = f.readline()
    if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:
        line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]

    #"  24 (-25) 10 32.9%"
    stats = line.split(' ')
    pl = Player( teamName2, playerName, int(stats[2]), int( stats[3].split('(')[1].split(')')[0]), int(stats[4]) )
    pl.initPowerUpsByMinutes(matchMinutesCnt)
    
    line = f.readline() # Wp: rl52.1% sg12.2%
    pl.parseWeapons(line)

    line = f.readline() # RL skill: ad:82.2 dh:25
    pl.rlskill_ad = float(line.split("ad:")[1].split(" ")[0])
    pl.rlskill_dh = float(line.split("dh:")[1].split(" ")[0])

    line = f.readline() # Armr&mhs: ga:0 ya:4 ra:1 mh:1
    pl.ga = int(line.split("ga:")[1].split(" ")[0])
    pl.ya = int(line.split("ya:")[1].split(" ")[0])
    pl.ra = int(line.split("ra:")[1].split(" ")[0])
    pl.mh = int(line.split("mh:")[1].split(" ")[0])

    line = f.readline() # Powerups: Q:0 P:0 R:0
    line = f.readline() # RL: Took:30 Killed:15 Dropped:28

    line = f.readline() # Damage: Tkn:4279 Gvn:4217 Tm:284
    pl.tkn = int(line.split("Tkn:")[1].split(" ")[0])
    pl.gvn = int(line.split("Gvn:")[1].split(" ")[0])
    pl.tm  = int(line.split("Tm:")[1].split(" ")[0])

    line = f.readline() # Streaks: Frags:3 QuadRun:0
    pl.streaks = int(line.split("Streaks: Frags:")[1].split(" ")[0])

    line = f.readline() # SpawnFrags: 4
    pl.spawnfrags = int(line.split("SpawnFrags: ")[1].split(" ")[0])

    players2.append(pl)
    allplayers.append(pl)

    line = f.readline()

# teams stats parse
while not "weapons, powerups, armors&mhs, damage" in line:
    line = f.readline()
line = f.readline()
line = f.readline() # [xep]: Wp: rl41 gl5 sg14% ssg14%
teamName = line.split("]")[0].split("[")[1]

team1 = Team(teamName)
line = f.readline() # Powerups: Q:0 P:0 R:0

line = f.readline() # Armr&mhs: ga:0 ya:24 ra:13 mh:13
team1.ga = int(line.split("ga:")[1].split(" ")[0])
team1.ya = int(line.split("ya:")[1].split(" ")[0])
team1.ra = int(line.split("ra:")[1].split(" ")[0])
team1.mh = int(line.split("mh:")[1].split(" ")[0])

line = f.readline() # RL: Took:93 Killed:66 Dropped:88

line = f.readline() # Damage: Tkn:15750 Gvn:15831 Tm:1916
team1.tkn = int(line.split("Tkn:")[1].split(" ")[0])
team1.gvn = int(line.split("Gvn:")[1].split(" ")[0])
team1.tm  = int(line.split("Tm:")[1].split(" ")[0])

line = f.readline() # [xep]: Wp: rl41 gl5 sg14% ssg14%
teamName = line.split("]")[0].split("[")[1]
team2 = Team(teamName)
line = f.readline() # Powerups: Q:0 P:0 R:0

line = f.readline() # Armr&mhs: ga:0 ya:24 ra:13 mh:13
team2.ga = int(line.split("ga:")[1].split(" ")[0])
team2.ya = int(line.split("ya:")[1].split(" ")[0])
team2.ra = int(line.split("ra:")[1].split(" ")[0])
team2.mh = int(line.split("mh:")[1].split(" ")[0])

line = f.readline() # RL: Took:93 Killed:66 Dropped:88

line = f.readline() # Damage: Tkn:15750 Gvn:15831 Tm:1916
team2.tkn = int(line.split("Tkn:")[1].split(" ")[0])
team2.gvn = int(line.split("Gvn:")[1].split(" ")[0])
team2.tm  = int(line.split("Tm:")[1].split(" ")[0])

mapName = ""
# map name
while not "top scorers" in line:
    line = f.readline()
    
if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:
    line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
    
mapName = line.split(" ")[0]


# total score
totalScore = []
while not "Team scores" in line:
    line = f.readline()
line = f.readline()
line = f.readline()

if not ezstatslib.LOG_TIMESTAMP_DELIMITER in line:  # TODO incorrect dates in netlog 
    if "+" in line and "=" in line:
        totalScore.append( [line.split(":")[0].split("[")[1].split("]")[0], int(line.split("= ")[1].split(" ")[0])] )
    else:
        totalScore.append( [line.split(":")[0].split("[")[1].split("]")[0], int(line.split(" ")[1])] )
    
    line = f.readline()
    
    if "+" in line and "=" in line:
        totalScore.append( [line.split(":")[0].split("[")[1].split("]")[0], int(line.split("= ")[1].split(" ")[0])] )
    else:
        totalScore.append( [line.split(":")[0].split("[")[1].split("]")[0], int(line.split(" ")[1])] )

f.close()

# head-to-head stats init
headToHead = {}
for pl1 in allplayers:
    headToHead[pl1.name] = []
    for pl2 in allplayers:
        # if pl1.name != pl2.name and pl1.teamname != pl2.teamname:
        headToHead[pl1.name].append([pl2.name,0])

progressStr = []
extendedProgressStr = []
isProgressLine = False
currentMatchTime = 0
battleProgressExtendedNextPoint = (int)(60 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
for logline in matchlog:
    if logline == "":
        continue

    lineStamp = -1
    if ezstatslib.LOG_TIMESTAMP_DELIMITER in logline:
        lineStamp = int( logline.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[0] )
        logline = logline.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
        currentMatchTime = lineStamp - matchStartStamp

    # battle progress
    if "remaining" in logline:  # [9] minutes remaining
        isProgressLine = True
        continue

    isIntermediatePoint = (not isProgressLine) and (not "time over, the game is a draw" in logline) and (currentMatchTime > battleProgressExtendedNextPoint)

    if isProgressLine or isIntermediatePoint or "time over, the game is a draw" in logline: # Team [red] leads by 4 frags || tie || time over, the game is a draw
        # TODO replace with frags when teams stats are updated on each increment
        progressLineDict = {}
        
        fr1 = 0
        for pl in players1:
            fr1 += pl.frags()
        fr2 = 0
        for pl in players2:
            fr2 += pl.frags()        
        
        progressLineDict[team1.name] = fr1;  # team1.frags()
        progressLineDict[team2.name] = fr2; # team2.frags()
        if not isIntermediatePoint:
            matchProgressDict.append(progressLineDict)
        matchProgressDictEx.append(progressLineDict)
        
        players1ByFrags = sorted(players1, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
        playersProgressLineDict1 = {}
        for pl in players1ByFrags:
            playersProgressLineDict1[pl.name] = [pl.frags(), pl.calcDelta()];
        if not isIntermediatePoint:
            matchProgressPlayers1Dict.append(playersProgressLineDict1)
        matchProgressPlayers1DictEx.append(playersProgressLineDict1)
        
        players2ByFrags = sorted(players2, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
        playersProgressLineDict2 = {}
        for pl in players2ByFrags:
            playersProgressLineDict2[pl.name] = [pl.frags(), pl.calcDelta()];
        if not isIntermediatePoint:
            matchProgressPlayers2Dict.append(playersProgressLineDict2)
        matchProgressPlayers2DictEx.append(playersProgressLineDict2)

        battleProgressExtendedNextPoint += (int)(60 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        
        if not isIntermediatePoint:
            isProgressLine = False
        
            if "time over, the game is a draw" in logline:
                progressStr.append("tie (overtime)")
                fillExtendedBattleProgress()
                continue
            elif "tie" in logline:
                progressStr.append("tie")
                fillExtendedBattleProgress()
                continue
            else:
                if not "leads" in logline:
                    ezstatslib.logError("progress: \"%s\"\n" % (logline))
                    exit(0)                
                sp = logline.split(" ")
                progressStr.append("%s%s" % (sp[1], sp[4]))
                fillExtendedBattleProgress()
                continue
    
    if len(matchProgressDictEx2) == 0 or matchProgressDictEx2[len(matchProgressDictEx2)-1][team1.name][0] != currentMatchTime:
        progressLineDict = {}
        
        fr1 = 0
        for pl in players1:
            fr1 += pl.frags()
        fr2 = 0
        for pl in players2:
            fr2 += pl.frags()        
        
        progressLineDict[team1.name] = [currentMatchTime, fr1]; # team1.frags()
        progressLineDict[team2.name] = [currentMatchTime, fr2]; # team2.frags()        
        matchProgressDictEx2.append(progressLineDict)
    
    # teamkill
    checkres,who,whom = ezstatslib.teamkillDetection(logline)
    if checkres:
        isFoundWho = False
        isFoundWhom = False if whom != "" else True
        for pl in allplayers:
            if pl.name == who:
                pl.incTeamkill(currentMatchTime, who, whom)                
                isFoundWho = True

            if whom != "" and pl.name == whom:
                pl.incTeamdeath(currentMatchTime, who, whom)
                isFoundWhom = True
                
        if whom != "":
            fillH2H(who,whom)
                
        if not isFoundWho and not isFoundWhom:            
            ezstatslib.logError("count teamkills\n")
            exit(0)
        continue

    # telefrag
    teamcnt = len(teammateTelefrags)
    checkres,who,whom = ezstatslib.talefragDetection(logline, teammateTelefrags)
    if checkres:
        isFoundWho = False if who != "" else True
        isFoundWhom = False
        isTeammateFrag = (teamcnt != len(teammateTelefrags))
        for pl in allplayers:
            if who != "" and pl.name == who:
                if not isTeammateFrag:
                    pl.incKill(currentMatchTime, who, whom)
                else:
                    pl.incTeamkill(currentMatchTime, who, whom)
                    
                pl.tele_kills += 1
                isFoundWho = True
            
            if pl.name == whom:
                if not isTeammateFrag:
                    pl.incDeath(currentMatchTime, who, whom)
                else:
                    pl.incTeamdeath(currentMatchTime, who, whom)
                    
                pl.tele_deaths += 1
                isFoundWhom = True
                
        if who != "":
            fillH2H(who,whom)

        if not isFoundWho or not isFoundWhom:            
            ezstatslib.logError("count telefrag %s - %s: %s\n" % (who, whom, logline))
            exit(0)

        continue

    checkres,checkname = ezstatslib.suicideDetection(logline)
    if checkres:
        isFound = False
        for pl in allplayers:
            if pl.name == checkname:
                pl.incSuicides(currentMatchTime)
                fillH2H(checkname,checkname)
                isFound = True
                break;
        if not isFound:
            ezstatslib.logError("count suicides")
            exit(0)

        continue

    # power ups
    checkres,checkname,pwr = ezstatslib.powerupDetection(logline)
    if checkres:
        isFound = False
        for pl in allplayers:
            if pl.name == checkname:                    
                exec("pl.inc%s(%d,%d)" % (pwr, (currentMatchTime / 60), currentMatchTime))
                isFound = True
                break;
        if not isFound:
            ezstatslib.logError("ERROR: powerupDetection: no playername %s\n" % (checkname))
            exit(0)

        continue

    cres,who,whom,weap = ezstatslib.commonDetection(logline)
    if cres:
        if not weap in ezstatslib.possibleWeapons:
            ezstatslib.logError("unknown weapon: %s\n" % (weap))
            exit(0)

        isFoundWho = False
        isFoundWhom = False
        for pl in allplayers:
            if pl.name == who:
                pl.incKill(currentMatchTime, who, whom)
                exec("pl.%s_kills += 1" % (weap))
                isFoundWho = True
            
            if pl.name == whom:
                pl.incDeath(currentMatchTime, who, whom);
                exec("pl.%s_deaths += 1" % (weap))
                isFoundWhom = True
                
        fillH2H(who,whom)
        
        if not isFoundWho or not isFoundWhom:
            ezstatslib.logError("count common %s-%s: %s\n" % (who, whom, logline))
        
        continue
    

# validate score
fragsSum1 = 0
for pl in players1:
    fragsSum1 += pl.frags()

fragsSum2 = 0
for pl in players2:
    fragsSum2 += pl.frags()

if len(totalScore) != 0:
    if players1[0].teamname == totalScore[0][0]:
       if fragsSum1 != totalScore[0][1]:
            # print "WARNING: frags sum(%d) for team [%s] is NOT equal to score(%d)" % (fragsSum1, players1[0].teamname, totalScore[0][1])
            pass
       if fragsSum2 != totalScore[1][1]:
            # print "WARNING: frags sum(%d) for team [%s] is NOT equal to score(%d)" % (fragsSum2, players2[0].teamname, totalScore[1][1])
            pass
    else:
       if fragsSum2 != totalScore[0][1]:
            # print "WARNING: frags sum(%d) for team [%s] is NOT equal to score(%d)" % (fragsSum2, players1[0].teamname, totalScore[0][1])
            pass
       if fragsSum1 != totalScore[1][1]:
            # print "WARNING: frags sum(%d) for team [%s] is NOT equal to score(%d)" % (fragsSum1, players2[0].teamname, totalScore[1][1])
            pass
else:
    totalScore.append( [players1[0].teamname, fragsSum1] )
    totalScore.append( [players2[0].teamname, fragsSum2] )
    

# fill team kills/deaths/teamkills/suicides/teamdeaths/powerups/weapons
for pl in players1:
    team1.kills += pl.kills
    team1.deaths += pl.deaths
    team1.teamkills += pl.teamkills
    team1.suicides += pl.suicides
    team1.teamdeaths += pl.teamdeaths
    
    team1.powerUps += pl.powerUps
    
    if len(team1.gaByMinutes) == 0:
        team1.initPowerUpsByMinutes(len(pl.gaByMinutes))
        
    for minNum in xrange(len(pl.gaByMinutes)):
        team1.gaByMinutes[minNum] += pl.gaByMinutes[minNum]
        team1.yaByMinutes[minNum] += pl.yaByMinutes[minNum]
        team1.raByMinutes[minNum] += pl.raByMinutes[minNum]
        team1.mhByMinutes[minNum] += pl.mhByMinutes[minNum]
        
    team1.fillWeaponsKillsDeaths(pl);    

for pl in players2:
    team2.kills += pl.kills
    team2.deaths += pl.deaths
    team2.teamkills += pl.teamkills
    team2.suicides += pl.suicides
    team2.teamdeaths += pl.teamdeaths
    
    team2.powerUps += pl.powerUps
    
    if len(team2.gaByMinutes) == 0:
        team2.initPowerUpsByMinutes(len(pl.gaByMinutes))
        
    for minNum in xrange(len(pl.gaByMinutes)):
        team2.gaByMinutes[minNum] += pl.gaByMinutes[minNum]
        team2.yaByMinutes[minNum] += pl.yaByMinutes[minNum]
        team2.raByMinutes[minNum] += pl.raByMinutes[minNum]
        team2.mhByMinutes[minNum] += pl.mhByMinutes[minNum]
        
    team2.fillWeaponsKillsDeaths(pl);

# fill final battle progress    
progressLineDict = {}
progressLineDict[team1.name] = team1.frags();
progressLineDict[team2.name] = team2.frags();
matchProgressDict.append(progressLineDict)
matchProgressDictEx.append(progressLineDict)


minsCount = len(matchProgressDict)
progressLineDict = {}
progressLineDict[team1.name] = [minsCount*60, team1.frags()];
progressLineDict[team2.name] = [minsCount*60, team2.frags()];

# correct final point if necessary
if len(matchProgressDictEx2) != 0 and matchProgressDictEx2[len(matchProgressDictEx2)-1][team1.name][0] == minsCount*60:
    matchProgressDictEx2[len(matchProgressDictEx2)-1] = progressLineDict
else:
    matchProgressDictEx2.append(progressLineDict)


players1ByFrags = sorted(players1, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
playersProgressLineDict1 = {}
for pl in players1ByFrags:
    playersProgressLineDict1[pl.name] = [pl.frags(), pl.calcDelta()];
matchProgressPlayers1Dict.append(playersProgressLineDict1)
matchProgressPlayers1DictEx.append(playersProgressLineDict1)

players2ByFrags = sorted(players2, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
playersProgressLineDict2 = {}
for pl in players2ByFrags:
    playersProgressLineDict2[pl.name] = [pl.frags(), pl.calcDelta()];
matchProgressPlayers2Dict.append(playersProgressLineDict2)
matchProgressPlayers2DictEx.append(playersProgressLineDict2)        

fillExtendedBattleProgress()
    
# fill final element in calculatedStreaks
for pl in allplayers:
    pl.fillStreaks(currentMatchTime)
    pl.fillDeathStreaks(currentMatchTime)

# TODO add teammateTelefrags to team score
# print "teammateTelefrags:", teammateTelefrags

powerUpsStatus = {}
for pwrup in ["ra","ya","ga","mh"]:
    exec("powerUpsStatus[\"%s\"] = False" % (pwrup))

# move power stats for doroped players from power ups by minutes and get power ups status
for pl in allplayers:
    pl.recoverArmorStats()

    for pwrup in ["ra","ya","ga","mh"]:
        exec("if pl.%s != 0:\n    powerUpsStatus[\"%s\"] = True" % (pwrup, pwrup))

# achievements
for pl in allplayers:
    pl.calculateAchievements([], powerUpsStatus, headToHead, isTeamGame = True)
    #pl.calculateAchievements(matchProgress, powerUpsStatus, headToHead)
    
ezstatslib.calculateCommonAchievements(allplayers, headToHead, isTeamGame = True)
    

# generate output string
resultString = ""

resultString += "==================\n"
resultString += "matchdate:" + matchdate + "\n"
resultString += "map:" + mapName + "\n"
resultString += "\n"

resultString += "teams:\n"

s1 = ""
for pl in players1:
    sign = "" if s1 == "" else ", "
    if s1 == "":
        s1 = "[%s]: " % (pl.teamname)
    s1 += "%s%s" % (sign, pl.name)
resultString += s1 + "\n"

s2 = ""
for pl in players2:
    sign = "" if s2 == "" else ", "
    if s2 == "":
        s2 = "[%s]: " % (pl.teamname)
    s2 += "%s%s" % (sign, pl.name)
resultString += s2 + "\n"

# if options.withScripts:
#     resultString += "</pre>MATCH_RESULTS_PLACE\n<pre>"

resultString += "\n"
resultString += "%s[%d] x %s[%d]\n" % (totalScore[0][0], totalScore[0][1], totalScore[1][0], totalScore[1][1])
resultString += "\n"

if options.withScripts:
    resultString += "</pre>TEAM_RESULTS\n<pre>"

s1 = ""
players1ByFrags = sorted(players1, key=methodcaller("frags"), reverse=True)
for pl in players1ByFrags:
    if s1 == "":
        s1 = "[%s]:\n" % (pl.teamname)
    s1 +=  "{0:20s} {1:3d}    ({2:s})\n".format(pl.name, pl.calcDelta(), pl.getFormatedStats())
resultString += s1
resultString += "\n"

for pl in players1ByFrags:
    resultString += "{0:20s}  {1:s}\n".format(pl.name, pl.getFormatedPowerUpsStats())
resultString += "\n"

s2 = ""
players2ByFrags = sorted(players2, key=methodcaller("frags"), reverse=True)
for pl in players2ByFrags:
    if s2 == "":
        s2 = "[%s]:\n" % (pl.teamname)
    s2 +=  "{0:20s} {1:3d}    ({2:s})\n".format(pl.name, pl.calcDelta(), pl.getFormatedStats())
resultString += s2
resultString += "\n"

for pl in players2ByFrags:
    resultString += "{0:20s}  {1:s}\n".format(pl.name, pl.getFormatedPowerUpsStats())
resultString += "\n"

if options.withScripts:
    resultString += "</pre>PLAYERS_ACHIEVEMENTS_PLACE\n<pre>"

allplayersByFrags = sorted(allplayers, key=methodcaller("frags"), reverse=True)

totalStreaksHtmlTable = \
    HTML.Table(header_row=["Kill streaks (%d+)\n" % (ezstatslib.KILL_STREAK_MIN_VALUE), "Death streaks (%d+)\n" % (ezstatslib.DEATH_STREAK_MIN_VALUE)],
               rows=[ \
                   HTML.TableRow(cells=[ \
                                     HTML.TableCell( str( ezstatslib.createStreaksHtmlTable(allplayersByFrags, ezstatslib.StreakType.KILL_STREAK)) ),
                                     HTML.TableCell( str( ezstatslib.createStreaksHtmlTable(allplayersByFrags, ezstatslib.StreakType.DEATH_STREAK)) ) \
                                       ] \
                                ) \
                    ],               
               border="1", 
               style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")

# if options.withScripts:
#     resultString += "</pre>TEAM_STATS_DONUTS_PLACE\n<pre>"
# 
# resultString += "<hr>"
# 
# if options.withScripts:
#     resultString += "</pre>POWER_UPS_DONUTS_PLACE\n<pre>"

if options.withScripts:
    resultString += "</pre>TEAMS_STATS_DONUTS_PLACE\n<pre>"

if options.withScripts:
    resultString += "</pre>POWER_UPS_TIMELINE_VER2_PLACE\n<pre>"
    
foldingHeaderStr = "</pre>" + ezstatslib.HTML_SCRIPT_FOLDING_SECTION_HEADER
foldingHeaderStr = foldingHeaderStr.replace("H2_CLASS_NAME", "StreaksTable");
foldingHeaderStr = foldingHeaderStr.replace("DIV_ID_NAME", "Streaks table");

resultString += foldingHeaderStr

resultString += str(totalStreaksHtmlTable)

resultString += ezstatslib.HTML_SCRIPT_FOLDING_SECTION_FOOTER + "<pre>"

if options.withScripts:
    resultString += "</pre>STREAK_ALL_TIMELINE_PLACE\n<pre>"

i = 1
resultString += "battle progress:\n"
for p in progressStr:
    resultString += "%d:%s %s\n" % (i, "" if i >= 10 else " ",  p)
    i += 1

if totalScore[0][1] > totalScore[1][1]:
    resultString += "%d: [%s]%d\n" % (i, totalScore[0][0], (totalScore[0][1] - totalScore[1][1]))
else:
    resultString += "%d: [%s]%d\n" % (i, totalScore[1][0], (totalScore[1][1] - totalScore[0][1]))

# extended battle progress
i = 1
resultString += "\n"
resultString += "extended battle progress:\n"
for p in extendedProgressStr:
    resultString += "%d:%s %s\n" % (i, "" if i >= 10 else " ",  p)
    i += 1

if options.withScripts:
    resultString += "\nHIGHCHART_BATTLE_PROGRESS_PLACE\n"
    
if options.withScripts:
    resultString += "\nHIGHCHART_EXTENDED_BATTLE_PROGRESS_PLACE\n"

if options.withScripts:
    resultString += "\nHIGHCHART_PLAYERS_BATTLE_PROGRESS_PLACE\n"
    
if options.withScripts:
    resultString += "\nHIGHCHART_TEAM_BATTLE_PROGRESS_PLACE\n"

if options.withScripts:
    resultString += "\nHIGHCHART_PLAYERS_RANK_PROGRESS_PLACE\n"

sortedByDelta = sorted(allplayers, key=methodcaller("calcDelta"))
# print
# print "next captains: %s(%d) and %s(%d)" % (sortedByDelta[0].name, sortedByDelta[0].calcDelta(), sortedByDelta[1].name, sortedByDelta[1].calcDelta())

# team stats output
resultString += "\n"
resultString += "Team stats:\n"
resultString += "[%s]\n" % (team1.name)
resultString += "GreenArm:   " + "{0:3d}".format(team1.ga) + "  [" +  ezstatslib.sortPlayersBy(players1, "ga") + "]\n"
resultString += "YellowArm:  " + "{0:3d}".format(team1.ya) + "  [" +  ezstatslib.sortPlayersBy(players1, "ya") + "]\n"
resultString += "RedArm:     " + "{0:3d}".format(team1.ra) + "  [" +  ezstatslib.sortPlayersBy(players1, "ra") + "]\n"
resultString += "MegaHealth: " + "{0:3d}".format(team1.mh) + "  [" +  ezstatslib.sortPlayersBy(players1, "mh") + "]\n"
resultString += "\n"
resultString += "TakenDam: " + "{0:5d}".format(team1.tkn) + "  [" +  ezstatslib.sortPlayersBy(players1, "tkn") + "]\n"
resultString += "GivenDam: " + "{0:5d}".format(team1.gvn) + "  [" +  ezstatslib.sortPlayersBy(players1, "gvn") + "]\n"
resultString += "TeamDam:  " + "{0:5d}".format(team1.tm)  + "  [" +  ezstatslib.sortPlayersBy(players1, "tm") + "]\n"
resultString += "DeltaDam: " + "{0:5d}".format(team1.damageDelta()) + "  [" +  ezstatslib.sortPlayersBy(players1,"damageDelta", fieldType="method") + "]\n"
resultString += "\n"
resultString += "Kills:    " + "{0:3d}".format(team1.kills) +   "  [" +  ezstatslib.sortPlayersBy(players1, "kills") + "]\n"
resultString += "Deaths:   " + "{0:3d}".format(team1.deaths) +  "  [" +  ezstatslib.sortPlayersBy(players1, "deaths") + "]\n"
resultString += "Teamkills:" + "{0:3d}".format(team1.teamkills)+"  [" +  ezstatslib.sortPlayersBy(players1, "teamkills") + "]\n"
resultString += "Suicides: " + "{0:3d}".format(team1.suicides) + "  [" +  ezstatslib.sortPlayersBy(players1, "suicides") + "]\n"
resultString += "\n"
resultString += "Streaks:    " + " [" + ezstatslib.sortPlayersBy(players1,"streaks") + "]\n"
resultString += "SpawnFrags: " + " [" + ezstatslib.sortPlayersBy(players1,"spawnfrags") + "]\n"

resultString += "\n"
resultString += "[%s]\n" % (team2.name)
resultString += "GreenArm:   " + "{0:3d}".format(team2.ga) + "  [" +  ezstatslib.sortPlayersBy(players2, "ga") + "]\n"
resultString += "YellowArm:  " + "{0:3d}".format(team2.ya) + "  [" +  ezstatslib.sortPlayersBy(players2, "ya") + "]\n"
resultString += "RedArm:     " + "{0:3d}".format(team2.ra) + "  [" +  ezstatslib.sortPlayersBy(players2, "ra") + "]\n"
resultString += "MegaHealth: " + "{0:3d}".format(team2.mh) + "  [" +  ezstatslib.sortPlayersBy(players2, "mh") + "]\n"
resultString += "\n"
resultString += "TakenDam: " + "{0:5d}".format(team2.tkn) + "  [" +  ezstatslib.sortPlayersBy(players2, "tkn") + "]\n"
resultString += "GivenDam: " + "{0:5d}".format(team2.gvn) + "  [" +  ezstatslib.sortPlayersBy(players2, "gvn") + "]\n"
resultString += "TeamDam:  " + "{0:5d}".format(team2.tm)  + "  [" +  ezstatslib.sortPlayersBy(players2, "tm") + "]\n"
resultString += "DeltaDam: " + "{0:5d}".format(team2.damageDelta()) + "  [" +  ezstatslib.sortPlayersBy(players2,"damageDelta", fieldType="method") + "]\n"
resultString += "\n"
resultString += "Kills:    " + "{0:3d}".format(team2.kills) +   "  [" +  ezstatslib.sortPlayersBy(players2, "kills") + "]\n"
resultString += "Deaths:   " + "{0:3d}".format(team2.deaths) +  "  [" +  ezstatslib.sortPlayersBy(players2, "deaths") + "]\n"
resultString += "Teamkills:" + "{0:3d}".format(team2.teamkills)+"  [" +  ezstatslib.sortPlayersBy(players2, "teamkills") + "]\n"
resultString += "Suicides: " + "{0:3d}".format(team2.suicides) + "  [" +  ezstatslib.sortPlayersBy(players2, "suicides") + "]\n"
resultString += "\n"
resultString += "Streaks:    " + " [" + ezstatslib.sortPlayersBy(players2,"streaks") + "]\n"
resultString += "SpawnFrags: " + " [" + ezstatslib.sortPlayersBy(players2,"spawnfrags") + "]\n"

# all players
resultString += "\n"
resultString += "All players:\n"
resultString += "GreenArm:   " + " [" +  ezstatslib.sortPlayersBy(allplayers, "ga") + "]\n"
resultString += "YellowArm:  " + " [" +  ezstatslib.sortPlayersBy(allplayers, "ya") + "]\n"
resultString += "RedArm:     " + " [" +  ezstatslib.sortPlayersBy(allplayers, "ra") + "]\n"
resultString += "MegaHealth: " + " [" +  ezstatslib.sortPlayersBy(allplayers, "mh") + "]\n"
resultString += "\n"
resultString += "TakenDam:   " + " [" +  ezstatslib.sortPlayersBy(allplayers, "tkn") + "]\n"
resultString += "GivenDam:   " + " [" +  ezstatslib.sortPlayersBy(allplayers, "gvn") + "]\n"
resultString += "TeamDam:    " + " [" +  ezstatslib.sortPlayersBy(allplayers, "tm") + "]\n"
resultString += "DeltaDam:   " + " [" +  ezstatslib.sortPlayersBy(allplayers,"damageDelta", fieldType="method") + "]\n"
resultString += "\n"
resultString += "Kills:      " + " [" +  ezstatslib.sortPlayersBy(allplayers, "kills") + "]\n"
resultString += "Deaths:     " + " [" +  ezstatslib.sortPlayersBy(allplayers, "deaths") + "]\n"
resultString += "Teamkills:  " + " [" +  ezstatslib.sortPlayersBy(allplayers, "teamkills") + "]\n"
resultString += "Suicides:   " + " [" +  ezstatslib.sortPlayersBy(allplayers, "suicides") + "]\n"
resultString += "\n"
resultString += "Streaks:    " + " [" +  ezstatslib.sortPlayersBy(allplayers,"streaks") + "]\n"
resultString += "SpawnFrags: " + " [" +  ezstatslib.sortPlayersBy(allplayers,"spawnfrags") + "]\n"
resultString += "\n"
resultString += "RL skill DH:" + " [" +  ezstatslib.sortPlayersBy(allplayers, "rlskill_dh") + "]\n"
resultString += "RL skill AD:" + " [" +  ezstatslib.sortPlayersBy(allplayers, "rlskill_ad") + "]\n"
resultString += "\n"
# resultString += "Weapons:\n"
# resultString += "RL:         " + " [" +  ezstatslib.sortPlayersBy(allplayers, "w_rl", units="%") + "]\n"
# resultString += "LG:         " + " [" +  ezstatslib.sortPlayersBy(allplayers, "w_lg", units="%") + "]\n"
# resultString += "GL:         " + " [" +  ezstatslib.sortPlayersBy(allplayers, "w_gl", units="%") + "]\n"
# resultString += "SG:         " + " [" +  ezstatslib.sortPlayersBy(allplayers, "w_sg", units="%") + "]\n"
# resultString += "SSG:        " + " [" +  ezstatslib.sortPlayersBy(allplayers, "w_ssg", units="%") + "]\n"
# resultString += "\n"

resultString += "Players weapons:\n"
weaponsCheck = ezstatslib.getWeaponsCheck(allplayers)
for pl in sorted(allplayers, key=attrgetter("kills"), reverse=True):
    resultString += "{0:23s} kills  {1:3d} :: {2:100s}\n".format("[%s]%s" % (pl.teamname, pl.name), pl.kills,  pl.getWeaponsKills(pl.kills,   weaponsCheck))
    resultString += "{0:23s} deaths {1:3d} :: {2:100s}\n".format("",                                pl.deaths, pl.getWeaponsDeaths(pl.deaths, weaponsCheck))
    resultString += "\n"
    
    
resultString += "Teams weapons:\n"    
resultString += "{0:23s} kills  {1:3d} :: {2:100s}\n".format("[%s]" % (team1.name), team1.kills,  team1.getWeaponsKills(team1.kills,   weaponsCheck))
resultString += "{0:23s} deaths {1:3d} :: {2:100s}\n".format("",                    team1.deaths, team1.getWeaponsDeaths(team1.deaths, weaponsCheck))
resultString += "\n"
resultString += "{0:23s} kills  {1:3d} :: {2:100s}\n".format("[%s]" % (team2.name), team2.kills,  team2.getWeaponsKills(team2.kills,   weaponsCheck))
resultString += "{0:23s} deaths {1:3d} :: {2:100s}\n".format("",                    team2.deaths, team2.getWeaponsDeaths(team2.deaths, weaponsCheck))
resultString += "\n"

if len(disconnectedplayers) != 0:
    resultString += "\n"
    resultString += "Disconnected players:" + str(disconnectedplayers) + "\n"

# H2H stats
resultString += "\n"
resultString += "Head-to-Head stats (who :: whom)\n"
resultString += "[%s]\n" % (team1.name)
for pl in sorted(players1, key=attrgetter("kills"), reverse=True):
    resStr = ""
    for el in sorted(headToHead[pl.name], key=lambda x: x[1], reverse=True):
        resStr += "%s%s(%d)" % ("" if resStr == "" else ", ", el[0], el[1])
    resultString += "{0:20s} {1:3d} :: {2:100s}\n".format(pl.name, pl.kills, resStr)
resultString += "\n"
resultString += "[%s]\n" % (team2.name)
for pl in sorted(players2, key=attrgetter("kills"), reverse=True):
    resStr = ""
    for el in sorted(headToHead[pl.name], key=lambda x: x[1], reverse=True):
        resStr += "%s%s(%d)" % ("" if resStr == "" else ", ", el[0], el[1])
    resultString += "{0:20s} {1:3d} :: {2:100s}\n".format(pl.name, pl.kills, resStr)

# Players duels table
# allplayersByFrags = sorted(allplayers, key=methodcaller("frags"), reverse=True)
# resultString += "\n"
# resultString += "Players duels:<br>"
# headerRow=['', 'Frags', 'Kills', 'Deaths']
# playersNames = []
# for pl in allplayersByFrags:
#     headerRow.append(pl.name);
#     playersNames.append(pl.name)
# 
# colAlign=[]
# for i in xrange(len(headerRow)):
#     colAlign.append("center")
# 
# htmlTable = HTML.Table(header_row=headerRow, border="2", cellspacing="3", col_align=colAlign,
#                        style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")
# 
# for pl in allplayersByFrags:
#     tableRow = HTML.TableRow(cells=[ezstatslib.htmlBold(pl.name),
#                                     ezstatslib.htmlBold(pl.frags()),
#                                     ezstatslib.htmlBold(pl.kills),
#                                     ezstatslib.htmlBold(pl.deaths)])
#         
#     for plName in playersNames:
#         if pl.name == plName:
#             tableRow.cells.append( HTML.TableCell(str(pl.suicides), bgcolor=ezstatslib.BG_COLOR_GRAY) )
#         else:            
#             plKills = 0
#             for val in headToHead[pl.name]:
#                 if val[0] == plName:
#                     plKills = val[1]
#             
#             plDeaths = 0
#             for val in headToHead[plName]:
#                 if val[0] == pl.name:
#                     plDeaths = val[1]
#             
#             cellVal = "%s / %s" % (ezstatslib.htmlBold(plKills)  if plKills  > plDeaths else str(plKills),
#                                    ezstatslib.htmlBold(plDeaths) if plDeaths > plKills  else str(plDeaths))
#             
#             cellColor = ""
#             if plKills == plDeaths:
#                 cellColor = ezstatslib.BG_COLOR_LIGHT_GRAY
#             elif plKills > plDeaths:
#                 cellColor = ezstatslib.BG_COLOR_GREEN
#             else:
#                 cellColor = ezstatslib.BG_COLOR_RED
#             
#             tableRow.cells.append( HTML.TableCell(cellVal, bgcolor=cellColor) )
#             
#     htmlTable.rows.append(tableRow)  
# 
# resultString += str(htmlTable)

resultString += "\n"
resultString += "Players duels:<br>"

def createDuelCell(rowPlayer, player):
    plName = player.name
    
    if rowPlayer.name == plName:
        return HTML.TableCell(str(rowPlayer.suicides), bgcolor=ezstatslib.BG_COLOR_GRAY)
    else:        
        plKills = 0
        for val in headToHead[rowPlayer.name]:
            if val[0] == plName:
                plKills = val[1]
        
        plDeaths = 0
        for val in headToHead[plName]:
            if val[0] == rowPlayer.name:
                plDeaths = val[1]
        
        cellVal = "%s / %s" % (ezstatslib.htmlBold(plKills)  if plKills  > plDeaths else str(plKills),
                               ezstatslib.htmlBold(plDeaths) if plDeaths > plKills  else str(plDeaths))
        
        cellColor = ""
        if plKills == plDeaths:
            cellColor = ezstatslib.BG_COLOR_LIGHT_GRAY
        elif plKills > plDeaths:
            cellColor = ezstatslib.BG_COLOR_GREEN
        else:
            cellColor = ezstatslib.BG_COLOR_RED            

        return HTML.TableCell(cellVal, bgcolor=cellColor)
    
def createPlayersDuelTable(team, teamPlayers, enemyPlayers):
    headerRow=["[" + team.name + "]", 'Frags', 'Kills', 'Deaths']
    playersNames = []
    for pl in enemyPlayers:
        headerRow.append(pl.name);
        playersNames.append(pl.name)
        
    headerRow.append("X");
    headerRow.append("Team kills");
    headerRow.append("Team deaths");
    for pl in teamPlayers:
        headerRow.append(pl.name);
    
    colAlign=[]
    for i in xrange(len(headerRow)):
        colAlign.append("center")
    
    htmlTable = HTML.Table(header_row=headerRow, border="2", cellspacing="3", col_align=colAlign,
                           style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")
    
    for pl in teamPlayers:
        tableRow = HTML.TableRow(cells=[ezstatslib.htmlBold(pl.name),
                                        ezstatslib.htmlBold(pl.frags()),
                                        ezstatslib.htmlBold(pl.kills),
                                        ezstatslib.htmlBold(pl.deaths)])
            
        for pll in enemyPlayers:
            tableRow.cells.append( createDuelCell(pl, pll) )
                
        tableRow.cells.append( HTML.TableCell("") )
        tableRow.cells.append( HTML.TableCell(ezstatslib.htmlBold(pl.teamkills)) )
        tableRow.cells.append( HTML.TableCell(ezstatslib.htmlBold(pl.teamdeaths)) )
        
        for pll in teamPlayers:
            tableRow.cells.append( createDuelCell(pl, pll) )
                
        htmlTable.rows.append(tableRow)  

    return htmlTable 

resultString += str( createPlayersDuelTable(team1, players1ByFrags, players2ByFrags) )
resultString += "\n"
resultString += str( createPlayersDuelTable(team2, players2ByFrags, players1ByFrags) )

resultString += "\nTeammate telefrags: " + str(teammateTelefrags) + "\n"

print resultString

def writeHtmlWithScripts(f, teams, resStr):
    sortedTeams = sorted(teams, key=lambda x: (x.frags()), reverse=True)
    teamsStr = ""
    for tt in sortedTeams:
        teamsStr += "%s(%d) " % (tt.name, tt.frags())
    teamsStr = teamsStr[:-1]
    teamsStr += "\n"        
    f.write("<!--\nGAME_TEAMS\n" + teamsStr + "-->\n")    
    
    pageHeaderStr = ezstatslib.HTML_HEADER_SCRIPT_SECTION
    pageTitle = "%s %s %s" % ("TEAM", mapName, matchdate)  # global values
    pageHeaderStr = pageHeaderStr.replace("PAGE_TITLE", pageTitle)
    pageHeaderStr += \
        "google.charts.load('current', {'packages':['corechart', 'bar', 'line', 'timeline']});\n" \
        "google.charts.setOnLoadCallback(drawAllStreakTimelines);\n" \
        "google.charts.setOnLoadCallback(drawTeamResults);\n" \
        "google.charts.setOnLoadCallback(drawPowerUpsTimelineVer2);\n"
    
    f.write(pageHeaderStr)
    
    # highcharts battle progress -->
    highchartsBattleProgressFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION
            
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "Battle progress")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Frags")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", "")
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \    
    
    hcDelim = "}, {\n"
    rowLines = ""

    isRed = False
    if len(teams) == 2:
        for tt in teams:
            if "red" == tt.name:
                isRed = True
                break        
    
    for tt in teams:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (tt.name)
        # rowLines += "data: [0"
        
        # add color if one of the two teams is 'red'
        if isRed:
            if tt.name == "red":
                rowLines += "color: 'red',\n"
            else:
                rowLines += "color: 'blue',\n"
        
        rowLines += "data: [[0,0]"
                
        # graphGranularity = 1.0
        # for minEl in matchProgressDict:
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[tt.name])  # TODO format, now is 0.500000
        #     graphGranularity += 1.0
            
        graphGranularity = 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        for minEl in matchProgressDictEx:
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[tt.name])  # TODO format, now is 0.500000
            graphGranularity += 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            
        rowLines += "]\n"        
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)
    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SIMPLE)
                
    f.write(highchartsBattleProgressFunctionStr)
    # <-- highcharts battle progress
    
    # highcharts battle extended progress -->
    highchartsBattleProgressFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("highchart_battle_progress", "highchart_battle_progress_extended")
            
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "Battle progress")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Frags")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "")
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \    
    
    hcDelim = "}, {\n"
    rowLines = ""

    isRed = False
    if len(teams) == 2:
        for tt in teams:
            if "red" == tt.name:
                isRed = True
                break        
        
    for tt in teams:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (tt.name)
        # rowLines += "data: [0"
        
        # add color if one of the two teams is 'red'
        if isRed:
            if tt.name == "red":
                rowLines += "color: 'red',\n"
            else:
                rowLines += "color: 'blue',\n"
        
        rowLines += "data: [[0,0]"
            
        for minEl in matchProgressDictEx2:
            rowLines += ",[%d,%d]" % (minEl[tt.name][0], minEl[tt.name][1])  # TODO format, now is 0.500000
            
        rowLines += "]\n"        
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)
    
    matchMinutesCnt = len(matchProgressDict)
    tickPositions = ""
    for k in xrange(matchMinutesCnt*60+1):
        if k % 30 == 0:
            tickPositions += "%d," % (k)
            
    xAxisLabels = \
        "labels: {\n" \
        "     formatter: function () {\n" \
        "       return (this.value / 60).toFixed(1).toString()\n" \
        "    },\n" \
        "},\n"
    xAxisLabels += "tickPositions: [%s]\n" % (tickPositions)
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", xAxisLabels)
    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SIMPLE)
                
    f.write(highchartsBattleProgressFunctionStr)
    # <-- highcharts battle extended progress
    
    # highcharts teams battle progress -->
    matchMinutesCnt = len(matchProgressDict)
    
    minutesStr = ""
    for i in xrange(1,matchMinutesCnt+1):
        minutesStr += "'%d'," % (i)
    minutesStr = minutesStr[:-1]
    
    maxTotalFrags =  (sorted(teams, key=methodcaller("frags"), reverse=True))[0].frags()
    maxPlayerFrags = (sorted(allplayers, key=methodcaller("frags"), reverse=True))[0].frags()
    
    tn = 1
    for tt in teams:
        highchartsTeamBattleProgressFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAM_BATTLE_PROGRESS_FUNCTION
        
        rowLines = ""
        for pl in (players1 if tn == 1 else players2):
            plStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAM_BATTLE_PROGRESS_PLAYER_SECTION
            
            plPoints = ""
            for minEl in matchProgressPlayers1Dict if tn == 1 else matchProgressPlayers2Dict:
                plPoints += "%d," % (minEl[pl.name][0])
            plPoints = plPoints[:-1]        
            
            plStr = plStr.replace("PLAYER_NAME", pl.name)
            plStr = plStr.replace("PLAYER_POINTS", plPoints)
            
            rowLines += plStr
        
        teamPointsStr = ""
        for minEl in matchProgressDict:
            teamPointsStr += "%d," % (minEl[tt.name])
        teamPointsStr = teamPointsStr[:-1]
        
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("DIV_NAME", "team_progress%d" % (tn))
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("TEAM_NAME", tt.name)
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("MINUTES", minutesStr)
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("ADD_ROWS", rowLines)
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("TEAM_POINTS", teamPointsStr)
        
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", str(int(maxPlayerFrags*1.2)))
        highchartsTeamBattleProgressFunctionStr = highchartsTeamBattleProgressFunctionStr.replace("MAX_TOTAL_FRAGS",  str(int(maxTotalFrags*1.2)))
                    
        f.write(highchartsTeamBattleProgressFunctionStr)
        
        tn = 2
    # <-- highcharts teams battle progress
    
    # highcharts players battle progress -->
    highchartsBattleProgressFunctionStr = (ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION).replace("highchart_battle_progress", "highchart_battle_progress_players")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "Players battle progress")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Frags")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", "")
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \        
    
    hcDelim = "}, {\n"
    rowLines = ""        
    for pl in players1:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)
        # rowLines += "data: [0"
        rowLines += "data: [[0,0]"
        
        # graphGranularity = 1.0
        # for minEl in matchProgressPlayers1Dict:
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][0])  # TODO format, now is 0.500000            
        #     graphGranularity += 1.0
            
        graphGranularity = 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        for minEl in matchProgressPlayers1DictEx:
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][0])  # TODO format, now is 0.500000
            graphGranularity += 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        
        rowLines += "]\n"
        rowLines += ",\ndashStyle: 'ShortDash',\n    lineWidth: 3"
        
    for pl in players2:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)
        # rowLines += "data: [0"
        rowLines += "data: [[0,0]"
                
        # graphGranularity = 1.0
        # for minEl in matchProgressPlayers2Dict:        
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][0])  # TODO format, now is 0.500000
        #     graphGranularity += 1.0
            
        graphGranularity = 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        for minEl in matchProgressPlayers2DictEx:        
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][0])  # TODO format, now is 0.500000
            graphGranularity += 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            
        rowLines += "]\n"
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)
    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SIMPLE)
                
    f.write(highchartsBattleProgressFunctionStr)
    # <-- highcharts players battle progress
    
    # all streaks timeline -->
    allStreaksTimelineFunctionStr = ezstatslib.HTML_SCRIPT_ALL_STREAK_TIMELINE_FUNCTION
    
    rowLines = ""
    currentRowsLines = ""
    # isFirstTeam = False
    # isSecondTeam = False
    for pl in sorted(players1, key=methodcaller("frags"), reverse=True) + sorted(players2, key=methodcaller("frags"), reverse=True):
        
        # if not isFirstTeam and pl.teamname == players1[0].teamname:
        #     currentRowsLines += "[ '[%s]', '', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % (pl.teamname)
        #     currentRowsLines += "[ '[%s]', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % (pl.teamname, matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
        #     isFirstTeam = True
        # 
        # if not isSecondTeam and pl.teamname == players2[0].teamname:
        #     currentRowsLines += "[ '[%s]', '', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % (pl.teamname)
        #     currentRowsLines += "[ '[%s]', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % (pl.teamname, matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
        #     isSecondTeam = True
        
        strkRes,maxStrk           = pl.getCalculatedStreaksFull(1)
        for strk in strkRes:
            hintStr = "<p>&nbsp&nbsp&nbsp<b>%d: %s</b>&nbsp&nbsp&nbsp</p>" \
                      "<p>&nbsp&nbsp&nbsp<b>Sum: %s</b>&nbsp&nbsp&nbsp</p><hr>" \
                      "&nbsp&nbsp&nbsp<b>Time:</b>&nbsp%dm %ds - %dm %ds&nbsp<br>" \
                      "<b>&nbsp&nbsp&nbspDuration:</b>&nbsp%d seconds<br>&nbsp" % (strk.count, strk.formattedNames(), strk.formattedNamesSum(), (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60), strk.duration())
            rowLines += "[ '%s', '%d', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % ("[%s] %s_kills" % (pl.teamname, pl.name), strk.count, hintStr, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60))
            
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("[%s] %s_kills" % (pl.teamname, pl.name))
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("[%s] %s_kills" % (pl.teamname, pl.name), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt    
        
        deathStrkRes,deathMaxStrk = pl.getDeatchStreaksFull(1)
        for strk in deathStrkRes:
            hintStr = "<p>&nbsp&nbsp&nbsp<b>%d: %s</b>&nbsp&nbsp&nbsp</p>" \
                      "<p>&nbsp&nbsp&nbsp<b>Sum: %s</b>&nbsp&nbsp&nbsp</p><hr>" \
                      "&nbsp&nbsp&nbsp<b>Time:</b>&nbsp%dm %ds - %dm %ds&nbsp<br>" \
                      "<b>&nbsp&nbsp&nbspDuration:</b>&nbsp%d seconds<br>&nbsp" % (strk.count, strk.formattedNames(), strk.formattedNamesSum(), (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60), strk.duration())
            rowLines += "[ '%s', '%d', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % ("[%s] %s_deaths" % (pl.teamname, pl.name), strk.count, hintStr, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60))
            
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("[%s] %s_deaths" % (pl.teamname, pl.name))  
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("[%s] %s_deaths" % (pl.teamname, pl.name), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt        
    
    allStreaksTimelineFunctionStr = allStreaksTimelineFunctionStr.replace("ALL_ROWS", rowLines)
    allStreaksTimelineFunctionStr = allStreaksTimelineFunctionStr.replace("CURRENT_ROWS", currentRowsLines)
    
    allStreaksTimelineDivStr = ezstatslib.HTML_SCRIPT_ALL_STREAK_TIMELINE_DIV_TAG
    timelineChartHeight = (len(allplayersByFrags) * 2 + 1) * (33 if len(allplayersByFrags) >= 4 else 35)
    allStreaksTimelineDivStr = allStreaksTimelineDivStr.replace("HEIGHT_IN_PX", str(timelineChartHeight))
    
    # TODO black text color for deaths
    # TODO bold players names
    # TODO folding ??
                    
    f.write(allStreaksTimelineFunctionStr)
    # <-- all streaks timeline
    
    # highcharts players rank progress -->
    
    # get min and max values
    minRank = 10000
    maxRank = -10000
    for pl in players1:
        for minEl in matchProgressPlayers1DictEx:
            minRank = min(minRank, minEl[pl.name][1])
            maxRank = max(maxRank, minEl[pl.name][1])
            
    for pl in players2:
        for minEl in matchProgressPlayers2DictEx:
            minRank = min(minRank, minEl[pl.name][1])
            maxRank = max(maxRank, minEl[pl.name][1])
            
    # I -->
    highchartsBattleProgressFunctionStr = (ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION).replace("highchart_battle_progress", "players_rank1")

    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "[%s] ranks" % (players1[0].teamname))
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Rank")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "      min: %d," % (minRank))
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "      max: %d," % (maxRank))
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", "")
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \        
    
    hcDelim = "}, {\n"
    rowLines = ""        
    for pl in players1:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)
        # rowLines += "data: [0"
        rowLines += "data: [[0,0]"
        
        # graphGranularity = 1.0
        # for minEl in matchProgressPlayers1Dict:
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
        #     graphGranularity += 1.0
            
        # graphGranularity = 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        # for minEl in matchProgressPlayers1DictEx:
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
        #     graphGranularity += 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        
        graphGranularity = 1.0*2 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        k = 1
        while k < len(matchProgressPlayers1DictEx):
            minEl = matchProgressPlayers1DictEx[k]
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
            graphGranularity += 1.0*2 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            k += 2
        
        rowLines += "]\n"
        
        # add negative zone
        rowLines += ",zones: [{ value: 0, dashStyle: 'Dash' }]"
        
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SORTED)
    
    f.write(highchartsBattleProgressFunctionStr)
    # <-- I
    
    # II -->
    highchartsBattleProgressFunctionStr = (ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION).replace("highchart_battle_progress", "players_rank2")
            
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "[%s] ranks" % (players2[0].teamname))
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Rank")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "      min: %d," % (minRank))
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "      max: %d," % (maxRank))
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", "")
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \        
    
    hcDelim = "}, {\n"
    rowLines = ""        
    for pl in players2:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)
        # rowLines += "data: [0"
        rowLines += "data: [[0,0]"
        
        # graphGranularity = 1.0
        # for minEl in matchProgressPlayers2Dict:
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
        #     graphGranularity += 1.0
            
        # graphGranularity = 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        # for minEl in matchProgressPlayers2DictEx:
        #     rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
        #     graphGranularity += 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)            
            
        graphGranularity = 1.0*2 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        k = 1
        while k < len(matchProgressPlayers2DictEx):
            minEl = matchProgressPlayers2DictEx[k]
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
            graphGranularity += 1.0*2 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            k += 2
        
        rowLines += "]\n"
        
        # add negative zone
        rowLines += ",zones: [{ value: 0, dashStyle: 'Dash' }]"
        
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SORTED)
    
    f.write(highchartsBattleProgressFunctionStr)
    # <-- II
    # <-- highcharts players rank progress
    
    # players achievements -->
    playersAchievementsStr = ezstatslib.HTML_PLAYERS_ACHIEVEMENTS_DIV_TAG    
    cellWidth = "20px"
    achievementsHtmlTable = HTML.Table(border="0", cellspacing="0",
                                       style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")
    
    for pl in allplayersByFrags:
        if len(pl.achievements) != 0:
            tableRow = HTML.TableRow(cells=[ HTML.TableCell(ezstatslib.htmlBold(pl.name), align="center", width=cellWidth) ])  # TODO player name cell width
            for ach in pl.achievements:
                tableRow.cells.append( HTML.TableCell(ach.generateHtml(), align="center" ) )
            
            achievementsHtmlTable.rows.append(tableRow)
        
    playersAchievementsStr = playersAchievementsStr.replace("PLAYERS_ACHIEVEMENTS_TABLE", str(achievementsHtmlTable))    
    # <-- players achievements
    
    # power ups donuts -->
    for pwrup in ["ra","ya","ga","mh"]:
        # data: [ ['Firefox', 45.0], ['IE', 26.8]]
        dataStr = ""
        valSum = 0
        for tt in teams:
            exec("val = tt.%s" % (pwrup))
            valSum += val
            dataStr += "['%s',%d]," % (tt.name, val)
        
        donutFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_DONUT_FUNCTION_TEMPLATE if valSum != 0 else ezstatslib.HTML_SCRIPT_HIGHCHARTS_EMPTY_DONUT_FUNCTION
        donutFunctionStr = donutFunctionStr.replace("CHART_NAME", "%s_donut" % (pwrup))
        
        if pwrup == "ra":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Red Armors")
        if pwrup == "ya":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Yellow Armors")
        if pwrup == "ga":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Green Armors")
        if pwrup == "mh":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Mega Healths")
        
        if valSum != 0:    
            donutFunctionStr = donutFunctionStr.replace("ADD_ROWS", dataStr)
        
        f.write(donutFunctionStr)
    # <-- power ups donuts
    
    # team stats donuts -->
    for tstat in ["frags","kills","deaths","suicides","teamkills"]:
        # data: [ ['Firefox', 45.0], ['IE', 26.8]]
        dataStr = ""
        for tt in teams:
            exec("val = tt.%s%s" % (tstat, "()" if tstat == "frags" else ""))
            dataStr += "['%s',%d]," % (tt.name, val)
        
        donutFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_DONUT_FUNCTION_TEMPLATE
        donutFunctionStr = donutFunctionStr.replace("CHART_NAME", "%s_donut" % (tstat))
        
        if tstat == "frags":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Frags")
        if tstat == "kills":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Kills")
        if tstat == "deaths":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Deaths")
        if tstat == "suicides":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Suicides")
        if tstat == "teamkills":
            donutFunctionStr = donutFunctionStr.replace("CHART_TITLE", "Teamkills")
        
        donutFunctionStr = donutFunctionStr.replace("ADD_ROWS", dataStr)
        
        f.write(donutFunctionStr)
    # <-- team stats donuts
    
    # match results -->
    # matchResultsStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_MATCH_RESULTS_FUNCTION    
    # f.write(matchResultsStr)
    
    matchResultsStr = ezstatslib.HTML_SCRIPT_TEAM_RESULTS_FUNCTION
    
    matchResultsStr = matchResultsStr.replace("ADD_HEADER_ROW", "['', '%s',{ role: 'annotation'},{ role: 'style'},'%s',{ role: 'annotation'},{role: 'style'}],\n" % (teams[0].name, teams[1].name))
    
    color1 = ""
    color2 = ""
    if "red" in teams[0].name:
        color1 = "red"
        color2 = "blue"
    elif "red" in teams[1].name:
        color1 = "blue"
        color2 = "red"
    else:
        color1 = "red"
        color2 = "blue"    
    
    matchResultsStr = matchResultsStr.replace("ADD_STATS_ROWS", "['', %d,'%d','color: %s', %d,'%d','color: %s'],\n" % (teams[0].frags(), teams[0].frags(), color1, teams[1].frags(), teams[1].frags(), color2))
    
    f.write(matchResultsStr)
    # <-- match results
    
    # power ups timeline ver2 -->
    powerUpsTimelineVer2FunctionStr = ezstatslib.HTML_SCRIPT_POWER_UPS_TIMELINE_VER2_FUNCTION
    
    rowLines = ""
    # colors = "'gray', "
    colors = []
    for col in ["red","yellow","green","#660066"]:
        colors += [col for i in xrange(len(teams))]
    colStr = ""
    for col in colors:
        colStr += "'%s'," % (col)
    colStr = colStr[:-1]
    
    for pwrup in ["RA","YA","GA","MH"]:
        for tt in teams:
            rowLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_%s" % (tt.name, pwrup))
            rowLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_%s" % (tt.name, pwrup), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
    
    for tt in teams:
        for pu in tt.powerUps:
            rowLines += "[ '%s', '', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % \
                        ("%s_%s" % (tt.name, ezstatslib.powerUpTypeToString(pu.type)), \
                         " %s (%d min %d sec) " % (pu.playerName, pu.time / 60, pu.time % 60), \
                         ( ((pu.time-3) if (pu.time-3) >= 0 else 0) / 60), \
                         ( ((pu.time-3) if (pu.time-3) >= 0 else 0) % 60), \
                         ( ((pu.time+3) if (pu.time+3) <= matchMinutesCnt*60 else matchMinutesCnt*60) / 60), \
                         ( ((pu.time+3) if (pu.time+3) <= matchMinutesCnt*60 else matchMinutesCnt*60) % 60) )
    
    powerUpsTimelineVer2FunctionStr = powerUpsTimelineVer2FunctionStr.replace("ALL_ROWS", rowLines)
    powerUpsTimelineVer2FunctionStr = powerUpsTimelineVer2FunctionStr.replace("COLORS", colStr)    
    
    powerUpsTimelineVer2DivStr = ezstatslib.HTML_SCRIPT_POWER_UPS_TIMELINE_VER2_DIV_TAG
    powerUpsTimelineVer2ChartHeight = (len(teams) * 4 + 1) * (33 if len(teams) >= 4 else 35)
    powerUpsTimelineVer2ChartHeight = (int)(powerUpsTimelineVer2ChartHeight * 1.5)  # TODO intersections
    powerUpsTimelineVer2DivStr = powerUpsTimelineVer2DivStr.replace("HEIGHT_IN_PX", str(powerUpsTimelineVer2ChartHeight))
    powerUpsTimelineVer2DivStr = powerUpsTimelineVer2DivStr.replace("Power Ups timeline ver.2", "Power Ups timeline")
                    
    f.write(powerUpsTimelineVer2FunctionStr)
    # <-- power ups timeline ver2
    
    f.write(ezstatslib.HTML_SCRIPT_SECTION_FOOTER)
    
    # add divs
    # resStr = resStr.replace("HIGHCHART_BATTLE_PROGRESS_PLACE",      ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_DIV_TAG)
    resStr = resStr.replace("HIGHCHART_BATTLE_PROGRESS_PLACE", "")
    
    resStr = resStr.replace("HIGHCHART_EXTENDED_BATTLE_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_EXTENDED_BATTLE_PROGRESS_DIV_TAG)
    
    # resStr = resStr.replace("HIGHCHART_TEAM_BATTLE_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAM_BATTLE_PROGRESS_DIV_TAG_TEAM1 + "\n" + \
    #                                                                 ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAM_BATTLE_PROGRESS_DIV_TAG_TEAM2 )
    resStr = resStr.replace("HIGHCHART_TEAM_BATTLE_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAM_BATTLE_PROGRESS_DIV_TAG)
    resStr = resStr.replace("HIGHCHART_PLAYERS_BATTLE_PROGRESS_PLACE", (ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_DIV_TAG).replace("highchart_battle_progress", "highchart_battle_progress_players"))
    resStr = resStr.replace("STREAK_ALL_TIMELINE_PLACE", allStreaksTimelineDivStr)
    resStr = resStr.replace("HIGHCHART_PLAYERS_RANK_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_PLAYERS_RANK_PROGRESS_DIV_TAG)
    resStr = resStr.replace("PLAYERS_ACHIEVEMENTS_PLACE", playersAchievementsStr)
    # resStr = resStr.replace("POWER_UPS_DONUTS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_POWER_UPS_DONUTS_DIV_TAG)
    # resStr = resStr.replace("TEAM_STATS_DONUTS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAM_STATS_DONUTS_DIV_TAG)
    resStr = resStr.replace("TEAMS_STATS_DONUTS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_TEAMS_STATS_DONUTS_DIV_TAG)
    # resStr = resStr.replace("MATCH_RESULTS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_MATCH_RESULTS_DIV_TAG)
    resStr = resStr.replace("TEAM_RESULTS", ezstatslib.HTML_TEAM_RESULTS_FUNCTION_DIV_TAG)
    resStr = resStr.replace("POWER_UPS_TIMELINE_VER2_PLACE", powerUpsTimelineVer2DivStr)
    
    f.write(resStr)
    
    f.write(ezstatslib.HTML_PRE_CLOSE_TAG)
    
    # add script section for folding
    f.write(ezstatslib.HTML_BODY_FOLDING_SCRIPT)  
       
    f.write(ezstatslib.HTML_FOOTER_NO_PRE)


formatedDateTime = datetime.strptime(matchdate, '%Y-%m-%d %H:%M:%S %Z').strftime('%Y-%m-%d_%H_%M_%S')
filePath     = "TEAM_" + mapName + "_" + formatedDateTime + ".html"
filePathFull = "../" + filePath

isFileNew = False
if os.path.exists(filePathFull):
    # temp file 
    tmpFilePathFull = "../" + filePath + ".tmp"
    if os.path.exists(tmpFilePathFull):        
        os.remove(tmpFilePathFull)
    
    tmpf = open(tmpFilePathFull, "w")
        
    if not options.withScripts:
        tmpf.write(ezstatslib.HTML_HEADER_STR)
        tmpf.write(resultString)
        tmpf.write(ezstatslib.HTML_FOOTER_STR)
    else:
        writeHtmlWithScripts(tmpf, [team1,team2], resultString)
    
    tmpf.close()
    
    tmpinfo = os.stat(tmpFilePathFull)
    finfo   = os.stat(filePathFull)
    
    isSizesEqual = tmpinfo.st_size == finfo.st_size
    
    if isSizesEqual:
        os.remove(tmpFilePathFull)
    else:
        os.remove(filePathFull)
        os.rename(tmpFilePathFull, filePathFull)

else:  # not os.path.exists(filePathFull):
    outf = open(filePathFull, "w")
    
    if not options.withScripts:
        outf.write(ezstatslib.HTML_HEADER_STR)
        outf.write(resultString)
        outf.write(ezstatslib.HTML_FOOTER_STR)
    else:    
        writeHtmlWithScripts(outf, [team1,team2], resultString)
    
    outf.close()
    isFileNew = True

# index file
logsIndexPath    = "../" + ezstatslib.TEAM_LOGS_INDEX_FILE_NAME
tmpLogsIndexPath = "../" + ezstatslib.TEAM_LOGS_INDEX_FILE_NAME + ".tmp"

files = os.listdir("../")

teamFiles = []

headerRow = HTML.TableRow(cells=[], header=True)
attrs = {} # attribs    
attrs['colspan'] = 2
headerRow.cells.append( HTML.TableCell("Date", header=True) )
headerRow.cells.append( HTML.TableCell("Time", header=True) )
headerRow.cells.append( HTML.TableCell("Match", header=True) )
headerRow.cells.append( HTML.TableCell("Result", attribs=attrs, header=True) )

filesTable = HTML.Table(header_row=headerRow, border="1", cellspacing="3", cellpadding="8")

filesMap = {}  # key: dt, value: [[ [PL1,dt],[PL2,dt],..],[ [FD1,dt], [FD2,dt],.. ],[ [SD1,dt], [SD2,dt],.. ]]
zerodt = datetime(1970,1,1)
filesMap[zerodt] = []  # files with problems

for fname in files:
    if "html" in fname and "TEAM" in fname:     
        teamFiles.append(fname)
        
        dateRes = re.search("(?<=]_).*(?=.html)", fname)
                
        if dateRes:
            try:
                dt = datetime.strptime(dateRes.group(0), "%Y-%m-%d_%H_%M_%S")
                dateStruct = datetime.strptime(dateRes.group(0).split("_")[0], "%Y-%m-%d")
            
                if not dateStruct in filesMap.keys(): # key exist
                    filesMap[dateStruct] = []
                    
                fnamePair = [fname,dt]
                    
                filesMap[dateStruct].append(fnamePair)
                                    
            except Exception, ex:
                filesMap[zerodt].append(fnamePair)                                
                break;
                
        else: # date parse failed
            filesMap[zerodt].append(fnamePair)

sorted_filesMap = sorted(filesMap.items(), key=itemgetter(0), reverse=True)

for el in sorted_filesMap:   
    formattedDate = el[0]
    if el[0] != zerodt:
        formattedDate = el[0].strftime("%Y-%m-%d")
    
    pls = el[1] # array, val: [str,dt]
    
    
    pls = sorted(pls, key=lambda x: x[1], reverse=True)
        
    for gg in pls:
        logHeadStr = subprocess.check_output(["head", "%s" % ("../" + gg[0])])
        teamsStr = ""
        if "GAME_TEAMS" in logHeadStr:
            teamsStr = logHeadStr.split("GAME_TEAMS")[1].split("-->")[0]
            teamsStr = teamsStr.replace("\n","")
            teamsStrSplit = teamsStr.split(" ")
            
            # TODO check for xep vs. red
        
        formattedTime = gg[1].strftime("%H-%M-%S")        
        
        tableRow = HTML.TableRow(cells=[formattedDate,formattedTime])        
        tableRow.cells.append( HTML.TableCell( htmlLink(gg[0], newGifTag if checkNew(isFileNew, filePath, gg[0]) else "") ) )
        
        if teamsStr == "":
            tableRow.cells.append( HTML.TableCell("") )
            tableRow.cells.append( HTML.TableCell("") )
        else:
            tableRow.cells.append( HTML.TableCell( ezstatslib.htmlBold(teamsStrSplit[0]), align="center" ) )
            tableRow.cells.append( HTML.TableCell(teamsStrSplit[1], align="center") )
        
        filesTable.rows.append(tableRow)


logsf = open(tmpLogsIndexPath, "w")
logsf.write(ezstatslib.HTML_HEADER_STR)

logsf.write("<h1>Team logs</h1>")
# for fileName in teamFiles:
#     logsf.write( htmlLink(fileName) )
    
logsf.write(str(filesTable))
    
logsf.write(ezstatslib.HTML_FOOTER_STR)
logsf.close()

if os.path.exists(logsIndexPath):
    os.remove(logsIndexPath)
os.rename(tmpLogsIndexPath, logsIndexPath)

print filePath
