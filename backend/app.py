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

# for SMS
import email, smtplib, ssl
from providers import PROVIDERS
# used for MMS
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename


f = open("../credentials.json")
data = json.load(f)

client = pymongo.MongoClient("mongodb+srv://" + urllib.parse.quote(data['username']) + ":" + urllib.parse.quote(data['password']) + "@cluster0.k7a8t4b.mongodb.net/?retryWrites=true&w=majority")

mydb = client["tamudb"]
mycol = mydb["courses"]

app = Flask(__name__)

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
    username = ''
    password = ''
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

    return { 'data' : data}


def send_sms_via_email(
    number: str,
    message: str,
    provider: str,
    sender_credentials: tuple,
    subject: str = "sent using etext",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):
    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("sms")}'

    email_message = f"Subject:{subject}\nTo:{receiver_email}\n{message}"

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, email_message)

def send_mms_via_email(
    number: str,
    message: str,
    file_path: str,
    mime_maintype: str,
    mime_subtype: str,
    provider: str,
    sender_credentials: tuple,
    subject: str = "sent using etext",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):

    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("sms")}'

    email_message=MIMEMultipart()
    email_message["Subject"] = subject
    email_message["From"] = sender_email
    email_message["To"] = receiver_email

    email_message.attach(MIMEText(message, "plain"))

    with open(file_path, "rb") as attachment:
        part = MIMEBase(mime_maintype, mime_subtype)
        part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={basename(file_path)}",
        )

        email_message.attach(part)

    text = email_message.as_string()

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, text)


@app.route("/sendmessage")
def send_message():
    number = "2104000374"
    message = "did you load up valorant yet!"
    provider = "AT&T"

    sender_credentials = ("tamuregisteraggie@gmail.com", "mcodbuyplbuwmxyd")

    # SMS
    send_sms_via_email(number, message, provider, sender_credentials)

    return {'message_sent' : 'true'}