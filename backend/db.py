import pymongo
import urllib
import json 

f = open("../credentials.json")
data = json.load(f)

client = pymongo.MongoClient("mongodb+srv://" + urllib.parse.quote(data['username']) + ":" + urllib.parse.quote(data['password']) + "@cluster0.k7a8t4b.mongodb.net/?retryWrites=true&w=majority")

mydb = client["tamudb"]
mycol = mydb["courses"]

myquery = { "department": "CSCE", "course_number" : "450"}

mydoc = mycol.find(myquery)

for x in mydoc:
  print(x['department'])