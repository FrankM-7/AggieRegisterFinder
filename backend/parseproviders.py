import json
from re import I
from providers import PROVIDERS

jsonPrint = {'data' : []}
for i in PROVIDERS:
    jsonPrint['data'].append({'value' : i, 'label' : i})

print(jsonPrint)