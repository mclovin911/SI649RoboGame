import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import networkx as nx
from pyvis.network import Network
import json
import scipy


# Read dataset (CSV)
with open('./robogame-v0.5/server/example1/examplematch1.socialnet.json') as f:
  df1 = json.load(f)


# Define list of selection options and sort alphabetically
# drug_list = ['Metformin', 'Glipizide', 'Lisinopril', 'Simvastatin',
#             'Warfarin', 'Aspirin', 'Losartan', 'Ibuprofen']
# drug_list.sort()

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
options = st.multiselect(
     'What the robots number?',
     nodes_lst)

st.write('You selected:', options)


def filterData(data):
    for node in nodes_lst:
        if(node in options):
            nodes_lst_selected.append(node)
        else:   
            nodes_lst_unselected.append(node)
    for link in links_lst:
        if(link in options):
            links_lst_selected.append(link)
        else:   
            links_lst_unselected.append(link)

G = nx.Graph()
nt = Network('800px', '800px',notebook=True)
G.add_nodes_from(nodes_lst)
G.add_edges_from(links_lst)
nt.from_nx(G)
nt.show_buttons()
#nt.show('nx.html')

# Save and read graph as HTML file (locally)

path = '/html_files'
nt.save_graph('./html_files/network_graph.html')
HtmlFile = open('./html_files/network_graph.html', 'r', encoding='utf-8')
# Load HTML file in HTML component for display on Streamlit page
components.html(HtmlFile.read(), height=435)