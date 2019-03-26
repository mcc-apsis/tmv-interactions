import os, sys, time, resource, re, gc, shutil, math
from nltk import ngrams
from multiprocess import Pool
from functools import partial
from mongoengine import *
from urllib.parse import urlparse, parse_qsl
connect('mongoengine_documents')

from gensim.models import Word2Vec, Doc2Vec
from gensim.models import Phrases
import gensim

import django

sys.path.append('/home/galm/software/django/tmv/BasicBrowser/')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

import pymongo
from pymongo import MongoClient
#client = MongoClient()
#db = client.documents
#scopus_docs = db.scopus_docs

from mongo_classes import *

def shingle(text,k):

    text = text.lower()
    shingleLength = k
    tokens = text.split()

    shingles = [tokens[i:i+shingleLength] for i in range(len(tokens) - shingleLength + 1) if len(tokens[i]) < 4]
    shingles = ngrams(tokens,k)
    s_set = set()
    for s in shingles:
        s_set.add(s)

    return s_set

def jaccard(s1,s2):
    try:
        return len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        return 0

def find_match(d1):
    django.db.connections.close_all()
    d1.shingle_list = d1.shingle
    d1.shingle = set()
    for li in list(d1.shingle_list):
        d1.shingle.add(tuple(li))
    d1.wc = len(str(d1.TI).split())
    matches = Doc.objects.filter(wosarticle__di=d1.DO)
    if matches.count() == 1:
        inferred_vector =
        d2 = matches.first()
        try:
            py_diff = d1.PY - d2.PY
        except:
            py_diff = None
        wc_diff = abs(d1.wc - d2.ti_word_count())
        j = jaccard(d1.shingle,d2.shingle())
        m = match(
            scopus_id = d1.scopus_id,
            wos_ut = d2.UT,
            py_diff = py_diff,
            jaccard = j,
            wc_diff = wc_diff
        )
        return(m)
        #m.save()

def find_sim(d2)

def main():

    #match.objects.all().delete()
    s_docs_count = scopus_doc.objects.filter(DO__exists=True,shingle__exists=True).count()
    print(s_docs_count)

    model = Doc2Vec.load("/queries/title_model")

    s_docs_count = 10025

    chunk_size= 10000

    for i in range(s_docs_count//chunk_size+1):
        f = i*chunk_size
        l = (i+1)*chunk_size-1
        if l > s_docs_count:
            l = s_docs_count-1
        s_docs = scopus_doc.objects.filter(DO__exists=True,shingle__exists=True)[f:l]

        matches = []
        sims = []
        pool = Pool(processes=16)
        #matches.append(pool.map(partial(find_match,),s_docs))
        sims.append(pool.map(partial(find_sim,),s_docs))
        pool.terminate()
        #matches = [x for x in matches[0] if x is not None]
        #matches = list(filter(None.__ne__, matches[0]))
        sims = list(filter(None.__ne__, sims[0]))
        #match.objects.insert(matches)
        similarity.objects.insert





if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)



    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
