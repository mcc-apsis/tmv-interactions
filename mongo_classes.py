import os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from mongoengine import *
from urllib.parse import urlparse, parse_qsl
connect('mongoengine_documents')


class scopus_doc(DynamicDocument):
    scopus_id = StringField(required=True, max_length=50, unique=True)
    PY = IntField(required=True)

class scopus_ref(Document):
    text = StringField(required=True, unique=True)
    ti = StringField()
    PY = IntField()
    extra = StringField()
    doi = StringField()
    url = URLField()

class similarity(Document):
    wos_ut = StringField(required=True, max_length=50)
    scopus_id = StringField(required=True, max_length=50,unique_with='wos_ut')
    scopus_do = BooleanField(required=True, max_length=50)
    wos_do = BooleanField(required=True, max_length=50)
    do_match = BooleanField()
    t_match = BooleanField()
    jaccard = FloatField()
    doc2vec_sim = FloatField()
    doc2vec_rank = IntField()
    doc2vec_checked = BooleanField()
    py_diff = IntField()
    wc_diff = IntField()
    wc = IntField()

class match(Document):
    scopus_id = StringField(required=True, max_length=50,unique_with='wos_ut')
    wos_ut = StringField(required=True, max_length=50)
    py_diff = IntField()
    jaccard = FloatField()
    wc_diff = IntField()
