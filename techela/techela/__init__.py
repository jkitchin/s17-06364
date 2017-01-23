# This code can be put in any Python module, it does not require IPython
# itself to be running already.  It only creates the magics subclass but
# doesn't instantiate it yet.
import collections
import getpass
import json
import os
import shutil
import smtplib
import subprocess
import sys
import time
import urllib.request
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from IPython import get_ipython
from IPython.core.magic import (Magics, magics_class, line_magic)
from IPython.core.magic_arguments import (argument, magic_arguments,
                                          parse_argstring)

from IPython.display import display, Javascript
from IPython.display import display_javascript
from IPython.core.display import HTML


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


def open_file(filename):
    """Cross-platform open file function."""
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])


# * User magic
@magics_class
class Techela(Magics):
    """IPython Magics for students.
    It is a command like this:
    > techela open label
    """

    @magic_arguments()
    @argument('-l', '--lecture', type=str, help='Open a lecture.')
    @argument('-o', '--open', type=str, help='Open an assignment.')
    @argument('-s', '--solution', type=str, help='Open a solution.')
    @argument('-t', '--turn-in', type=str, help='Turn in an assignment.')
    @line_magic
    def techela(self, line):
        """IPython magic function to get and turn in assignments."""

        args = parse_argstring(self.techela, line)

        if args.open:
            self.open(args.open)
        elif args.lecture:
            self.lecture(args.lecture)
        elif args.solution:
            self.solution(args.solution)
        elif args.turn_in:
            self.turn_in(args.turn_in)

    def open(self, label):
        """Open label.ipynb, and download if needed."""
        print('Opening {}'.format(label))
        fname = '{}/assignments/{}-{}.ipynb'.format(COURSEDIR,
                                                    ANDREWID,
                                                    label)
        if not os.path.exists(fname):
            print('Downloading {}.'.format(ASSIGNMENTURL + fname))
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
        subprocess.Popen(['jupyter', 'notebook', fname])

    def solution(self, label):
        """Open label.ipynb, and download if needed."""
        fname = '{}/solutions/{}.ipynb'.format(COURSEDIR, label)
        if not os.path.exists(fname):
            print('Downloading {}.'.format(SOLUTIONURL + fname))
            urllib.request.urlretrieve(SOLUTIONURL
                                       + '{}.ipynb'.format(label), fname)

        # Now open the notebook.
        subprocess.Popen(['jupyter', 'notebook', fname])

    def lecture(self, label):
        """Open label.ipynb, and download if needed."""
        fname = '{}/lectures/{}.ipynb'.format(COURSEDIR, label)
        if not os.path.exists(fname):
            print('Downloading {}.'.format(LECTUREURL + fname))
            urllib.request.urlretrieve(LECTUREURL
                                       + '{}.ipynb'.format(label), fname)

        # Now open the notebook.
        subprocess.Popen(['jupyter', 'notebook', fname])

# ** Turn it in
    def turn_in(self, label):
        """Turn in LABEL by email."""
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
            s.login(ANDREWID, getpass.getpass('Andrew password: '))
            s.send_message(msg)
            s.quit()

        print('{} submitted.'.format(fname))


# * Admin magic
def get_andrewids():
    """Return a list of andrew ids."""
    import csv

    with open('course/roster.csv') as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    return [x[8] for x in rows]



multipliers = collections.OrderedDict([('A++', 1),
                                       ('A+', 0.95),
                                       ('A', 0.9),
                                       ('A-', 0.85),
                                       ('A/B', 0.8),
                                       ('B+', 0.75),
                                       ('B', 0.7),
                                       ('B-', 0.65),
                                       ('B/C', 0.6),
                                       ('C+', 0.55),
                                       ('C', 0.5),
                                       ('C-', 0.45),
                                       ('C/D', 0.4),
                                       ('D+', 0.35),
                                       ('D', 0.3),
                                       ('D-', 0.25),
                                       ('D/R', 0.2),
                                       ('R+', 0.15),
                                       ('R', 0.1),
                                       ('R-', 0.05),
                                       ('R--', 0.0)])

rubrics = {'default': [['technical', 0.7],
                       ['presentation', 0.3]]}


@magics_class
class TechelaAdmin(Magics):
    """IPython Magics."""
    @magic_arguments()
    @argument('-c', '--collect', type=str, help='Collect an assignment')
    @argument('-s', '--summarize', type=str, help='Grade an assignment')
    @argument('-r', '--return-assignment', type=str,
              help='Return an assignment')
    @line_magic
    def ta(self, line):
        """IPython magic function to get and turn in assignments."""
        args = parse_argstring(self.ta, line)

        if args.collect:
            print('Collecting {}'.format(args.collect))
            self.collect(args.collect)

        elif args.return_assignment:
            print('Returning {}'.format(args.return_assignment))
            self.return_assignment(args.return_assignment)

    def collect(self, label):
        """Collect LABEL assignment.

        Collect means copy all the files matching {andrew-id}-label.ipynb
        from the submission directory to the label directory.

        You should run this in the root directory where the submissions folder
        is. It will create the label directory.

        """
        adir = 'assignments/{}/'.format(label)
        if not os.path.isdir(adir):
            os.makedirs(adir)

        for andrewid in get_andrewids():
            fname = 'submissions/{}-{}.ipynb'.format(andrewid, label)

            if os.path.exists(fname):
                shutil.move(fname, adir)
                print('Moved {} to {}'.format(fname, adir))
            else:
                print('No submission for {}'.format(andrewid))

    def return_assignment(self, label):
        """Return the graded files by email.

        This does not keep track of what has been sent, so it will send them
        all every time!

        """

        password = getpass.getpass('Andrew password: ')

        for andrewid in get_andrewids():
            # I am not sure we have to reauthenticate each time. But an earlier
            # version had s.quit outside the context manager and it caused an
            # error.
            with smtplib.SMTP_SSL('smtp.andrew.cmu.edu', port=465) as s:
                s.login(self.data['andrewid'], password)
                msg = MIMEMultipart()
                subject = '[{}] - {} has been graded'
                msg['Subject'] = subject.format(self.data['course'],
                                                label)
                msg['From'] = '{}@andrew.cmu.edu'.format(self.data['andrewid'])
                msg['To'] = '{}@andrew.cmu.edu'.format(andrewid)

                ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)

                fname = 'assignments/{}/{}-{}.ipynb'.format(label, andrewid, label)

                if not os.path.exists(fname):
                    print('{} not found. Continuing.'.format(fname))
                    continue

                with open(fname, 'rb') as fp:
                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(fp.read())
                    # Encode the payload using Base64
                    encoders.encode_base64(attachment)
                    # Set the filename parameter
                    attachment.add_header('Content-Disposition', 'attachment',
                                          filename=pdf)
                    msg.attach(attachment)

                s.send_message(msg)
                s.quit()
                print('{} returned.'.format(fname))
                # Pause so we don't get kicked out
                time.sleep(0.5)

        print('Done returning {}.'.format(label))

    # @line_magic
    # def grade(self, line):
    #     """A widget to add a grade based on the rubric in the notebook."""
    #     # First we have to get the rubric.
    #     # It is stored by name in metadata.org.RUBRIC

        
        
    #     # tech = input('technical: ').upper()
    #     # pres = input('presentation: ').upper()

    #     # if not (tech in multipliers and pres in multipliers):
    #     #     raise Exception('Invalid grade entered.')

    #     # grade = 0.7 * multipliers[tech] + 0.3 * multipliers[pres]

    #     # letter_grade = [(k, v) for k, v in multipliers.items() if v < grade][0][0]

    #     # s1 = 'IPython.notebook.metadata.grade.technical = "{}";'.format(tech)
    #     # s2 = 'IPython.notebook.metadata.grade.presentation = "{}";'.format(pres)
    #     # s3 = 'IPython.notebook.metadata.grade.overall = {};'.format(grade)

    #     # display_javascript('IPython.notebook.metadata.grade = {};', raw=True)
    #     # display_javascript(s1, raw=True)
    #     # display_javascript(s2, raw=True)
    #     # display_javascript(s3, raw=True)
    #     # display(Javascript('IPython.notebook.save_checkpoint();'))

    #     # return 'Overall grade: {0:1.3f} ({1})'.format(grade, letter_grade)

    # @line_magic
    # def comment(self, line):
    #     s = '<font color="red">{0}: {1}</font>'
    #     comment = input('Comment: ')
    #     return HTML(s.format(ANDREWID, comment))        


# * Register the extensions and magics

# In order to actually use these magics, you must register them with a
# running IPython.  This code must be placed in a file that is loaded once
# IPython is up and running:
ip = get_ipython()
# You can register the class itself without instantiating it.  IPython will
# call the default constructor on it.
ip.register_magics(Techela)
ip.register_magics(TechelaAdmin)
