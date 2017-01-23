# This code can be put in any Python module, it does not require IPython
# itself to be running already.  It only creates the magics subclass but
# doesn't instantiate it yet.
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)

from IPython.core.magic_arguments import (argument, magic_arguments,
    parse_argstring)

from IPython import get_ipython

# Import smtplib for the actual sending function
import smtplib

# Here are the email package modules we'll need
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import mimetypes

from getpass import getpass
import json
import os
import subprocess
import urllib.request

COURSE = 's17-06364'
CONFIG = os.path.expanduser("~/.techela-{0}".format(COURSE))
BOX_EMAIL = 'submiss.uj1v37qz3m0gpzsu@u.box.com'

BASEURL = 'https://raw.githubusercontent.com/jkitchin/s17-06364/master/'

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

# The class MUST call this class decorator at creation time
@magics_class
class Techela(Magics):

    @line_magic
    def submit(self, label):
        '''Submit the assignment designated by LABEL.

        The function looks for a file with a name of ANDREWID-LABEL and an
        extension of either .pdf or.ipynb. An exception is raised if one is not
        found.

        '''

        # Create the container (outer) email message.
        msg = MIMEMultipart()
        msg['Subject'] = '[{}] - Turning in {}'.format(COURSE, label)
        msg['From'] = '"{0}" <{1}@andrew.cmu.edu>'.format(ANDREWID)
        msg['To'] = BOX_EMAIL

        ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)

        basename = '{}-{}'.format(ANDREWID, label)
        if os.path.exists(basename + '.pdf'):
            fname = basename + '.pdf'
        elif os.path.exists(basename + '.ipynb'):
            fname = basename + '.ipynb'
        else:
            raise Exception('No file with basename of {} found.'.format(basename))

        with open(fname, 'rb') as fp:
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(fp.read())
            # Encode the payload using Base64
            encoders.encode_base64(attachment)
            # Set the filename parameter
            attachment.add_header('Content-Disposition', 'attachment', filename=fname)
            msg.attach(attachment)

        with smtplib.SMTP_SSL('smtp.andrew.cmu.edu', port=465) as s:
            s.login(ANDREWID, getpass('Andrew password: '))
            s.send_message(msg)
            s.quit()

        print('{} submitted.'.format(label))

    @line_magic
    def open(self, label):
        '''Open a label.
        You can force it to reload the file by adding a truthy value after the
        label in the line, separated by at least one space.

        '''
        f = label.split(' ')
        label = f[0]
        if len(f) > 1:
            reload = f[1]
        else:
            reload = False
 
        fname = '{}.ipynb'.format(label)
        if (not os.path.exists(fname)) or reload:
            print('Downloading {}.'.format(BASEURL + fname))
            urllib.request.urlretrieve(BASEURL + fname, fname)

        p = subprocess.Popen(['jupyter', 'notebook', fname])
        return p

# In order to actually use these magics, you must register them with a
# running IPython.  This code must be placed in a file that is loaded once
# IPython is up and running:
ip = get_ipython()
# You can register the class itself without instantiating it.  IPython will
# call the default constructor on it.
ip.register_magics(Techela)

