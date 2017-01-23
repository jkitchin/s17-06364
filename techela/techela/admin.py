import getpass
import json
import os
import shutil
import smtplib
import subprocess
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from nbconvert import LatexExporter
from jinja2 import Environment, PackageLoader

from IPython.core import magic_arguments
from IPython.core.magic import (Magics, magics_class, line_magic) 

from IPython import get_ipython
import collections
from IPython.display import display, Javascript
from IPython.display import display_javascript
from IPython.core.display import HTML

from . import CONFIG

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


def open_file(filename):
    '''Cross-platform open file function.'''
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])


def convert_ipynb_pdf(nbfile, delete_files=True):
    '''Convert NBFILE into a gradable pdf.

    This is done via LaTeX export, and pdflatex.
    The resulting pdf has "-gradable" appended to it.

    '''

    t = os.path.join(os.path.dirname(__file__),
                     'templates/nbconvert_ipynb.tplx')

    latex_exporter = LatexExporter()
    latex_exporter.template_file = os.path.relpath(t)

    (body, _) = latex_exporter.from_filename(nbfile)

    base, ext = os.path.splitext(nbfile)
    texfile = base + '-gradable.tex'

    with open(texfile, 'w') as f:
        f.write(body)

    CWD = os.getcwd()
    basedir, f = os.path.split(texfile)
    os.chdir(basedir)
    try:
        print('Compiling {} (exists = {})'.format(f, os.path.exists(f)))
        subprocess.run(['pdflatex', f], stdout=subprocess.PIPE)
        subprocess.run(['pdflatex', f], stdout=subprocess.PIPE)
        subprocess.run(['pdflatex', f], stdout=subprocess.PIPE)

        if delete_files:
            nbase, ext = os.path.splitext(f)
            for ext in ['aux', 'log', 'out', 'tex']:
                fname = nbase + '.' + ext
                print(fname)
                if os.path.exists(fname):
                    os.unlink(fname)
            for f in ['md.djs', 'mydljs.djs']:
                if os.path.exists(f):
                    os.unlink(f)
    finally:
        os.chdir(CWD)

    return base + '-gradable.pdf'


def convert_pdf_to_gradable(pdf, delete_files=True):
    '''Convert PDF to a gradable pdf by wrapping it in a LaTeX file.'''

    env = Environment(loader=PackageLoader('s17_06364', 'templates'),
                      variable_start_string='((',
                      variable_end_string='))')

    template = env.get_template('gradable_pdf.tplx')

    base, ext = os.path.splitext(pdf)
    texfile = base + '-gradable.tex'

    with open(texfile, 'w') as f:
        basedir, pdffile = os.path.split(pdf)
        f.write(template.render(pdffile=pdffile))

    CWD = os.getcwd()
    basedir, f = os.path.split(texfile)
    os.chdir(basedir)
    try:
        print('Compiling {} (exists = {})'.format(f, os.path.exists(f)))
        subprocess.run(['pdflatex', f], stdout=subprocess.PIPE)
        subprocess.run(['pdflatex', f], stdout=subprocess.PIPE)
        subprocess.run(['pdflatex', f], stdout=subprocess.PIPE)

        if delete_files:
            nbase, ext = os.path.splitext(f)
            for ext in ['aux', 'log', 'out', 'tex']:
                fname = nbase + '.' + ext
                if os.path.exists(fname):
                    os.unlink(fname)
            for f in ['md.djs', 'mydljs.djs']:
                if os.path.exists(f):
                    os.unlink(f)
    finally:
        os.chdir(CWD)

    return base + '-gradable.pdf'

#  Admin magic


def get_andrewids():
    '''Return a list of andrew ids.

    TODO: get from roster'''

    return ['jkitchin']


# The class MUST call this class decorator at creation time
@magics_class
class TechelaAdmin(Magics):
    '''TechelaAdmin magics for IPython.'''
    @line_magic
    def setup(self, line):
        '''make sure we are setup.'''
        if not os.path.exists('techela.json'):
            data = {}
            data['username'] = input('Andrew ID: ').strip()
            data['course'] = input('Course id: ').strip()

            with open('techela.json', 'w') as f:
                f.write(json.dumps(data))

    @line_magic
    def collect(self, line):
        '''
        Collect means copy all the files matching {andrew-id}-label.(ipynb|pdf)
        from the submission directory to the label directory.

        You should run this in the root directory where the submissions folder
        is (i.e. not in the submissions folder, but one up. It will create the
        label directory.

        '''
        label = line.strip()
        assignment_dir = 'assignments/{}'.format(label)
        if not os.path.isdir(assignment_dir):
            os.makedirs(assignment_dir)

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
                shutil.copy(fname, assignment_dir)
                print('Copied {} to {}'.format(fname, assignment_dir))
            else:
                print('No submission for {}'.format(andrewid))

    @line_magic
    def prepare(self, line):
        '''Prepare the files for grading.
        This collects the files, and converts them to a gradable pdf.

        '''
        label = line.strip()
        assignment_dir = 'assignments/{}'.format(label)
        if not os.path.isdir(assignment_dir):
            self.collect(label)

        files_to_grade = []

        for andrewid in get_andrewids():
            f1 = '{}/{}-{}.ipynb'.format(assignment_dir, andrewid, label)
            f2 = '{}/{}-{}.pdf'.format(assignment_dir, andrewid, label)

            if os.path.exists(f1):
                files_to_grade += [convert_ipynb_pdf(f1)]
            elif os.path.exists(f2):
                files_to_grade += [convert_pdf_to_gradable(f2)]

        return files_to_grade

    @line_magic
    def open_for_grading(self, line):
        '''Open all the files for grading.

        Eventually, this may become a Flask app with links to open the files.
        '''

        label = line.strip()
        assignment_dir = 'assignments/{}'.format(label)
        if not os.path.isdir(assignment_dir):
            self.prepare(label)

        for andrewid in get_andrewids():
            f = '{assignment_dir}/{andrewid}-{label}-gradable.pdf'
            if os.path.exists(f.format(assignment_dir=assignment_dir,
                                       label=label,
                                       andrewid=andrewid)):
                open_file(f.format(assignment_dir=assignment_dir,
                                   label=label,
                                   andrewid=andrewid))

    @line_magic
    def return_assignment(self, line):
        '''Return the graded files by email.'''

        with open('techela.json') as f:
            data = json.loads(f.read())

        password = getpass.getpass('Andrew password: ')

        label = line.strip()
        assignment_dir = 'assignments/{}'.format(label)

        for andrewid in get_andrewids():
            # I am not sure we have to reauthenticate each time. But an earlier
            # version had s.quit outside the context manager and it caused an
            # error.
            with smtplib.SMTP_SSL('smtp.andrew.cmu.edu', port=465) as s:
                s.login(data['username'], password)
                msg = MIMEMultipart()
                subject = '[{}] - {} has been graded'.format(data['course'],
                                                             label)
                msg['Subject'] = subject
                msg['From'] = '{}@andrew.cmu.edu'.format(data['username'])
                msg['To'] = '{}@andrew.cmu.edu'.format(andrewid)

                ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)

                pdf = '{}/{}-{}-gradable.pdf'.format(assignment_dir, andrewid, label)

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

    @line_magic
    def grade(self, line):
        """A widget to add a grade."""
        tech = input('technical: ').upper()
        pres = input('presentation: ').upper()

        if not (tech in multipliers and pres in multipliers):
            raise Exception('Invalid grade entered.')

        grade = 0.7 * multipliers[tech] + 0.3 * multipliers[pres]

        letter_grade = [(k, v) for k, v in multipliers.items() if v < grade][0][0]

        s1 = 'IPython.notebook.metadata.grade.technical = "{}";'.format(tech)
        s2 = 'IPython.notebook.metadata.grade.presentation = "{}";'.format(pres)
        s3 = 'IPython.notebook.metadata.grade.overall = {};'.format(grade)

        display_javascript('IPython.notebook.metadata.grade = {};', raw=True)
        display_javascript(s1, raw=True)
        display_javascript(s2, raw=True)
        display_javascript(s3, raw=True)
        display(Javascript('IPython.notebook.save_checkpoint();'))

        return 'Overall grade: {0:1.3f} ({1})'.format(grade, letter_grade)

    @line_magic
    def comment(self, line):
        s = '<font color="red">{0}: {1}</font>'
        comment = input('Comment: ')
        return HTML(s.format(ANDREWID, comment))


# In order to actually use these magics, you must register them with a
# running IPython.  This code must be placed in a file that is loaded once
# IPython is up and running:

ip = get_ipython()
# You can register the class itself without instantiating it.  IPython will
# call the default constructor on it.
ip.register_magics(TechelaAdmin)
