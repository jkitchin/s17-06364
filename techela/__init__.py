"""A flask of techela."""

import os
import json
import smtplib
import subprocess
import time
import urllib
import sys

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)

COURSE = 's17-06364'
COURSEDIR = os.path.expanduser('~/{}/'.format(COURSE))

CONFIG = '{}/techela.json'.format(COURSEDIR)

BOX_EMAIL = 'submiss.uj1v37qz3m0gpzsu@u.box.com'

BASEURL = 'https://raw.githubusercontent.com/jkitchin/s17-06364/master/'

LECTUREURL = BASEURL + 'lectures/'
ASSIGNMENTURL = BASEURL + 'assignments/'
SOLUTIONURL = BASEURL + 'solutions/'


@app.route("/coursedir")
def open_course():
    """Open the course directory in a file explorer."""
    if sys.platform == "win32":
        os.startfile(COURSEDIR)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, COURSEDIR])

    return redirect(url_for('hello'))


@app.route("/")
def hello():

    if not os.path.isdir(COURSEDIR):
        os.makedirs(COURSEDIR)
        os.makedirs(COURSEDIR + 'assignments/')
        os.makedirs(COURSEDIR + 'solutions/')
        os.makedirs(COURSEDIR + 'lectures/')

    if not os.path.exists(CONFIG):
        return redirect(url_for('setup_view'))

    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']
        NAME = data['NAME']

    # Should be setup now. Update the course info
    ONLINE = True
    try:
        urllib.request.urlretrieve('{}/s17-06364.json'.format(BASEURL),
                                   '{}/s17-06364.json'.format(COURSEDIR))
    except:
        print('Unable to download the course json file!!!!!!')
        ONLINE = False

    with open('{}/s17-06364.json'.format(COURSEDIR)) as f:
        data = json.loads(f.read())

    # First get lecture status
    lecture_paths = [os.path.join(COURSEDIR, path)
                     for path in data['lectures']]
    lecture_files = [os.path.split(path)[-1] for path in lecture_paths]

    lecture_labels = [os.path.splitext(f)[0] for f in lecture_files]

    lecture_status = ['Downloaded' if os.path.exists(path)
                      else '<font color="red">Not downloaded</font>'
                      for path in lecture_paths]

    # Next get assignments. These are in assignments/label.ipynb For students I
    # construct assignments/andrewid-label.ipynb to check if they have local
    # versions.
    assignments = data['assignments']

    assignment_files = [os.path.split(assignment)[-1]
                        for assignment in assignments]
    assignment_labels = [os.path.splitext(f)[0] for f in assignment_files]
    assignment_paths = ['{}assignments/{}-{}.ipynb'.format(COURSEDIR,
                                                           ANDREWID,
                                                           label)
                        for label in assignment_labels]
    assignment_status = ['Downloaded' if os.path.exists(path)
                         else '<font color="red">Not downloaded</font>'
                         for path in assignment_paths]

    duedates = [assignments[f]['duedate'] for f in assignments]
    turned_in = []
    for path in assignment_paths:
        if os.path.exists(path):
            with open(path) as f:
                d = json.loads(f.read())
                ti = d['metadata'].get('TURNED-IN', None)
                if ti:
                    turned_in.append(ti['timestamp'])
                else:
                    turned_in.append('Not yet.')
        else:
            turned_in.append(None)

    return render_template('hello.html',
                           COURSEDIR=COURSEDIR,
                           ANDREWID=ANDREWID,
                           NAME=NAME,
                           ONLINE=ONLINE,
                           lectures=list(zip(lecture_labels, lecture_status)),
                           assignments4templates=list(zip(assignment_labels,
                                                          assignment_paths,
                                                          assignment_status,
                                                          duedates,
                                                          turned_in)))


@app.route("/setup")
def setup_view():
    return render_template('setup.html')


@app.route("/setup_post", methods=['POST'])
def setup_post():
    ANDREWID = request.form['andrewid']
    NAME = request.form['fullname']

    with open(CONFIG, 'w') as f:
        f.write(json.dumps({'ANDREWID': ANDREWID.lower(),
                            'NAME': NAME}))

    return redirect(url_for('hello'))


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


@app.route("/course-lecture/<label>")
def open_course_lecture(label):
    fname = '{}/lectures/course-{}.ipynb'.format(COURSEDIR, label)

    urllib.request.urlretrieve(LECTUREURL
                               + '{}.ipynb'.format(label), fname)

    # Now open the notebook.
    cmd = ["jupyter", "notebook", fname]
    subprocess.Popen(cmd, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE)

    return redirect(url_for('hello'))


@app.route("/assignment/<label>")
def open_assignment(label):
    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']
        NAME = data['NAME']

    fname = '{}assignments/{}-{}.ipynb'.format(COURSEDIR,
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


@app.route("/new")
def new_notebook():
    CWD = os.getcwd()
    os.chdir(COURSEDIR)
    cmd = ["jupyter", "notebook"]
    subprocess.Popen(cmd, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE)
    os.chdir(CWD)
    return redirect(url_for('hello'))

    
@app.route("/submit/<label>")
def authenticate(label):
    "Get the andrew password."
    return render_template("email.html", label=label)


@app.route("/submit_post", methods=['POST'])
def submit_post():
    """Turn in LABEL by email."""

    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']
        NAME = data['NAME']

    password = request.form['password']
    label = request.form['label']

    # Create the container (outer) email message.
    msg = MIMEMultipart()
    subject = '[{}] - Turning in {} from {}'
    msg['Subject'] = subject.format(COURSE, label, NAME)
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
