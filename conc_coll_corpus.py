#!/usr/bin/env python
# coding: utf-8

# In[2]:


import sqlite3
import pandas as pd
from dhlab.nbtext import totals
from collections import Counter



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

textmappe = "polnet_all_text"
ft = 'new_zot.db'

# In[131]:



# In[98]:


def konk(ft, word, before = 5, after = 5, size = 20):
    return query(ft, """
    select root.zid,
     (select group_concat(c.word, ' ') from ft as c
            where c.rowid >= root.rowid-? and c.rowid < root.rowid),
     root.word,
     (select group_concat(b.word, ' ') from ft as b
        where b.rowid > root.rowid and b.rowid <= root.rowid+?)
     from ft as root
     where root.word = ? limit ?  
     
     """, (before, after, word, size))

def konk_ft(ft, query, window=20, limit = 20):
    with sqlite3.connect(ft) as con:
        res = con.execute("select snippet(paragraphs, 2, '<b>', '</b>','', ?) from paragraphs where text match ? order by random() limit ?", (window, query, limit)).fetchall()
    return pd.DataFrame(res, columns = ["zid", 'concordance'])
    
def konk_corpus(ft, corpus, word, before = 5, after = 5, size = 20):
    # best egnet for et lite knippe ord
    words = tuple([x.strip() for x in word.split(',')])
    with sqlite3.connect(ft) as con:
        cur = con.cursor()
        cur.execute("attach database '' as zid_ids")
        cur.execute("create table zid_ids.zids (zid varchar)")
        for z in corpus:
            cur.execute("insert into zid_ids.zids values (?)", (z,))
        sqlq = """
            select root.zid,
             (select group_concat(c.word, ' ') from ft as c
                    where c.rowid >= root.rowid-? and c.rowid < root.rowid),
             root.word,
             (select group_concat(b.word, ' ') from ft as b
                where b.rowid > root.rowid and b.rowid <= root.rowid+?)
             from (ft as root inner join zid_ids.zids as z on root.zid = z.zid)
             where root.word in ({qs}) limit ?  
          """.format(qs = ','.join(['?']*len(words)))
        #print(sqlq)
        res = cur.execute(sqlq, (before, after) + words + (size,)).fetchall()
    return res


# In[104]:


def koll(ft, word, before = 5, after = 5, limit = 500):
    return query(ft, """
    select res.target, sum(res.freq), count(*), avg(res.dist) from
        (select root.zid, t.word as target, avg(t.rowid - root.rowid) as dist, count(*) as freq from
            (select a.zid, a.rowid, a.word from ft as a
            where a.word = ? limit ?) as root, ft as t
        where t.rowid >= root.rowid - ? and t.rowid <= root.rowid + ? and t.rowid != root.rowid
        group by root.zid, t.word) as res
        group by res.target""",(word, limit, before, after))

def koll_corpus(ft, corpus, word, before = 5, after = 5, limit = 500):
    with sqlite3.connect(ft) as con:
        cur = con.cursor()
        cur.execute("attach database '' as zid_ids")
        cur.execute("create table zid_ids.zids (zid varchar)")
        for z in corpus:
            cur.execute("insert into zid_ids.zids values (?)", (z,))
        res = cur.execute("""
            select res.target, sum(res.freq), count(*), avg(res.dist) from
                (select root.zid, t.word as target, avg(t.rowid - root.rowid) as dist, count(*) as freq from
                    (select a.zid, a.rowid, a.word from ft as a inner join zid_ids.zids as z on a.zid = z.zid
                    where a.word = ? limit ?) as root, ft as t
                where t.rowid >= root.rowid - ? and t.rowid <= root.rowid + ? and t.rowid != root.rowid
                group by root.zid, t.word) as res
                group by res.target""",(word, limit, before, after)).fetchall()
    return res


# In[159]:


def collocation(ft, word, corpus = None, before = 5, after = 5, size = 5000):
    res = koll_corpus(ft, corpus, word, before, after, limit = size)
    df = pd.DataFrame({x[0]:tuple(x[1:]) for x in res}).transpose()
    if not df.empty:
        df.columns = ['freq', 'doc', 'dist']
        res = df.sort_values(by='freq', ascending = False)
    else:
        res = df
    return res


def concordance(ft, word, corpus = None, before = 5, after = 5, size = 500):
    res = konk_corpus(ft, corpus, word, before, after, size)
    df = pd.DataFrame(res)
    if not df.empty:
        df.columns = ['zid', 'before', 'word', 'after']
    return df


# In[174]:


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


def nbtotals(n = 150000):
    tot = pd.DataFrame.from_dict(totals(n), orient = "index")
    tot.columns = ['tot']
    return tot

def unigram(ft, zid):
    with sqlite3.connect(ft) as con:
        a = con.execute("select zid, word, freq from unigram where zid = ?", (zid,)).fetchall()
    # Create DataFrame with explicit column names
    df = pd.DataFrame(a, columns=['zid', 'word', 'freq'])
    df.word = df.word.astype(str)
    df.freq = df.freq.astype(int)
    df.zid = df.zid.astype(str)
    return df.pivot_table(index='word', columns='zid', values = 'freq')
    
def corpus_text(corpus, columns = 'freq'):
    c = Counter()
    for t in corpus:
        c.update(zotero_text(t))
    res = pd.DataFrame.from_dict(c, orient = "index")
    res.columns = [columns]
    return res

def zotero_text(id):
    res = query(ft, "select word from ft where zid = ?", (id,))
    return Counter([x[0] for x in res])  