import Robogame as rg
import altair as alt
import time, json
import pandas as pd
import streamlit as st
import numpy as np

#Title


def drawvis(max_key1, max_key2):
    if 'curtime' in game.getGameTime().keys():
        print(game.getGameTime()['curtime'])
        partHints = game.getAllPartHints()
        parthints_df = pd.read_json(json.dumps(partHints),orient='records')
        robots = game.getRobotInfo()
        robots = robots[robots.winner != 0]
        parts_df = parthints_df.merge(robots, on='id', how='inner').drop_duplicates(ignore_index=True)

        productivities = parts_df.pivot(index=['id','Productivity','expires'], columns='column', values='value',).reset_index()
        for i in range(len(productivities['Productivity'])):
            if productivities.loc[i,'Productivity'] > 0:
                productivities.loc[i,'Productivity'] = 1
            elif productivities.loc[i,'Productivity'] <= 0:
                productivities.loc[i,'Productivity'] = 0

        expiredrobot = alt.Chart(productivities).mark_point().encode(
            x=max_key1,
            y=max_key2,
            color = 'Productivity:N',
            tooltip = 'id'
        )

        incomingrobot = alt.Chart(productivities).mark_point(color='red').transform_filter(
            ((alt.datum.expires - game.getGameTime()['curtime']) <= 2) & ((alt.datum.expires - game.getGameTime()['curtime'])>= 0) ).encode(
            x=max_key1,
            y=max_key2,
            tooltip = 'id'
        )

        text_id = incomingrobot.mark_text(
            baseline='middle',
            size = 10,
            color = 'red',
            dx = -10
        ).encode(
            text=alt.Text('id'),
        )
        scatterplot = expiredrobot + incomingrobot + text_id
        return  scatterplot
    else:
        quit

def productivity():
    
    return 1


def findkey():
    if game.getGameTime()['curtime'] > 25:
        for i in np.arange(0,70):
            print(game.getGameTime()['curtime'])
            hints = game.getHints()
            if ('parts' in hints):
                print('we got '+str(len(hints['parts']))+' part hints')
            
            partHints = game.getAllPartHints()
            parthints_df = pd.read_json(json.dumps(partHints),orient='records')
            robots = game.getRobotInfo()
            robot = robots[robots.expires < game.getGameTime()['curtime']]

            parts_df = parthints_df.merge(robot, on='id', how='inner').drop_duplicates(ignore_index=True)
            names = ['Astrogation Buffer Length','InfoCore Size','AutoTerrain Tread Count','Polarity Sinks','Cranial Uplink Bandwidth','Repulsorlift Motor HP','Sonoreceptors']
            quantile = parts_df[parts_df.column.isin(names)]
            quantile.value = quantile.value.astype(float)
            part_cnt_df = quantile.groupby('column').size()
            imporant_part = {}
            a = 0
            for part in part_cnt_df[part_cnt_df>=2].index.values:
                p_df = quantile[quantile.column == part]
                p_corr = p_df['value'].corr(p_df['Productivity'])
                if abs(p_corr)>0.3:
                    a += 1
                imporant_part[part]=abs(p_corr)
                print(part,p_corr)
            if a == 2:
                max_key1 = max(imporant_part, key=imporant_part.get)
                del imporant_part[max_key1]
                max_key2 = max(imporant_part, key=imporant_part.get)
                print(max_key1,max_key2)
                game.setPartInterest([max_key1,max_key2])
                return (max_key1,max_key2)
            time.sleep(6)
###### Making of all the charts


if __name__ == '__main__':
    game = rg.Robogame("bob")
    game.setReady()
    print(game.getGameTime()['curtime'])
    while(True):
        gametime = game.getGameTime()
        timetogo = gametime['gamestarttime_secs'] - gametime['servertime_secs']
        
        if ('Error' in gametime):
            print("Error"+str(gametime))
            break
        if (timetogo <= 0):
            print("Let's go!")
            break
        print("waiting to launch... game will start in " + str(int(timetogo)))
        time.sleep(1)

    time.sleep(150)
    a,b = findkey()
    predVis = st.empty()
    predtime = st.empty()
    while 'curtime' in game.getGameTime().keys():
        vis = drawvis(a,b)
        predVis.write(vis)
        predtime.write(game.getGameTime()['curtime'])
        time.sleep(6)

    
