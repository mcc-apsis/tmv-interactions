import os, sys, time, resource, re, gc, shutil
from nltk import ngrams
from multiprocess import Pool
from functools import partial
from mongoengine import *
from urllib.parse import urlparse, parse_qsl
connect('mongoengine_documents')

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

from gensim.models import Word2Vec, Doc2Vec
from gensim.models import Phrases
import gensim

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

def compare(d1, model):
    # Close all django connections
    django.db.connections.close_all()
    # If we are missing a shingle, don't even bother
    if not hasattr(d1,'shingle'):
        return None
    # unpack the shingle
    d1.shingle_list = d1.shingle
    d1.shingle = set()
    for li in list(d1.shingle_list):
        d1.shingle.add(tuple(li))
    # get the word count
    d1.wc = len(str(d1.TI).split())

    #dv = model.infer_vector(gensim.utils.simple_preprocess(d1.TI),steps=10)

    if hasattr(d1,'DO'):
        d1_do = True
    else:
        d1_do = False
    # initialise an empty list of similarity objects
    sims = []
    #get the wos docs in the same year
    #dc2 = Doc.objects.filter(PY=d1.PY).all().iterator()
    #d1word = d1.TI.split()[0]

    # Try and match by title

    try:
        d2 = Doc.objects.get(
            UT__UT__icontains="WOS:",
            title__iexact=d1.TI,
            wosarticle__di__iexact=d1.DO
        )
        try:
            py_diff = d1.PY - d2.PY
        except:
            py_diff = None
        d2_wc = d2.ti_word_count()
        dv_sim = model.docvecs.similarity_unseen_docs(
            model,
            gensim.utils.simple_preprocess(d1.TI),
            gensim.utils.simple_preprocess(d2.title),
            steps=10
        )
        sim = similarity(
            scopus_id=d1.scopus_id,
            wos_ut=d2.UT.UT,
            scopus_do=True,
            wos_do=True,
            do_match=True,
            jaccard=1,
            py_diff=py_diff,
            wc_diff=abs(d1.wc - d2_wc),
            wc = (d1.wc + d2_wc)/2,
            t_match = True
        )
        if dv_sim:
            sim.doc2vec_sim = dv_sim
            sim.doc2vec_checked = True
        sims.append(sim)
        return sims
    except:
        pass

    #print(d1word)
    dc2 = Doc.objects.filter(
        UT__UT__icontains="WOS:",
        query=365,
        wosarticle__di__isnull=False
        #PY=d1.PY,title__icontains=d1word
    )


    #print(dc2.count())
    # iterate over the wos docs in the same year that contain the first title word
    for d2 in dc2.iterator(): #Doc.objects.filter(PY=d1.PY).iterator():
        # try:
        #     #d2v =
            #try:
            dv_sim = model.docvecs.similarity_unseen_docs(
                model,
                gensim.utils.simple_preprocess(d1.TI),
                gensim.utils.simple_preprocess(d2.title),
                steps=10
            )
            #except:
            #    dv_sim = None
            # Check for doi in WoS article
            if d2.wosarticle.di is not None:
                d2_do = True
            else:
                d2_do = False
            # Check for doi match
            match = False
            if d1_do and d2_do:
                if d1.DO == d2.wosarticle.di and len(d1.DO) > 5:
                    match = True
            # Compute the jaccard similarity
            j = jaccard(d1.shingle,d2.shingle())
            #if j < 0.1 and match==False:
        #        continue
            try:
                py_diff = d1.PY - d2.PY
            except:
                py_diff = None
            if d1.TI == d2.title:
                tmatch = True
            else:
                tmatch = False
            # create a similarity object
            d2_wc = d2.ti_word_count()
            sim = similarity(
                scopus_id=d1.scopus_id,
                wos_ut=d2.UT.UT,
                scopus_do=d1_do,
                wos_do=d2_do,
                do_match=match,
                jaccard=j,
                py_diff=py_diff,
                wc_diff=abs(d1.wc - d2_wc),
                wc = (d1.wc + d2_wc)/2,
                t_match = tmatch
            )
            if dv_sim:
                sim.doc2vec_sim = dv_sim
                sim.doc2vec_checked = True
            # append this to sims
            sims.append(sim)
            #django.db.connections.close_all()
    return sims

def flatten(container):
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i

def main():
    model = Doc2Vec.load("/usr/local/apsis/queries/title_model")
    do_shingle = True
    print(scopus_doc.objects.filter(TI__isnull=True).count())
    if do_shingle:
        unshingled_s_docs = scopus_doc.objects.filter(shingle__exists=False)
        print(unshingled_s_docs.count())
        for sd in unshingled_s_docs:
            if not hasattr(sd, 'TI'):
                print(sd)
                sd.delete()
            else:
            #try:
                sd.shingle = list(shingle(sd.TI,2))
                sd.save()
            #except:
            #    pass

    scopus_docs_all = scopus_doc.objects.filter(
        shingle__exists=True,
        DO__exists=True,
        doc2vec_checked=False
    )
    s_docs_i = scopus_docs_all.count()

    #s_docs_i = 10

    chunk_size= 3

    #similarity.objects.all().delete()

    for i in range(s_docs_i//chunk_size+1):
        print(i)
        #t0 = time.time()
        f = i*chunk_size
        l = (i+1)*chunk_size
        if l > s_docs_i:
            l = s_docs_i-1
        s_docs = scopus_docs_all[f:l]

        print(s_docs)

        # initialise an empty list, and append sim items to it in parallel
        sims = []
        pool = Pool(processes=chunk_size)
        sims.append(pool.map(partial(compare,model=model),s_docs))
        pool.terminate()

        #sims = [item for sublist in sims for item in sublist]
        #try:
        #    sims = [item for sublist in sims for item in sublist]
        #except:
        #    pass

        # Flatten and remove nones
        #print(sims)
        sims = flatten(sims)
        sims = list(filter(None.__ne__, sims))

        similarity.objects.insert(sims)

        s_docs.update(doc2vec_checked=True)
        #try:
        #    similarity.objects.insert(sims)
        #except:
    #        print(sims)
    #        sys.exit()

        #itTime = time.time() - t0
        #tm = int(itTime//60)
        #ts = round(itTime-(tm*60),2)

        #print("Iteration time: " + str(tm) + " minutes and " + str(ts) + " seconds")




if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)



    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
