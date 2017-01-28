"""A flask of techela."""
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from pkg_resources import get_distribution
import json
import random
import shutil
import smtplib
import subprocess
import sys
import time
import urllib

from flask import Flask, render_template, redirect, url_for, request

__version__ = get_distribution('techela').version

app = Flask(__name__)

COURSE = 's17-06364'
COURSEDIR = os.path.expanduser('~/{}/'.format(COURSE))
SOLUTIONDIR = '{}/solutions'.format(COURSEDIR)

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

    with open(CONFIG, encoding='utf-8') as f:
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

    with open('{}/s17-06364.json'.format(COURSEDIR), encoding='utf-8') as f:
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
            with open(path, encoding='utf-8') as f:
                d = json.loads(f.read())
                ti = d['metadata'].get('TURNED-IN', None)
                if ti:
                    turned_in.append(ti['timestamp'])
                else:
                    turned_in.append('Not yet.')
        else:
            turned_in.append(None)

    solution_paths = data['solutions']
    solution_files = [os.path.split(path)[-1] for path in solution_paths]
    solution_labels = [os.path.splitext(f)[0] for f in solution_files]

    solutions = [label if label in solution_labels else None
                 for label in assignment_labels]

    return render_template('hello.html',
                           COURSEDIR=COURSEDIR,
                           ANDREWID=ANDREWID,
                           NAME=NAME,
                           ONLINE=ONLINE,
                           announcements=data['announcements'],
                           version=__version__,
                           lectures=list(zip(lecture_labels, lecture_status)),
                           assignments4templates=list(zip(assignment_labels,
                                                          assignment_paths,
                                                          assignment_status,
                                                          duedates,
                                                          turned_in,
                                                          solutions)))

@app.route("/debug")
def debug():
    "In debug mode this gets me to a console in the browser."
    raise(Exception)


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

    if os.path.exists(fname):
        os.unlink(fname)
    urllib.request.urlretrieve(LECTUREURL
                               + '{}.ipynb'.format(label), fname)

    # Now open the notebook.
    cmd = ["jupyter", "notebook", fname]
    subprocess.Popen(cmd, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE)

    return redirect(url_for('hello'))


@app.route("/solution/<label>")
def open_solution(label):
    fname = '{}/solutions/{}.ipynb'.format(COURSEDIR, label)

    urllib.request.urlretrieve(SOLUTIONURL
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

        dt = datetime.now()

        author = {'cell_type': 'markdown',
                  'metadata': {},
                  'source': ['{} ({}@andrew.cmu.edu)\n'.format(NAME,
                                                               ANDREWID),
                             'Date: {}\n'.format(dt.isoformat(" "))]}
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
    dt = datetime.now()
    j['metadata']['TURNED-IN']['timestamp'] = dt.isoformat(" ")

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

# * Admin


@app.route('/admin')
def admin():
    "Setup admin page."
    # First install the new key bindings.
    import notebook.nbextensions
    from notebook.services.config import ConfigManager

    import techela
    js = '{}/{}'.format(techela.__path__[0], 'static/techela.js')
    notebook.nbextensions.install_nbextension(js, user=True)
    cm = ConfigManager()
    cm.update('notebook', {"load_extensions": {"techela": True}})

    ONLINE = True
    try:
        urllib.request.urlretrieve('{}/s17-06364.json'.format(BASEURL),
                                   '{}/s17-06364.json'.format(COURSEDIR))
    except:
        print('Unable to download the course json file!!!!!!')
        ONLINE = False

    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']
        NAME = data['NAME']

    with open('{}/s17-06364.json'.format(COURSEDIR)) as f:
        data = json.loads(f.read())

    # Next get assignments. These are in assignments/label.ipynb For students I
    # construct assignments/andrewid-label.ipynb to check if they have local
    # versions.
    assignments = data['assignments']

    assignment_files = [os.path.split(assignment)[-1]
                        for assignment in assignments]
    assignment_labels = [os.path.splitext(f)[0] for f in assignment_files]
    duedates = [assignments[f]['duedate'] for f in assignments]

    return render_template('admin.html',
                           NAME=NAME, ANDREWID=ANDREWID,
                           ONLINE=ONLINE,
                           assignments4templates=list(zip(assignment_labels,
                                                          duedates)))


def get_roster():
    "Read roster and return a list of dictionaries for each student."
    import csv
    roster_file = os.path.expanduser('~/Box Sync/s17-06-364/course/roster.csv')
    with open(roster_file) as f:
        reader = csv.reader(f, delimiter=',')
        rows = [row for row in reader]
        roster_entries = [dict(zip(rows[0], row)) for row in rows]
    # skip first entry that is the headers
    return roster_entries[1:]


@app.route('/roster')
def roster():
    "Render roster page"
    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']

    return render_template('roster.html',
                           ANDREWID=ANDREWID,
                           roster=get_roster())


@app.route('/grade-assignment/<label>')
def grade_assignment(label):

    roster = get_roster()
    random.shuffle(roster)

    submission_dir = os.path.expanduser('~/Box Sync/s17-06-364/submissions')
    assignment_dir = os.path.expanduser('~/Box Sync/s17-06-364/assignments')
    assignment_dir = '{}/{}'.format(assignment_dir, label)

    assignment_archive_dir = os.path.expanduser('~/Box Sync/s17-06-364/assignments-archive')
    assignment_archive_dir = '{}/{}'.format(assignment_archive_dir, label)

    if not os.path.isdir(assignment_dir):
        os.makedirs(assignment_dir)

    if not os.path.isdir(assignment_archive_dir):
        os.makedirs(assignment_archive_dir)

    grade_data = []

    for entry in roster:
        andrewid = entry['Andrew ID']
        d = {}
        d['first-name'] = entry['Preferred/First Name']
        d['last-name'] = entry['Last Name']
        d['name'] = '{} {}'.format(entry['Preferred/First Name'],
                                   entry['Last Name'])

        # This is the file that was submitted
        sfile = '{}-{}.ipynb'.format(andrewid, label)
        SFILE = os.path.join(submission_dir, sfile)

        # This is an archive copy in case anything happens.
        AFILE = os.path.join(assignment_archive_dir, sfile)
        if not os.path.exists(AFILE) and os.path.exists(SFILE):
            # Now we copy SFILE to AFILE
            shutil.copy(SFILE, AFILE)

        # This the file we will grade. We move it, so it will be gone from
        # submissions. We do not move it if it already exists though.
        GFILE = os.path.join(assignment_dir, sfile)
        if not os.path.exists(GFILE) and os.path.exists(SFILE):
            # Now we move SFILE to GFILE
            shutil.move(SFILE, GFILE)

        # collect data in a dictionary
        d['filename'] = GFILE
        d['andrewid'] = andrewid
        d['label'] = label

        # Check for a grade and returned
        if os.path.exists(GFILE):
            with open(GFILE) as f:
                j = json.loads(f.read())
                if j['metadata'].get('grade', None):
                    d['grade'] = j['metadata']['grade']['overall']
                else:
                    d['grade'] = None

                if j['metadata'].get('RETURNED', None):
                    d['returned'] = j['metadata']['RETURNED']
                else:
                    d['returned'] = None

                if j['metadata'].get("TURNED-IN"):
                    d['turned-in'] = j['metadata']['TURNED-IN']['timestamp']
                else:
                    d['turned-in'] = None

        grade_data.append(d)

    # Add this function so we can use it in a template
    app.jinja_env.globals.update(exists=os.path.exists)

    return render_template('grade-assignment.html',
                           label=label,
                           grade_data=grade_data)


@app.route('/grade/<andrewid>/<label>')
def grade(andrewid, label):
    "Opens the file for andrewid and label."
    assignment_dir = os.path.expanduser('~/Box Sync/s17-06-364/assignments')
    GFILE = os.path.join(assignment_dir,
                         label,
                         '{}-{}.ipynb'.format(andrewid, label))

    # Now open the notebook.
    cmd = ["jupyter", "notebook", GFILE]
    subprocess.Popen(cmd, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE)

    return redirect(url_for('grade_assignment', label=label))


@app.route('/return/<andrewid>/<label>')
def return_one(andrewid, label):
    """Return an assignment by email. 
    If a force parameter is given return even if it was returned before.
    """
    force = True if request.args.get('force') else False
    print('force = ', force)
    assignment_dir = os.path.expanduser('~/Box Sync/s17-06-364/assignments')
    GFILE = os.path.join(assignment_dir,
                         label,
                         '{}-{}.ipynb'.format(andrewid, label))
    # Make sure file exists
    if not os.path.exists(GFILE):
        print('{} not found.'.format(GFILE))
        return redirect(url_for('grade_assignment', label=label))

    # Check for grade, we don't return ungraded files
    with open(GFILE) as f:
        j = json.loads(f.read())
        if j['metadata'].get('grade', None) is None:
            print('No grade in {}. not returning.'.format(GFILE))
            return redirect(url_for('grade_assignment', label=label))
        grade = j['metadata']['grade']['overall']

    # Check if it was already returned, we don't return it again unless force
    # is truthy.
    if j['metadata'].get('RETURNED', None) and not force:
        print('Returned already!')
        return redirect(url_for('grade_assignment', label=label))

    # ok, finally we have to send it back.
    EMAIL = '{}@andrew.cmu.edu'.format(andrewid)

    with open(CONFIG) as f:
        data = json.loads(f.read())
        ANDREWID = data['ANDREWID']

    # Create the container (outer) email message.
    msg = MIMEMultipart()
    subject = '[{}] - {}-{}.ipynb has been graded'
    msg['Subject'] = subject.format(COURSE, andrewid, label)
    msg['From'] = '{}@andrew.cmu.edu'.format(ANDREWID)
    msg['To'] = EMAIL

    body = '''Grade = {}'''.format(grade)

    msg.attach(MIMEText(body, 'plain'))

    ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)

    # Save some return data.
    with open(GFILE) as f:
        j = json.loads(f.read())

    dt = datetime.now()
    j['metadata']['RETURNED'] = dt.isoformat(" ")

    with open(GFILE, 'w') as f:
        f.write(json.dumps(j))

    with open(GFILE, 'rb') as fp:
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(fp.read())
        # Encode the payload using Base64
        encoders.encode_base64(attachment)
        # Set the filename parameter
        aname = '{}-{}.ipynb'.format(ANDREWID, label)
        attachment.add_header('Content-Disposition', 'attachment',
                              filename=aname)
        msg.attach(attachment)

    print(msg)
#    with smtplib.SMTP_SSL('relay.andrew.cmu.edu', port=465) as s:
#        s.send_message(msg)
#        s.quit()

    return redirect(url_for('grade_assignment', label=label))


@app.route('/return-all/<label>')
def return_all(label):
    """Return all the assignments for label."""

    roster = get_roster()
    andrewids = [d['Andrew ID'] for d in roster]

    for andrewid in andrewids:
        return_one(andrewid, label)
        time.sleep(1)

    return redirect(url_for('grade_assignment', label=label))
