from flask import Flask, request
import pymongo
import urllib
import json 

# selenium
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import os

db = os.environ['AGGIE_REGISTER_FINDER_CREDENTIALS_DB']
username = os.environ['AGGIE_REGISTER_FINDER_CREDENTIALS_USERNAME']
password = os.environ['AGGIE_REGISTER_FINDER_CREDENTIALS_PASSWORD']
client = pymongo.MongoClient("mongodb+srv://" + urllib.parse.quote(username) + ":" + urllib.parse.quote(password) + db)

mydb = client["tamudb"]
mycol = mydb["courses"]

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://zwqrxvopowpwin:6db469619e82250ab39d43cf3854fdb2b0d1eae0136469dc0b42cac59150bcf3@ec2-18-210-64-223.compute-1.amazonaws.com:5432/d4fbgd8ra9n7hi'

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/course/<department>/<course_number>")
def get_courses(department, course_number):
    myquery = { "department": department, "course_number" : course_number}
    mydoc = mycol.find(myquery)
    jsonDict = { 'data' : []}
    for x in mydoc:
        jsonDict['data'].append({ 'department' : x['department'] , 'course_number' : x['course_number'], 'course_crn' : x['course_crn'], 'professor' : x['course_professor']})

    return jsonDict

@app.route("/howdy", methods=['POST'])
def go_howdy():
    username = 'FrankM-7'
    password = 'Messi@11'
    crnString = ""
    
    for i in request.json['crns']:
        crnString += (i + " OR ")
    print(crnString)
    driver = webdriver.Chrome()

    driver.get("https://cas.tamu.edu/cas/login?TARGET=https%3A%2F%2Fcompassxe-ssb.tamu.edu%2FStudentRegistrationSsb%2Flogin%2Fcas")
    
    # wait for the page to load
    WebDriverWait(driver, 10000).until(EC.presence_of_element_located((By.ID, 'username')))

    # add login
    driver.find_element(By.ID, 'username').send_keys(username)
    driver.find_element(By.ID, 'password').send_keys(password)
    # driver.find_element(By.CLASS_NAME, 'thinking-anim').click()

    # wait for register page to load
    WebDriverWait(driver, 10000).until(EC.presence_of_element_located((By.ID, 'classSearchLink')))

    driver.find_element(By.ID, 'classSearchLink').click()

    WebDriverWait(driver, 10000).until(EC.presence_of_element_located((By.ID, 's2id_txt_term')))

    driver.find_element(By.ID, 's2id_txt_term').click()

    WebDriverWait(driver, 10000).until(EC.presence_of_element_located((By.ID, '202231')))

    driver.find_element(By.ID, '202231').click()
    driver.find_element(By.ID, 'term-go').click()

    WebDriverWait(driver, 10000).until(EC.presence_of_element_located((By.ID, 'txt_keywordany')))

    driver.find_element(By.ID, 'txt_keywordany').send_keys(crnString)
    driver.find_element(By.ID, 'search-go').click()

    # collect cookies and store in variable
    cookieDict = driver.get_cookies()

    # close browser 
    driver.close()

    s = requests.session()
    for i in cookieDict:
        s.cookies.set(i['name'], i['value'], domain=i['domain'])
    response = json.loads(s.get('https://compassxe-ssb.tamu.edu/StudentRegistrationSsb/ssb/searchResults').text)

    print(response)

    data = []
    for i in response['data']:
        data.append({'subject' : i['subject'], 'courseNumber' : i['courseNumber'], 'courseTitle' : i['courseTitle'], 'courseReferenceNumber' : i['courseReferenceNumber'], 'seatsA' : i['seatsAvailable']})

    returnDict = {'cookies' : [], 'data' : data}

    for i in cookieDict: 
        returnDict['cookies'].append({'domain' : i['domain'], 'name': i['name'], 'value' : i['value']})

    return returnDict

@app.route("/checkseats", methods=['POST'])
def check_seats():
    # start session 
    s = requests.session()

    # put cookies into session
    for i in request.json['cookies']:
        s.cookies.set(i['name'], i['value'], domain=i['domain'])

    response = json.loads(s.get('https://compassxe-ssb.tamu.edu/StudentRegistrationSsb/ssb/searchResults').text)
    data = []
    for i in response['data']:
        data.append({'subject' : i['subject'], 'courseNumber' : i['courseNumber'], 'courseTitle' : i['courseTitle'], 'courseReferenceNumber' : i['courseReferenceNumber'], 'seatsAvailable' : i['seatsAvailable']})
        print(str(i['courseNumber']) + ' ' + str(i['seatsAvailable']))

    return { 'data' : data }
