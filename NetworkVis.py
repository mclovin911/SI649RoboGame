from altair.vegalite.v4.schema.channels import Column
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import networkx as nx
from pyvis.network import Network
import json
import scipy
import altair as alt
from streamlit.proto.DataFrame_pb2 import DataFrame


# Read dataset (CSV)
with open('./robogame-v0.5/server/example1/examplematch1.socialnet.json') as f:
  df1 = json.load(f)


# Create network graph
nodes_lst = []
links_lst = []
nodes_lst_selected = []
nodes_lst_unselected = []
links_lst_unselected = []
links_lst_selected = []
def data_setup(data):
    df_nodes = data['nodes']
    df_links = data['links']
    for node in df_nodes:
        nodes_lst.append(node['id'])
    for link in df_links:
        links_lst.append([link['source'],link['target']])
data_setup(df1)

# Start Chart selection
st.title('Network Graph For Robogame')
options = st.sidebar.multiselect(
     'What the robots number?',
     nodes_lst)

if options == []:
    options1 = nodes_lst
else:
    options1 = options

#filter data based on selection
def filterData():
    for node in nodes_lst:
        if(node in options1):
            nodes_lst_selected.append(node)
        else:   
            nodes_lst_unselected.append(node)
    for link in links_lst:
        if(any(item in link for item in options1)):
            links_lst_selected.append(link)
        else:   
            links_lst_unselected.append(link)

filterData()

#write a summary
connectionCount = {}
def calculate():
    for robot in nodes_lst:
        connection_lst = []
        for link in links_lst:
            if(robot in link):
                for item in link:
                    if(item != robot):
                        connection_lst.append(item)
        connectionCount[robot]= connection_lst
calculate()
#st.write(connectionCount)
def summary(options):
    for selected in options:
        st.sidebar.write('The robot', selected, 'has', len(connectionCount[selected]), 'connections. They are')
        st.sidebar.markdown(connectionCount[selected])
summary(options1)

G = nx.Graph()
nt = Network('1000px', '1000px',notebook=True)

G.add_nodes_from(nodes_lst_selected, color = "#003F63")
G.add_nodes_from(nodes_lst_unselected, color = "#F2B138")
G.add_edges_from(links_lst_selected, )
G.add_edges_from(links_lst_unselected, hidden=True)
nt.from_nx(G)
nt.show_buttons()
#nt.show('nx.html')

# Save and read graph as HTML file (locally)

path = '/html_files'
nt.save_graph('./html_files/network_graph.html')
HtmlFile = open('./html_files/network_graph.html', 'r', encoding='utf-8')
# Load HTML file in HTML component for display on Streamlit page
components.html(HtmlFile.read(), height=500)

#display a bar chart
count = {}
for item in connectionCount:
    count[item] = len(connectionCount[item])

count2 = {'robotN': count.keys(), 'connectionN': count.values()}
df = pd.DataFrame.from_dict(count2)
bar = alt.Chart(df).mark_bar().transform_window(
    sort=[alt.SortField('connectionN',order='descending')],
    rank='rank(*)'
).transform_filter(
    alt.datum.rank<10
).encode(
    alt.Y('robotN:N', sort=alt.EncodingSortField(
        field='connectionN', order='descending')),
    alt.X('connectionN:Q'),
    color=alt.value('#F2B138')   # And if it's not true it sets the bar steelblue.
 )

st.altair_chart(bar)