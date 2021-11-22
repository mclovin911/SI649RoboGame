import flask
from flask import request, jsonify
import pandas as pd
import numpy as np
import argparse
import uuid
import sys
import networkx as nx
import json
import time
from flask_cors import CORS

app = flask.Flask(__name__)
app.config["DEBUG"] = True
CORS(app)

config = {'team1secret':str(uuid.uuid4()),
		  'team2secret':str(uuid.uuid4()),
		  # when was the last request made
		  'team1_lR':-1,
		  'team2_lR':-1,
		  # what robots are they interested in
		  'team1_int_bots':[],
		  'team2_int_bots':[],
		  'team1_int_parts':[],
		  'team2_int_parts':[],
		  # pick a start time when both teams are ready 
		  'starttime':-1,
		  # team ready
		  'team1_ready':-1,
		  'team2_ready':-1,
		  # team bets
		  'team1_bets':np.zeros(100),
		  'team2_bets':np.zeros(100),
		  # last hint request time
		  'team1_lasthint':0,
		  'team2_lasthint':0}

t = config['team1_bets']
t = t - 1
config['team1_bets'] = t

t = config['team2_bets']
t = t - 1
config['team2_bets'] = t


socialnet = None
genealogy = None

robotadata = None

quantProps = ['Astrogation Buffer Length','InfoCore Size',
	'AutoTerrain Tread Count','Polarity Sinks',
	'Cranial Uplink Bandwidth','Repulsorlift Motor HP',
	'Sonoreceptors']
nomProps = ['Arakyd Vocabulator Model','Axial Piston Model','Nanochip Model']
allProps = quantProps + nomProps

timecolumns = []
for i in np.arange(1,101):
	timecolumns.append("t_"+str(i))


def updateWinners(curtime=None):
	if (curtime == None):
		curtime = getCurrentRuntime()

	if ((curtime < 0) or (curtime > 100)):
		return

	robotdata['winner'] = robotdata['winner'].values

	t1bets = config['team1_bets']
	t2bets = config['team2_bets']

	# find undeclared robots that have expired
	todeclare = robotdata[(robotdata.winner == -2) & (robotdata.expires <= curtime)]
	for row in todeclare.iterrows():
		row = row[1]
		rid = row['id']
		expired = int(row['expires'])
		correct = int(row['t_'+str(int(expired))])

		robotdata.at[rid,'winner'] = -1

		print(rid,"exp:",expired,"cor:",correct,"t1:",t1bets[rid],"t2:",t2bets[rid])
		
		if ((t1bets[rid] == -1) and (t2bets[rid] == -1)):
			# no one wants this robot
			robotdata.at[rid,'winner'] = -1
			continue

		if (t1bets[rid] == -1):
			# team 1 doesn't want this robot, assign to team 2
			
			robotdata.at[rid,'winner'] = 2
			continue

		if (t2bets[rid] == -1):
			# team 2 doesn't want this robot, assign to team 1
			robotdata.at[rid,'winner'] = 1
			continue

		dist1 = abs(t1bets[rid] - correct)
		dist2 = abs(t2bets[rid] - correct)
		if ((dist1 == dist2) or ((dist1 < 10) and (dist2 < 10))):
			# do social net part
			neighbors = [n for n in socialnet.neighbors(rid)]

			# determine which neighbors have been declared
			neighrow = robotdata[robotdata['id'].isin(neighbors)][['id','winner']]

			neighrow = neighrow[neighrow.winner > -1]
			

			neighbors = neighrow['id'].values
			neighdec = neighrow['winner'].values
			neighpop = [socialnet.degree[n] for n in neighbors]
			tot = sum(neighpop)
			neighpop = [n/tot for n in neighpop]
			v1 = 0
			v2 = 0
			for i in np.arange(0,len(neighbors)):
				if (neighdec[i] == 1):
					v1 = v1 + neighpop[i]
				else:
					v2 = v2 + neighpop[i]

			if (v1 > v2):
				robotdata.at[rid,'winner'] = 1
				continue
			elif (v2 > v1):
				robotdata.at[rid,'winner'] = 2
				continue
			else:
				robotdata.at[rid,'winner'] = np.random.choice([1,2], 1)[0]
				continue

		if (dist1 < dist2):
			# team 1 closer
			robotdata.at[rid,'winner'] = 1
			continue
		else:
			# team 2 closer
			robotdata.at[rid,'winner'] = 1
			continue
		#print(rid,expired,correct)

	robotdata['winner'] = robotdata['winner'].values
	#print(robotdata[robotdata.winner != -2])



@app.route('/', methods=['GET'])
def home():
    return "<h1>Robogame Server</h1>"

@app.route('/api/v1/resources/network', methods=['POST'])
def api_network():
	try:
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))

		updateWinners()
		return(config['socialnet'])
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

@app.route('/api/v1/resources/tree', methods=['POST'])
def api_tree():
	try:
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))

		updateWinners()
		return(config['genealogy'])
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

def getCurrentRuntime():
	if ('gamestarttime' not in config):
		return(-1)
	return(round((time.time() - config['gamestarttime']) / 6,2))

@app.route('/api/v1/resources/gametime', methods=['POST'])
def api_gametime():
	try:
		updateWinners()

		if (not 'gamestarttime' in config):
			return(jsonify({"Error":"Game not started"}))
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))
		else:
			ft = getCurrentRuntime()
			fl= 100-ft
			if (ft < 0):
				ft = 0
				fl = 100
			w = {"servertime_secs":time.time(),"gamestarttime_secs":config['gamestarttime'],
				"gameendtime_secs":config['gameendtime'],"unitsleft":fl,"curtime":ft}
			return(jsonify(w))
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

@app.route('/api/v1/resources/robotinfo', methods=['POST'])
def api_robotinfo():
	try:
		updateWinners()
		toret = robotdata[['id','name','expires','winner','Productivity']]
		ft = getCurrentRuntime()
		toret.loc[(toret.expires >= ft),'Productivity'] = np.NaN
		return(toret.to_json(orient="records"))
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))
	#return(jsonify({"Result":"OK"}))

def getExpiration(rid):
	e = robotdata[robotdata.id == rid]['expires']
	return(e.values[0])

def getTeam(_r):
	_r['Validated'] = 'False'
	if 'secret' in _r:
		secret = str(_r['secret'])
		if (secret == config['team1secret']):
			_r['Team'] = 1
			_r['Validated'] = 'True'
		elif (secret == config['team2secret']):
			_r['Team'] = 1
			_r['Validated'] = 'True'
		else:
			_r['Error'] = "Team secret doesn't match any team"
	else:
		_r['Error'] = "No team secret"
	return(_r) 
       
@app.route('/api/v1/resources/setinterestbots', methods=['POST'])
def api_setinterestbots():

	# TODO -- the interests should only apply going forward, not to past hints 
	try:
		updateWinners()
		if (not 'gamestarttime' in config):
			return(jsonify({"Error":"Game hasn't started"}))
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))
		req_data = request.get_json()
		req_data = getTeam(req_data)
		if ('Error' in req_data):
			return(jsonify({"Error":req_data['Error']}))
		interest = []
		if 'Bots' in req_data:
			for b in req_data['Bots']:
				interest.append(int(b))		
		if (req_data['Team'] == 1):
			config['team1_int_bots'] = interest
		elif (req_data['Team'] == 2):
			config['team2_int_bots'] = interest
		return(jsonify({"Result":"OK"}))
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

@app.route('/api/v1/resources/setinterestparts', methods=['POST'])
def api_setinterestparts():
	try:
		updateWinners()
		if (not 'gamestarttime' in config):
			return(jsonify({"Error":"Game hasn't started"}))
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))
		req_data = request.get_json()
		req_data = getTeam(req_data)
		if ('Error' in req_data):
			return(jsonify({"Error":req_data['Error']}))
		interest = []
		if 'Parts' in req_data:
			for b in req_data['Parts']:
				interest.append(b)		
		if (req_data['Team'] == 1):
			config['team1_int_parts'] = interest
		elif (req_data['Team'] == 2):
			config['team2_int_parts'] = interest

		return(jsonify({"Result":"OK"}))
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

@app.route('/api/v1/resources/setbets', methods=['POST'])
def api_setbets():
	try:
		updateWinners()
		if (not 'gamestarttime' in config):
			return(jsonify({"Error":"Game hasn't started"}))
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))

		req_data = request.get_json()
		req_data = getTeam(req_data)
		if ('Error' in req_data):
			return(jsonify({"Error":req_data['Error']}))
		bets = None
		if (req_data['Team'] == 1):
			bets = config['team1_bets']
		elif (req_data['Team'] == 2):
			bets = config['team2_bets']
		newbets = req_data['Bets']
		curtime = getCurrentRuntime()
		for b in newbets.keys():
			if (int(b) <= len(bets)):
				expires = getExpiration(int(b))
				if (expires <= curtime):
					# robot already expired
					continue
				if ((newbets[b] >= -1) and (newbets[b] <= 100)):
					bets[int(b)] = newbets[b]
		print(bets)
		if (req_data['Team'] == 1):
			config['team1_bets'] = bets
		elif (req_data['Team'] == 2):
			config['team2_bets'] = bets
		return(jsonify({"Result":"OK"}))
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

def getRobotHints(interests,samples):
	toret = []

	for i in np.arange(0,samples):
		# pick 5 rows at random
		s = robotdata.sample(5)
		j = 0
		randcols = np.random.choice(timecolumns, 5)
		for row in s.iterrows():
			row = row[1]
			rid = row['id']
			randcol = randcols[j].replace("t_","")
			randval = row[randcols[j]]
			d = {'id':rid,'time':int(randcol),'value':randval}
			toret.append(d)
			j = j + 1

		j = 0 
		s = robotdata
		if (len(interests) > 1):
			# if player expressed interest
			# pick those robots
			s = robotdata[robotdata['id'].isin(interests)]
		j = 0
		s = s.sample(5,replace=True)
		randcols = np.random.choice(timecolumns, 5)
		for row in s.iterrows():
			row = row[1]
			rid = row['id']
			randcol = randcols[j].replace("t_","")
			randval = row[randcols[j]]
			d = {'id':rid,'time':int(randcol),'value':randval}
			toret.append(d)
			j = j + 1

	return(toret)

def getPartHints(interests,samples):
	toret = []

	possi = robotdata[robotdata.id < 100]

	for i in np.arange(0,samples):
		if (len(interests) == 0):
			# user hasn't expressed interests,
			# all data is possible
			interests = allProps

		s = possi.sample(6)
		j = 1
		validcol = allProps
		selection = np.random.choice(validcol, 3)
		selection = np.append(selection,np.random.choice(interests, 3))
		for row in s.iterrows():
			row = row[1]
			rid = row['id']
			randcol = selection[j-1]
			randval = row[randcol]
			d = {'id':rid,'column':randcol,'value':randval}
			toret.append(d)
			j = j + 1				
			#print(toret)

	return(toret)


@app.route('/api/v1/resources/gethints', methods=['POST'])
def api_gethints():
	try:
		updateWinners()
		if (not 'gamestarttime' in config):
			return(jsonify({"Error":"Game hasn't started"}))
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))

		req_data = request.get_json()
		req_data = getTeam(req_data)
		if ('Error' in req_data):
			return(jsonify({"Error":req_data['Error']}))

		team = 0
		lastreq = -1
		roboint = []
		partint = []

		if (req_data['Team'] == 1):
			team = 1
			lastreq = config['team1_lasthint']
			roboint = config['team1_int_bots']
			partint = config['team1_int_parts']
		else:
			team = 2
			lastreq = config['team2_lasthint']
			roboint = config['team1_int_bots']
			partint = config['team1_int_parts']

		reqtime = getCurrentRuntime()
		if (reqtime - lastreq < 1):
			return(jsonify({}))


		# number of time units since last ask, specs the 
		# number of things we can respond
		samples = round(reqtime - lastreq)

		# half of samples should be random, half from interest list
		p = getPartHints(partint, samples)
		r = getRobotHints(roboint, samples)

		if (team == 1):
			config['team1_lasthint'] = reqtime
		else:
			config['team2_lasthint'] = reqtime

		return(jsonify({"parts":p,"predictions":r}))

	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

@app.route('/api/v1/resources/setready', methods=['POST'])
def api_setready():
	try:
		updateWinners()
		if (('gameendtime' in config) and (time.time() > config['gameendtime'])):
			return(jsonify({"Error":"Game completed"}))

		if ('gamestarttime' in config):
			return(jsonify({"Error":"Game already started"}))
		print(request)
		req_data = request.get_json()
		req_data = getTeam(req_data)

		if ('Error' in req_data):
			return(jsonify({"Error":req_data['Error']}))
		if (req_data['Team'] == 1):
			config['team1_ready'] = 1
		if (req_data['Team'] == 2):
			config['team2_ready']= 1
		if ((config['team1_ready'] == 1) and (config['team2_ready'] == 1)):
			startGame()
		return(jsonify({"Result":"OK"}))
	except:
		e = sys.exc_info()[0]
		return(jsonify({"Error":str(e)}))

def startGame():
	start = time.time() + 10
	end = start + 600
	config['gamestarttime'] = start
	config['gameendtime'] = end
	return(start)

def simulatedSecondPlayer():
	config['team2_ready']= 1
	bets = config['team2_bets']
	for i in np.arange(0,100):
		bets[i] = 50
	config['team2_bets'] = bets
	if ((config['team1_ready'] == 1) and (config['team2_ready'] == 1)):
		config['starttime'] = startGame()

def init_argparse() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		usage="%(prog)s [OPTION] [gameid]...",
		description="run th server"
	)
	
	parser.add_argument('gameid')
	parser.add_argument("-s", "--simulated", help="play a simulated player two", 
		action='store_true')
	parser.add_argument("-t1s", "--team1secret", help="secret for team 1, default is random")
	parser.add_argument("-t2s", "--team2secret", help="secret for team 2, default is random")
	parser.add_argument("-d", "--directory", help="directory for game files, default is cwd", 
		default="./")
	return parser

parser = init_argparse()
args = parser.parse_args()


if (args.team1secret != None):
	config['team1secret'] = args.team1secret

if (args.team2secret != None):
	config['team2secret'] = args.team2secret

if (config['team1secret'] == config['team2secret']):
	print("Error! Team 1 and Team 2 secrets must be different")
	sys.exit(0)


print("Team 1 Secret: " + config['team1secret'])


if (args.simulated):
	print("Team 2 will be simulated")
	simulatedSecondPlayer()
else:
	print("Team 2 Secret: " + config['team2secret'])

config['gameid'] = args.gameid

with open(args.directory + "/" + args.gameid+".socialnet.json") as json_file:
	data = json.load(json_file)
	socialnet = nx.node_link_graph(data)
	config['socialnet'] = data

with open(args.directory + "/" + args.gameid+".tree.json") as json_file:
	data = json.load(json_file)	
	genealogy = nx.tree_graph(data)
	config['genealogy'] = data

robotdata = pd.read_csv(args.directory + "/" + args.gameid+".robotdata.csv")
robotdata['winner'] = -2

outf = open(args.directory + "/" + args.gameid+"",'w')
for i in np.arange(0,100):
	r = getRobotHints([],1)
	p = getPartHints([],1)

app.run()
