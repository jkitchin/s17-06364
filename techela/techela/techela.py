# This code can be put in any Python module, it does not require IPython
# itself to be running already.  It only creates the magics subclass but
# doesn't instantiate it yet.
import getpass
import json
import os
import shutil
import smtplib
import subprocess
import sys
import urllib.request
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from nbconvert import LatexExporter
from jinja2 import Environment, PackageLoader

from IPython import get_ipython
from IPython.core.magic import (Magics, magics_class, line_magic)
from IPython.core.magic_arguments import (argument, magic_arguments,
                                          parse_argstring)


def open_file(filename):
    '''Cross-platform open file function.'''
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])

# * Converting to gradable PDF files


def convert_ipynb_pdf(nbfile, delete_files=True):
    '''Convert NBFILE into a gradable pdf.

    This is done via LaTeX export, and pdflatex.
    The resulting pdf has "-gradable" appended to it.

    '''

    template = os.path.join(os.path.dirname(__file__),
                            'templates/nbconvert_ipynb.tplx')

    latex_exporter = LatexExporter()
    latex_exporter.template_file = os.path.relpath(template)

    (body, _) = latex_exporter.from_filename(nbfile)

    base, ext = os.path.splitext(nbfile)
    texfile = base + '-gradable.tex'
    pdffile = base + '-gradable.pdf'

    if os.path.exists(pdffile):
        return pdffile

    with open(texfile, 'w') as f:
        f.write(body)

    CWD = os.getcwd()
    basedir, f = os.path.split(texfile)
    os.chdir(basedir)
    try:
        print('Compiling {} (exists = {})'.format(f, os.path.exists(f)))
        subprocess.run(['latexmk', '-pdf', '-f',  f], stdout=subprocess.PIPE)

        if delete_files:
            nbase, ext = os.path.splitext(f)
            for ext in ['aux', 'log', 'out', 'tex', 'fls', 'fdb_latexmk']:
                fname = nbase + '.' + ext
                if os.path.exists(fname):
                    os.unlink(fname)
            for f in ['md.djs', 'mydljs.djs']:
                if os.path.exists(f):
                    os.unlink(f)
    finally:
        os.chdir(CWD)

    return pdffile


def convert_pdf_to_gradable(pdf, delete_files=True):
    '''Convert PDF to a gradable pdf by wrapping it in a LaTeX file.'''

    env = Environment(loader=PackageLoader('s17_06364', 'templates'),
                      variable_start_string='((',
                      variable_end_string='))')

    template = env.get_template('gradable_pdf.tplx')

    base, ext = os.path.splitext(pdf)
    texfile = base + '-gradable.tex'
    pdffile = base + '-gradable.pdf'

    if os.path.exists(pdffile):
        return pdffile

    with open(texfile, 'w') as f:
        basedir, pdffile = os.path.split(pdf)
        f.write(template.render(pdffile=pdffile))

    CWD = os.getcwd()
    basedir, f = os.path.split(texfile)
    os.chdir(basedir)
    try:
        print('Compiling {} (exists = {})'.format(f, os.path.exists(f)))
        subprocess.run(['latexmk', '-pdf', '-f',  f], stdout=subprocess.PIPE)

        if delete_files:
            nbase, ext = os.path.splitext(f)
            for ext in ['aux', 'log', 'out', 'tex', 'fls', 'fdb_latexmk']:
                fname = nbase + '.' + ext
                if os.path.exists(fname):
                    os.unlink(fname)
            for f in ['md.djs', 'mydljs.djs']:
                if os.path.exists(f):
                    os.unlink(f)
    finally:
        os.chdir(CWD)

    return pdffile


# * User magic
@magics_class
class Techela(Magics):
    '''IPython Magics for students.'''

    @magic_arguments()
    @argument('-s', '--setup', action='store_true', help='Setup techela.')
    @argument('-o', '--open', type=str, help='Open an assignment.')
    @argument('-t', '--turn-in', type=str, help='Turn in an assignment.')
    @line_magic
    def techela(self, line):
        '''IPython magic function to get and turn in assignments.'''

        if os.path.exists('techela.json'):
            with open('techela.json', 'r') as f:
                self.data = json.loads(f.read())
        else:
            self.data = self.setup()

        args = parse_argstring(self.techela, line)

        if args.setup:
            self.setup()
        elif args.open:
            self.open(args.open)
        elif args.turn_in:
            self.turn_in(args.turn_in)

    def setup(self):
        '''Setup the techela.json file.'''
        data = {}
        data['andrewid'] = input('Andrew ID: ')
        data['course'] = 's17-06364'
        data['submit_email'] = 'test.99vf772x4zplbvuo@u.box.com'
        data['baseurl'] = 'https://raw.githubusercontent.com/jkitchin/f16-06625/master/'

        with open('techela.json', 'w') as f:
            f.write(json.dumps(data))
        return data

    def open(self, label):
        '''open label.ipynb, and download if needed.'''
        print('Opening {}'.format(label))
        fname = '{}.ipynb'.format(label)
        if (not os.path.exists(fname)):
            BASEURL = self.data['baseurl']
            print('Downloading {}.'.format(BASEURL + fname))
            urllib.request.urlretrieve(BASEURL + fname, fname)

        subprocess.Popen(['jupyter', 'notebook', fname])

# ** Turn it in
    def turn_in(self, label):
        '''Turn in LABEL by email.'''
        # Create the container (outer) email message.
        msg = MIMEMultipart()
        subject = '[{}] - Turning in {}'
        msg['Subject'] = subject.format(self.data['course'], label)
        msg['From'] = '{}@andrew.cmu.edu'.format(self.data['andrewid'])
        msg['To'] = self.data['submit_email']

        ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)

        basename = '{}-{}'.format(self.data['andrewid'], label)
        if os.path.exists(basename + '.pdf'):
            fname = basename + '.pdf'
        elif os.path.exists(basename + '.ipynb'):
            fname = basename + '.ipynb'
        else:
            raise Exception('{} not found.'.format(basename))

        with open(fname, 'rb') as fp:
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(fp.read())
            # Encode the payload using Base64
            encoders.encode_base64(attachment)
            # Set the filename parameter
            attachment.add_header('Content-Disposition', 'attachment',
                                  filename=fname)
            msg.attach(attachment)

        with smtplib.SMTP_SSL('smtp.andrew.cmu.edu', port=465) as s:
            s.login(self.data['andrewid'], getpass('Andrew password: '))
            s.send_message(msg)
            s.quit()

        print('{} submitted.'.format(label))


# * Admin magic
def get_andrewids():
    '''Return a list of andrew ids.

    TODO: get from roster'''

    return ['jkitchin']


@magics_class
class TechelaAdmin(Magics):
    '''IPython Magics.'''
    @magic_arguments()
    @argument('-s', '--setup', action='store_true', help='Setup techela-admin')
    @argument('-c', '--collect', type=str, help='Collect an assignment')
    @argument('-p', '--prepare', type=str, help='Prepare an assignment')
    @argument('-g', '--grade', type=str, help='Grade an assignment')
    @argument('-r', '--return-assignment', type=str,
              help='Return an assignment')
    @line_magic
    def techela_admin(self, line):
        '''IPython magic function to get and turn in assignments.'''
        args = parse_argstring(self.techela_admin, line)

        if os.path.exists('techela-admin.json'):
            with open('techela-admin.json', 'r') as f:
                self.data = json.loads(f.read())
        else:
            self.data = self.setup()

        if args.setup:
            self.setup()

        elif args.collect:
            print('Collecting {}'.format(args.collect))
            self.collect(args.collect)

        elif args.prepare:
            print('Preparing {}'.format(args.prepare))
            self.prepare(args.prepare)

        elif args.grade:
            print('Grading {}'.format(args.grade))
            self.grade(args.grade)

        elif args.return_assignment:
            print('Returning {}'.format(args.return_assignment))
            self.return_assignment(args.return_assignment)

    def setup(self):
        '''make sure we are setup.'''
        data = {}
        data['andrewid'] = input('Andrew ID: ').strip()
        data['course'] = input('Course id: ').strip()

        with open('techela-admin.json', 'w') as f:
            f.write(json.dumps(data))
        return data


# ** Collect
    def collect(self, label):
        '''Collect LABEL assignment.

        Collect means copy all the files matching {andrew-id}-label.(ipynb|pdf)
        from the submission directory to the label directory.

        You should run this in the root directory where the submissions folder
        is. It will create the label directory.

        '''
        if not os.path.isdir(label):
            os.makedirs(label)

        for andrewid in get_andrewids():
            f1 = 'submissions/{}-{}.ipynb'.format(andrewid, label)
            f2 = 'submissions/{}-{}.pdf'.format(andrewid, label)

            if os.path.exists(f1):
                fname = f1
            elif os.path.exists(f2):
                fname = f2
            else:
                fname = None

            if fname:
                shutil.copy(fname, label)
                print('Copied {} to {}'.format(fname, label))
            else:
                print('No submission for {}'.format(andrewid))

# ** Prepare
    def prepare(self, label):
        '''Prepare the files for grading.

        '''
        if not os.path.isdir(label):
            self.collect(label)

        files_to_grade = []

        for andrewid in get_andrewids():
            f1 = '{}/{}-{}.ipynb'.format(label, andrewid, label)
            f2 = '{}/{}-{}.pdf'.format(label, andrewid, label)

            if os.path.exists(f1):
                files_to_grade += [convert_ipynb_pdf(f1)]
            elif os.path.exists(f2):
                files_to_grade += [convert_pdf_to_gradable(f2)]

        return files_to_grade

# ** Grade
    def grade(self, label):
        '''Open all the files for grading.

        Eventually, this may become a Flask app.
        '''

        if not os.path.isdir(label):
            self.prepare(label)

        for andrewid in get_andrewids():
            f = '{label}/{andrewid}-{label}-gradable.pdf'
            if os.path.exists(f.format(label=label,
                                       andrewid=andrewid)):
                open_file(f.format(label=label,
                                   andrewid=andrewid))

# ** Return
    def return_assignment(self, label):
        '''Return the graded files by email.'''

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

                pdf = '{}/{}-{}-gradable.pdf'.format(label, andrewid, label)

                if not os.path.exists(pdf):
                    print('{} not found. Continuing.'.format(pdf))
                    continue

                with open(pdf, 'rb') as fp:
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
                print('{} returned.'.format(pdf))

        print('Done returning {}.'.format(label))


# * Register the extensions and magics

# In order to actually use these magics, you must register them with a
# running IPython.  This code must be placed in a file that is loaded once
# IPython is up and running:
ip = get_ipython()
# You can register the class itself without instantiating it.  IPython will
# call the default constructor on it.
ip.register_magics(Techela)
ip.register_magics(TechelaAdmin)
