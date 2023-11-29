#!/usr/bin/env python
# coding: utf-8

# In[2]:


import sqlite3
import pandas as pd
from dhlab.nbtext import totals
from collections import Counter
import re
import networkx as nx

import igraph as ig
import leidenalg as la

from igraph import Graph
from leidenalg import find_partition
import matplotlib.pyplot as plt
import numpy as np


def query(db, query, params = ()):
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        res = cur.execute(query, params)
    return res.fetchall()


# In[125]:
def zot():
    zotero = pd.read_excel("POLNET_from1988_load091220c.xlsx")

    def map_title(t):
        if t.startswith("St."):
            res = "STM"
        elif t.startswith("NOU"):
            res = "NOU"
        else:
            res = "Annet"
        return res

    zotero['Type'] = zotero['Title'].apply(map_title)
    return zotero

zotero = zot()



def series_int(s, default = 0):
    return s.apply(lambda x: x if isinstance(x, int) else default)

def corpus_def(column, value, comparison = '='):
        
    if comparison == '=':
        res = zotero[zotero[column] == value]
    elif "<"  in comparison or ">" in comparison :
        try:
            if "<" in comparison:
                res = zotero[zotero[column] <= value]
            else:
                res = zotero[zotero[column] >= value]
        except:
            if "<" in comparison:
                res = zotero[series_int(zotero[column], int(value) + 1) <= int(value)]
            else:
                res = zotero[series_int(zotero[column], int(value) + 1) >= int(value)]
    else:
        res = zotero[zotero[column].str.contains(value)]
    return res.Key


# In[187]:
def make_nx_graph(z):

    referanser = list(z[['Key','Notes']].to_records())
    #print(referanser[:3])
    reference_dict = {
        referanser[i][1]:re.findall("<p>([0-9A-Z]+)</p>", referanser[i][2]) 
        for i in range(len(referanser)) 
        if  type(referanser[i][2]) is str
    }
    #print(reference_dict)
    
    edge_list = [(y, x) for x in reference_dict for y in reference_dict[x] ]
    
    def label_from_z(e):
        res = z[z.Key==e]['Title'].values[0]
        elements = res.split()
        if elements[0] == "NOU":
            res = ' '.join(elements[:3])
        else:
            res = ' '.join(elements[:4])
        return str(res)
    
    nodelist = [(e, {'name':label_from_z(e)}) for e in z.Key.values ] 
    

    G = nx.DiGraph()
    
    G.add_edges_from(edge_list)
    G.add_nodes_from(nodelist)
    
    # add name for root element
    #G.nodes[0]['name'] = 'root'
   
    return G



def igraph_from_networkx(G):
    """directed graph to directed igraph"""
    h = ig.Graph.TupleList(G.edges(), directed=True)
    nx_to_ig = {node: index for index, node in enumerate(h.vs['name'])}
    centrality = {vertex:deg for vertex, deg in zip(h.vs, h.degree(mode='in'))}
    # Set the 'name' attribute in igraph for each node
    for nx_node, data in G.nodes(data=True):
        if nx_node in nx_to_ig:
            ig_index = nx_to_ig[nx_node]
            h.vs[ig_index]['name'] = nx_node
            h.vs[ig_index]['centrality'] = centrality.get(nx_node, '0')
            h.vs[ig_index]['label'] = data.get('name', 'Default Name')  # or any default value
    return h

def betweenness(h):
    # Extracting vertex identifiers, labels, and calculating betweenness
    
    vertex_data = [(vertex['name'], vertex['label'], btwn) for vertex, btwn in zip(h.vs, h.betweenness())]
    df = pd.DataFrame(vertex_data, columns=['vertex_id', 'label', 'betweenness'])
    return df.sort_values(by='betweenness', ascending=False)



def indegree(h):
    vertex_data = [(vertex['name'], vertex['label'], btwn) for vertex, btwn in zip(h.vs, h.degree(mode='in'))]
    df = pd.DataFrame(vertex_data, columns=['vertex_id', 'label', 'indegree'])
    return df.sort_values(by='indegree', ascending=False)

def outdegree(h):
    vertex_data = [(vertex['name'], vertex['label'], btwn) for vertex, btwn in zip(h.vs, h.degree(mode='out'))]
    df = pd.DataFrame(vertex_data, columns=['vertex_id', 'label', 'outdegree'])
    return df.sort_values(by='outdegree', ascending=False)

def degree(h):
    vertex_data = [(vertex['name'], vertex['label'], btwn) for vertex, btwn in zip(h.vs, h.degree(mode='all'))]
    df = pd.DataFrame(vertex_data, columns=['vertex_id', 'label', 'degree'])
    return df.sort_values(by='degree', ascending=False)


def degrees(h):
    df_i = indegree(h)
    df_o = outdegree(h)
    df_a = degree(h)
    df = pd.concat([df_i.set_index('vertex')[['in_degree']], df_o.set_index('vertex')[['out_degree']], df_a.set_index('vertex')], axis=1).reset_index()
    return df.sort_values(by='degree', ascending=False)


def make_clusters(g, iterations = 3):
    # Apply Leiden clustering
    partition = find_partition(g, la.ModularityVertexPartition, n_iterations=iterations)
    
    # Calculate degrees
    degrees = g.degree()
    
    # Normalize degree for size and transparency
    max_degree = max(degrees)
    
    min_size, max_size = 10, 50  # adjust as needed
    sizes = [min_size + (d / max_degree) * (max_size - min_size) for d in degrees]

    min_size, max_size = 4, 20  # adjust as needed
    label_sizes = [min_size + (d / max_degree) * (max_size - min_size) for d in degrees]
    
    
    max_alpha = 0.8
    alphas = [max_alpha - (d / max_degree) * max_alpha for d in degrees]
    
    # Create a color palette using matplotlib
    
    n_communities = len(partition)
    
    colors_rgb = plt.cm.tab20(np.linspace(0, 1, n_communities))
    
    
    def rgba_to_hex(rgba):
        r, g, b, a = rgba
        return "#{:02x}{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255), int(a*255))
    
    # Adjust the alpha channel for each community color based on node degree
    colors_hex = [rgba_to_hex((r, g, b, alphas[i])) for i, (r, g, b, a) in enumerate(colors_rgb)]
    
    # Assign these as attributes of the vertices in the graph
    g.vs["color"] = [colors_hex[part] for part in partition.membership]
    g.vs["size"] = sizes
    g.vs["label_size"] = label_sizes
    # Now plot the partition, which will use the vertex attributes we've just set
    
    
    
    vertex_colors = [rgba_to_hex((colors_rgb[partition.membership[i]][0], 
                                 colors_rgb[partition.membership[i]][1], 
                                 colors_rgb[partition.membership[i]][2], 
                                 alphas[i])) for i in range(len(g.vs))]
    
    # Assign the calculated colors to the vertices
    g.vs["color"] = vertex_colors
    return partition


def corpus_info_print(column = None):
    if column == None:
        print('Columns: ', ', '.join(zotero.columns))
    else:
        if column in zotero:
            print(', '.join([str(x) for x in zotero[column]]))
        else:
            print('not a column:', column)

def corpus_info(column = None):
    if column == None:
        res =  '\n\n'.join(zotero.columns)
    else:
        if column in zotero:
            res = '\n\n'.join([str(x) for x in zotero[column]])
        else:
            res = []
    return res
