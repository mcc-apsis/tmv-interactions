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

    text = text.lower().replace("-"," ")
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
        j = len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        j = 0
    return j

model = Doc2Vec.load("/usr/local/apsis/queries/title_model")

n_docs = scopus_doc.objects.all().count()


for chunk in range((n_docs // 1000)+1):

    first = chunk*1000
    last = (chunk+1)*1000
    if last > n_docs:
        last = n_docs
    docs = scopus_doc.objects.all().order_by('id')[first:last]

    print(first)
    gc.collect()
    sys.stdout.flush()

    for i,d in enumerate(docs):
        if i > 100000000000000:
            break
        if hasattr(d,'DO'):
            d1_do = True
        else:
            d1_do = False

        #d = scopus_doc.objects.get(scopus_id=sim.scopus_id)
        inferred_vector = model.infer_vector(gensim.utils.simple_preprocess(d.TI),steps=200)
        sims = model.docvecs.most_similar([inferred_vector], topn=500)
        for rank,s in enumerate(sims):
            try:
                d2 = Doc.objects.get(pk=s[0])
                if d2.title is None or hasattr(d2, "wosarticle")==False:
                    continue
                if "WOS:" not in d2.UT.UT:
                    continue
            except:
                continue

            if d2.wosarticle.di is not None:
                d2_do = True
            else:
                d2_do = False

            try:
                sim = similarity.objects.get(wos_ut=d2.UT.UT, scopus_id=d.scopus_id)
            except:
                sim = similarity(
                    wos_ut=d2.UT.UT,
                    scopus_id=d.scopus_id,
                    scopus_do = d1_do,
                    wos_do = d2_do
                )
            sim.doc2vec_sim = s[1]
            sim.save()

            if d2.wosarticle.di is not None:
                d2_do = True
            else:
                d2_do = False
            match = False
            if d1_do and d2_do:
                if d.DO == d2.wosarticle.di and len(d.DO) > 5:
                    match = True
            j = jaccard(shingle(d.TI,2), d2.shingle())

            sim.scopus_do=d1_do
            sim.wos_do=d2_do
            sim.do_match=match
            sim.jaccard=j
            sim.doc2vec_sim=s[1]
            if rank+1<0:
                print(rank)
                sys.exit()
            sim.doc2vec_rank=rank+1

            sim.save()

        d.doc2vec_checked=True
        d.save()
