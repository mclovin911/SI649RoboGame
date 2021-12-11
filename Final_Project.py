import pandas as pd
from sklearn import linear_model
import matplotlib.pyplot as plt
from sklearn.svm import SVR
from random import randrange
import numpy as np
import streamlit as st
import Robogame as rg
import networkx as nx
import time, json
import altair as alt
import operator
import time


def someFunction(robot_id):
    return []

class FriendshipGame:
    data = {}
    time_matrix = pd.DataFrame({'time':list(range(1, 101))})
    expire = [] # [(robot_id, expire_time)]
    
    def init_expiration_time(self, df):
        # df = game.getRobotInfo()
        # initialized the time robots expires
        self.expire = []
        df_expire = pd.DataFrame()
        df_expire['id'] = df['id']
        df_expire['expires'] = df['expires']
        for row in df_expire.iterrows():
            if row[1]['expires'] in range(0, 101):
                self.expire.append((int(row[1]['id']), int(row[1]['expires'])))
        self.expire.sort(key = operator.itemgetter(1))
        
    def get_expiration_time(self, robot_id):
        for item in self.expire:
            if item[0] == robot_id:
                return item[1]
    
    def updateData(self, hints):
        # updata self.data when new hints are received
        # hints in .json format, should be passed from getHint()
        newdata = pd.read_json(hints)
        for row in newdata.iterrows():
            dict = {'id': int(row[1]['id']), 'time': int(row[1]['time']) , 'value': row[1]['value']}
            key = int(row[1]['id'])
            if key in self.data.keys():
                flag = True
                for iter in self.data[key]:
                    if dict['time'] == iter['time']:
                        flag = False
                if flag is True:
                    self.data[key].append(dict)
            else:
                self.data[key] = [dict]
                
    def setInterestRobot(self, gametime): # useless now, since the time might not be 0 when first called
        # obtained from team.getGameTime()['curtime']
        gametime = int(gametime)
        if gametime < 100:
            return self.expire[gametime][0]
        else:
            return []
                
    def appendFamilyTree(self, robot_id):
        # return {time1:(value, min, max, iteration(useless), generation(useless)), time2...}
        time_dict = {}
        # obtain family tree info from someFunction, which returns [(id, generation)]
        familyInfo = someFunction(robot_id)
        # search through the list of relatives
        for t in range(0, 100):
            contain_flag = False
            for datapoint in self.data[robot_id]:
                if int(datapoint['time']) == t:
                    contain_flag = True
            if contain_flag == False:
                # check in relative robots for hints
                for relative_robot in familyInfo:
                    for datapoint in self.data[int(relative_robot[0])]:
                        if int(datapoint['time']) == t:
                            if t in time_dict.keys():
                                old = time_dict[t]
                                if (old[4] == 1 and relative_robot[1] == 2): # original closer, ignore
                                    continue
                                elif (old[4] == 2 and relative_robot[1] == 1): # new closer, use new
                                    range_max = datapoint['value'] + relative_robot[1] * 5
                                    range_min = datapoint['value'] - relative_robot[1] * 5
                                    if range_max > 100:
                                        range_max = 100
                                    if range_min < 0:
                                        range_min = 0
                                    time_dict.update({t: (datapoint['value'], range_max, range_min, 1, relative_robot[1])})
                                else:
                                    range_max = datapoint['value'] + relative_robot[1] * 5
                                    range_min = datapoint['value'] - relative_robot[1] * 5
                                    if range_max > 100:
                                        range_max = 100
                                    if range_min < 0:
                                        range_min = 0
                                    if range_max > old[1]:
                                        range_max = old[1]
                                    if range_min < old[2]:
                                        range_min = old[2]
                                    mean = (old[0] * old[3] + datapoint['value']) / (old[3] + 1)
                                    time_dict.update({t: (mean, range_max, range_min, old[3] + 1)})
                            else: # new
                                range_max = datapoint['value'] + relative_robot[1] * 5
                                range_min = datapoint['value'] - relative_robot[1] * 5
                                if range_max > 100:
                                    range_max = 100
                                if range_min < 0:
                                    range_min = 0
                                time_dict.update({t: (datapoint['value'], range_max, range_min, 1, relative_robot[1])})
        return time_dict
                        
                
    def predictRobot(self, robot_id):
        # input: id of the Robot
        # output: list of dictionary, with "time" and "value" as keys
        
        # get current available data
        if robot_id not in self.data.keys():
            return []
        df = pd.DataFrame(self.data[robot_id])
        # append data from Family Tree
        family_data = self.appendFamilyTree(robot_id)
        family_list = []
        for t in family_data.keys():
            df.loc[len(df.index)] = [robot_id, t, family_data[t][0]]
            family_list.append({'time': t, 'value': family_data[t][0], 'max': family_data[t][1], 'min': family_data[t][2]})
            # print("merged(%d, %d, %d)"%(robot_id, t, familyData[t][0]))
        # df.loc[len(df.index)] = [id, time, value]
        # fit SVR model
        temp = df.iloc[:]
        data_array = temp[['time', 'value']]
        svr = SVR(C=800, epsilon=0.05).fit(data_array[['time']], data_array['value'])
        svr_pred = svr.predict(self.time_matrix[['time']])
        # change format for output
        expiration_time = self.get_expiration_time(robot_id)
        prediction = svr_pred[expiration_time]
        output = []
        for i in range(0, 100):
            output.append({'time': i, 'value': svr_pred[i]})
        return (output, expiration_time, prediction, family_list)
    
    def printVisual(self, robot_id):
        # vis_data: normally output from predictRobot
        vis_data = self.predictRobot(robot_id)
        if vis_data == []:
            return []
        df = pd.DataFrame(vis_data[0])
        vis_line = alt.Chart(df).mark_line().encode(
            alt.X('time:Q'),
            alt.Y('value:Q')
        ).properties(
            width = 500,
            height = 300
        )
        
        df_scatter = pd.DataFrame(self.data[robot_id])
        vis_scatter = alt.Chart(df_scatter).mark_point(filled = True, color = 'blue').encode(
            alt.X('time:Q'),
            alt.Y('value:Q'),
            tooltip = ['time:Q','value:Q']
        )
        
        df_expire = pd.DataFrame({'time': [vis_data[1]], 'value': [vis_data[2]]})
        vis_expire = alt.Chart(df_expire).mark_point(filled = True, color = 'red', size = 40).encode(
            alt.X('time:Q'),
            alt.Y('value:Q'),
            tooltip = ['time:Q','value:Q']
        )
        
        if vis_data[1] < 50 :
            align_method = 'left'
            dx_value = 15
        else:
            align_method = 'right'
            dx_value = -15
            
        text_expire = vis_expire.mark_text(
            align = align_method,
            baseline='middle',
            dx=dx_value,
            size = 30
        ).encode(
            text=alt.Text('value'),
        )
        
        vis_prediction = vis_expire + text_expire
        
        # plot the interval for Family Tree
        family_df = pd.DataFrame(vis_data[3])
        family_scatter = alt.Chart(family_df).mark_point(filled = True, color = 'green').encode(
            alt.X('time:Q'),
            alt.Y('value:Q')
        )
        family_bar1 = alt.Chart(family_df).mark_bar(color = 'green',size = 9, opacity = 0.6).encode(
            alt.X('time:Q'),
            alt.Y('max:Q')
        )
        family_bar2 = alt.Chart(family_df).mark_bar(color = 'white',size = 10).encode(
            alt.X('time:Q'),
            alt.Y('min:Q')
        )
        
        vis_friendship = alt.layer(vis_line, 
                                   vis_scatter, 
                                   vis_prediction,
                                   family_scatter,
                                   family_bar1,
                                   family_bar2,
                                   title = "Robot " + str(robot_id)).configure_axis(grid=False)
        return [vis_friendship, vis_data[2]]
    
    def __init__(self):
        pass





# Main function
if __name__ == '__main__':
    predVis = st.empty()
    predValue = st.empty()
    # ---------Do not need in real Game---------------
    robotdata = pd.read_csv("../server/example1/examplematch1.robotdata.csv")
    team2 = rg.Robogame("alice")
    # ------------------------------------------------
    
    team1 = rg.Robogame("bob")
    game = FriendshipGame()
    interest_ptr = 0
    bet_ptr = 0
    print(team1.setReady())
    
    # ---------Do not need in real Game---------------
    print(team2.setReady())
    # ------------------------------------------------
    
    # Wait for game to start
    while(True):
        gametime = team1.getGameTime()
        timetogo = gametime['gamestarttime_secs'] - gametime['servertime_secs']
        if ('Error' in gametime):
            print("Error"+str(gametime))
            break
        if (timetogo <= 0):
            print("Let's go!")
            break
        print("waiting to launch... game will start in " + str(int(timetogo)))
        time.sleep(0.3) # sleep 1 second at a time, wait for the game to start
        
    # Initialize expiration time
    game.init_expiration_time(team1.getRobotInfo())
    print("Robot Expiration Time init complete")
    
    # Set initial bet in case of error
    omniplayerAllBets1 = {}
    for i in np.arange(0,100):
        omniplayerAllBets1[int(i)] = int(50)
    team1.setBets(omniplayerAllBets1)
    
    # ---------Do not need in real Game---------------
    omniplayerAllBets2 = {}
    for i in np.arange(0,100):
        omniplayerAllBets2[int(i)] = int(50)
    team2.setBets(omniplayerAllBets2)
    # ------------------------------------------------
    print("Initial bet complete")
    
    # Time loop
    game_time = team1.getGameTime()
    print(game_time)
    if 'curtime' in game_time.keys():
        set_time = game_time['curtime'] - 1
        cur_time = game_time['curtime']
    while 'curtime' in game_time.keys():
        if cur_time >= 100:
            break
        print("Current system time: %.2f"%cur_time)
        
        # set interest robot
        while cur_time - set_time < 1:
            cur_time = team1.getGameTime()['curtime']
        team1.setRobotInterest([game.expire[interest_ptr]])
        set_time = cur_time
        print("Set interest Robot to be: %d"%game.expire[interest_ptr][0])
        interest_ptr = interest_ptr + 1
        
        # Grab hints
        hints = team1.getHints()
        hints_json = json.dumps(team1.getAllPredictionHints())
        game.updateData(hints_json)
        
        # choose the robot that needs to be betted on
        while bet_ptr < 100:
            # set bet if expire with 3 seconds
            game_time = team1.getGameTime()
            if 'curtime' not in game_time.keys():
                break
            cur_time = game_time['curtime']
            print("Current time is: %.2f"%cur_time)
            if game.expire[bet_ptr][1] - cur_time < 3:
                data = game.printVisual(game.expire[bet_ptr][0])
                if data == []:
                    team1.setBets({game.expire[bet_ptr][0]: 50})
                    print("Bet set! Robot %d: %.2f"%(game.expire[bet_ptr][0], 50))
                else:
                    if data[1] > 100:
                        team1.setBets({game.expire[bet_ptr][0]: 100})
                    elif data[1] < 0:
                        team1.setBets({game.expire[bet_ptr][0]: 0})
                    else:
                        team1.setBets({game.expire[bet_ptr][0]: data[1]})
                    print("Bet set! Robot %d: %.2f"%(game.expire[bet_ptr][0], data[1]))
                    predVis.write(data[0])
                    predValue.write(data[1])
                    
                # ---------Do not need in real Game---------------
                # real value is
                real_value = float(robotdata.iloc[[game.expire[bet_ptr][0]]]['t_' + str(int(robotdata.iloc[[game.expire[bet_ptr][0]]]['expires']))])
                print("Real value is: %d"%real_value)
                # ------------------------------------------------
                bet_ptr = bet_ptr + 1
            else: 
                print("No bet set")
                break
    print("Finished")
