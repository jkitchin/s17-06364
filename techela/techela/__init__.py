"""A flask of techela."""
import getpass
import os
import json
import smtplib
import subprocess
import time
import urllib


from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)

COURSE = 's17-06364'
COURSEDIR = os.path.expanduser('~/{}/'.format(COURSE))

if not os.path.isdir(COURSEDIR):
    os.makedirs(COURSEDIR)
    os.makedirs(COURSEDIR + 'assignments/')
    os.makedirs(COURSEDIR + 'solutions/')
    os.makedirs(COURSEDIR + 'lectures/')

CONFIG = '{}/techela.json'.format(COURSEDIR)
if os.path.exists(CONFIG):
    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']
        NAME = data['NAME']
else:
    ANDREWID = input("Enter your Andrew ID: ")
    NAME = input("Enter your full name: ")
    with open(CONFIG, 'w') as f:
        f.write(json.dumps({'ANDREWID': ANDREWID,
                            'NAME': NAME}))


BOX_EMAIL = 'submiss.uj1v37qz3m0gpzsu@u.box.com'

BASEURL = 'https://raw.githubusercontent.com/jkitchin/s17-06364/master/'

LECTUREURL = BASEURL + 'lectures/'
ASSIGNMENTURL = BASEURL + 'assignments/'
SOLUTIONURL = BASEURL + 'solutions/'


@app.route("/")
def hello():
    # TODO download this from github.

    with open('s17-06364.json') as f:
        data = json.loads(f.read())

    # First get lecture status
    lecture_labels = data['lectures']
    lecture_paths = ['{}/lectures/{}.ipynb'.format(COURSEDIR, label)
                     for label in lecture_labels]
    lecture_status = ['Downloaded' if os.path.exists(path)
                      else 'Not downloaded'
                      for path in lecture_paths]

    # Next get assignments.
    assignment_labels = data['assignments']
    assignment_paths = ['{}/assignments/{}-{}.ipynb'.format(COURSEDIR,
                                                            ANDREWID,
                                                            label)
                        for label in assignment_labels]
    assignment_status = ['Downloaded' if os.path.exists(path)
                         else 'Not downloaded'
                         for path in assignment_paths]

    duedates = []
    turned_in = []
    for path in assignment_paths:
        with open(path) as f:
            d = json.loads(f.read())
            duedates.append(d['metadata']['org']['DUEDATE'])
            turned_in.append(d['metadata'].get('TURNED-IN', None))

    return render_template('hello.html',
                           COURSEDIR=COURSEDIR,
                           ANDREWID=ANDREWID,
                           NAME=NAME,
                           lectures=zip(lecture_labels, lecture_status),
                           assignments=zip(assignment_labels,
                                           assignment_status,
                                           duedates,
                                           turned_in))


@app.route("/lecture/<label>")
def open_lecture(label):
    fname = '{}/lectures/{}.ipynb'.format(COURSEDIR, label)
    if not os.path.exists(fname):
        urllib.request.urlretrieve(LECTUREURL
                                   + '{}.ipynb'.format(label), fname)
        # We need to check for images. Boo...
        # They look like this in the cells: ![img](./images/control-volume.png)

    # Now open the notebook.
    cmd = ["jupyter", "notebook", fname]
    subprocess.Popen(cmd, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE)

    return redirect(url_for('hello'))


@app.route("/assignment/<label>")
def open_assignment(label):
    print('Opening {}'.format(label))
    fname = '{}/assignments/{}-{}.ipynb'.format(COURSEDIR,
                                                ANDREWID,
                                                label)
    if not os.path.exists(fname):
        urllib.request.urlretrieve('{}/{}.ipynb'.format(ASSIGNMENTURL,
                                                        label),
                                   fname)

        # Insert their full name at the top
        with open(fname) as f:
            j = json.loads(f.read())

        author = {'cell_type': 'markdown',
                  'metadata': {},
                  'source': ['{} ({}@andrew.cmu.edu)\n'.format(NAME,
                                                               ANDREWID),
                             'Date: {}\n'.format(time.asctime())]}
        j['cells'].insert(0, author)

        # Also put Author metadata in so it is easy to email these back.
        j['metadata']['author'] = {}
        j['metadata']['author']['name'] = NAME
        j['metadata']['author']['email'] = '{}@andrew.cmu.edu'.format(ANDREWID)

        with open(fname, 'w') as f:
            f.write(json.dumps(j))

    # Now open the notebook.
    # os.system('jupyter notebook {}'.format(fname))
    cmd = ["jupyter", "notebook", fname]
    subprocess.Popen(cmd, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE)

    return redirect(url_for('hello'))


@app.route("/submit/<label>")
def authenticate(label):
    "Get the andrew password."
    return render_template("email.html", label=label)


@app.route("/submit_post", methods=['POST'])
def submit_post():
    """Turn in LABEL by email."""

    password = request.form['password']
    label = request.form['label']

    # Create the container (outer) email message.
    msg = MIMEMultipart()
    subject = '[{}] - Turning in {}'
    msg['Subject'] = subject.format(COURSE, label)
    msg['From'] = '{}@andrew.cmu.edu'.format(ANDREWID)
    msg['To'] = BOX_EMAIL
    msg['Cc'] = '{}@andrew.cmu.edu'.format(ANDREWID)

    ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)

    fname = '{}/assignments/{}-{}.ipynb'.format(COURSEDIR,
                                                ANDREWID,
                                                label)
    if not os.path.exists(fname):
        raise Exception('{} not found.'.format(fname))

    # Save some turn in data.
    with open(fname) as f:
        j = json.loads(f.read())

    j['metadata']['TURNED-IN'] = {}
    j['metadata']['TURNED-IN']['timestamp'] = time.asctime()

    with open(fname, 'w') as f:
        f.write(json.dumps(j))

    with open(fname, 'rb') as fp:
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(fp.read())
        # Encode the payload using Base64
        encoders.encode_base64(attachment)
        # Set the filename parameter
        aname = '{}-{}.ipynb'.format(ANDREWID, label)
        attachment.add_header('Content-Disposition', 'attachment',
                              filename=aname)
        msg.attach(attachment)

    with smtplib.SMTP_SSL('smtp.andrew.cmu.edu', port=465) as s:
        s.login(ANDREWID, password)
        s.send_message(msg)
        s.quit()

    return redirect(url_for('hello'))


if __name__ == "__main__":
    app.run()
