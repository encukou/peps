#!/usr/bin/env python
"""
Convert PEPs to (X)HTML fragments for Pyramid - courtesy of /F

Usage: %(PROGRAM)s [options] [<peps> ...]

Options:

-d <DIR>, --destdir <DIR>
    Specify the base destination directory for Pyramid files.
    Default: %(SERVER_DEST_DIR_BASE)s

-f, --force
    Force the rebuilding of output files, regardless of modification times.

-k, --keep-going
    Continue building past errors if possible.

-q, --quiet
    Turn off verbose messages.

-h, --help
    Print this help message and exit.

The optional arguments ``peps`` are either pep numbers or .txt files.
"""

import sys
import os
import codecs
import re
import cgi
import glob
import getopt
import errno
import random
import time
import shutil

REQUIRES = {'python': '2.2',
            'docutils': '0.5'}
PROGRAM = sys.argv[0]
SERVER_DEST_DIR_BASE = (
    '/data/ftp.python.org/pub/beta.python.org/build/data/dev/peps')
RFCURL = 'http://www.faqs.org/rfcs/rfc%d.html'
PEPCVSURL = 'http://hg.python.org/peps/file/tip/pep-%04d.txt'
PEPDIRURL = '/dev/peps/'
PEPURL = PEPDIRURL + 'pep-%04d'
PEPANCHOR = '<a href="' + PEPURL + '">%i</a>'


LOCALVARS = "Local Variables:"

COMMENT = """<!--
This HTML is auto-generated.  DO NOT EDIT THIS FILE!  If you are writing a new
PEP, see http://www.python.org/dev/peps/pep-0001 for instructions and links
to templates.  DO NOT USE THIS HTML FILE AS YOUR TEMPLATE!
-->"""

# The generated HTML doesn't validate -- you cannot use <hr> and <h3> inside
# <pre> tags.  But if I change that, the result doesn't look very nice...

fixpat = re.compile("((https?|ftp):[-_a-zA-Z0-9/.+~:?#$=&,]+)|(pep-\d+(.txt)?)|"
                    "(RFC[- ]?(?P<rfcnum>\d+))|"
                    "(PEP\s+(?P<pepnum>\d+))|"
                    ".")

CONTENT_HTML = """\
<n:invisible n:data="content" n:render="mapping">
<div id="breadcrumb" n:data="breadcrumb" n:render="breadcrumb" />
<n:slot name="text"></n:slot>
</n:invisible>
"""

CONTENT_YML = """\
--- !fragment
# Type of template to use
template: content.html

# The data to pass to the template
local:
    content:
        breadcrumb: !breadcrumb nav.yml nav
        text: !htmlfile body.html
"""

INDEX_YML = """\
--- !fragment
template: index.html
# The data to pass to the template
local:
  title: "%s"
  content: !fragment content.yml
"""

EMPTYSTRING = ''
SPACE = ' '
COMMASPACE = ', '


class Settings:

    # defaults:
    verbose = True
    keep_going = False
    force_rebuild = False
    dest_dir_base = SERVER_DEST_DIR_BASE

settings = Settings()



def usage(code, msg=''):
    """Print usage message and exit.  Uses stderr if code != 0."""
    if code == 0:
        out = sys.stdout
    else:
        out = sys.stderr
    print >> out, __doc__ % globals()
    if msg:
        print >> out, msg
    sys.exit(code)



def fixanchor(current, match):
    text = match.group(0)
    link = None
    if (text.startswith('http:') or text.startswith('https:')
        or text.startswith('ftp:')):
        # Strip off trailing punctuation.  Pattern taken from faqwiz.
        ltext = list(text)
        while ltext:
            c = ltext.pop()
            if c not in '();:,.?\'"<>':
                ltext.append(c)
                break
        link = EMPTYSTRING.join(ltext)
    elif text.endswith('.txt') and text <> current:
        link = PEPDIRURL + os.path.splitext(text)[0] + '/' + text 
    elif text.startswith('pep-') and text <> current:
        link = os.path.splitext(text)[0] + ".html"
    elif text.startswith('PEP'):
        pepnum = int(match.group('pepnum'))
        link = PEPURL % pepnum
    elif text.startswith('RFC'):
        rfcnum = int(match.group('rfcnum'))
        link = RFCURL % rfcnum
    if link:
        return '<a href="%s">%s</a>' % (cgi.escape(link), cgi.escape(text))
    return cgi.escape(match.group(0)) # really slow, but it works...



NON_MASKED_EMAILS = [
    'peps@python.org',
    'python-list@python.org',
    'python-dev@python.org',
    ]

def fixemail(address, pepno):
    if address.lower() in NON_MASKED_EMAILS:
        # return hyperlinked version of email address
        return linkemail(address, pepno)
    else:
        # return masked version of email address
        parts = address.split('@', 1)
        return '%s&#32;&#97;t&#32;%s' % (parts[0], parts[1])


def linkemail(address, pepno):
    parts = address.split('@', 1)
    return ('<a href="mailto:%s&#64;%s?subject=PEP%%20%s">'
            '%s&#32;&#97;t&#32;%s</a>'
            % (parts[0], parts[1], pepno, parts[0], parts[1]))


def fixfile(inpath, input_lines, outfile):
    from email.Utils import parseaddr
    basename = os.path.basename(inpath)
    infile = iter(input_lines)
    # head
    header = []
    pep = ""
    title = ""
    for line in infile:
        if not line.strip():
            break
        if line[0].strip():
            if ":" not in line:
                break
            key, value = line.split(":", 1)
            value = value.strip()
            header.append((key, value))
        else:
            # continuation line
            key, value = header[-1]
            value = value + line
            header[-1] = key, value
        if key.lower() == "title":
            title = value
        elif key.lower() == "pep":
            pep = value

    if pep:
        title = "PEP " + pep + " -- " + title
    r = random.choice(range(64))
    print >> outfile, COMMENT
    print >> outfile, '<div class="header">\n<table border="0" class="rfc2822">'
    for k, v in header:
        if k.lower() in ('author', 'discussions-to'):
            mailtos = []
            for part in re.split(',\s*', v):
                if '@' in part:
                    realname, addr = parseaddr(part)
                    if k.lower() == 'discussions-to':
                        m = linkemail(addr, pep)
                    else:
                        m = fixemail(addr, pep)
                    mailtos.append('%s &lt;%s&gt;' % (realname, m))
                elif part.startswith('http:'):
                    mailtos.append(
                        '<a href="%s">%s</a>' % (part, part))
                else:
                    mailtos.append(part)
            v = COMMASPACE.join(mailtos)
        elif k.lower() in ('replaces', 'replaced-by', 'requires'):
            otherpeps = ''
            for otherpep in re.split(',?\s+', v):
                otherpep = int(otherpep)
                otherpeps += PEPANCHOR % (otherpep, otherpep)
            v = otherpeps
        elif k.lower() in ('last-modified',):
            date = v or time.strftime('%Y-%m-%d',
                                      time.localtime(os.stat(inpath)[8]))
            if date.startswith('$' 'Date: ') and date.endswith(' $'):
                date = date[6:-2]
            try:
                url = PEPCVSURL % int(pep)
                v = '<a href="%s">%s</a> ' % (url, cgi.escape(date))
            except ValueError, error:
                v = date
        elif k.lower() == 'content-type':
            url = PEPURL % 9
            pep_type = v or 'text/plain'
            v = '<a href="%s">%s</a> ' % (url, cgi.escape(pep_type))
        elif k.lower() == 'version':
            if v.startswith('$' 'Revision: ') and v.endswith(' $'):
                v = cgi.escape(v[11:-2])
        else:
            v = cgi.escape(v)
        print >> outfile, ('  <tr><th class="field-name">%s:&nbsp;</th>'
                           '<td>%s</td></tr>' % (cgi.escape(k), v))
    print >> outfile, '</table>'
    print >> outfile, '</div>'
    need_pre = 1
    for line in infile:
        if line[0] == '\f':
            continue
        if line.strip() == LOCALVARS:
            break
        if line[0].strip():
            if not need_pre:
                print >> outfile, '</pre>'
            print >> outfile, '<h3>%s</h3>' % line.strip()
            need_pre = 1
        elif not line.strip() and need_pre:
            continue
        else:
            # PEP 0 has some special treatment
            if basename == 'pep-0000.txt':
                parts = line.split()
                if len(parts) > 1 and re.match(r'\s*\d{1,4}', parts[1]):
                    # This is a PEP summary line, which we need to hyperlink
                    url = PEPURL % int(parts[1])
                    if need_pre:
                        print >> outfile, '<pre>'
                        need_pre = 0
                    print >> outfile, re.sub(
                        parts[1],
                        '<a href="/dev/peps/pep-%04d/">%s</a>' % (int(parts[1]),
                            parts[1]), line, 1),
                    continue
                elif parts and '@' in parts[-1]:
                    # This is a pep email address line, so filter it.
                    url = fixemail(parts[-1], pep)
                    if need_pre:
                        print >> outfile, '<pre>'
                        need_pre = 0
                    print >> outfile, re.sub(
                        parts[-1], url, line, 1),
                    continue
            line = fixpat.sub(lambda x, c=inpath: fixanchor(c, x), line)
            if need_pre:
                print >> outfile, '<pre>'
                need_pre = 0
            outfile.write(line)
    if not need_pre:
        print >> outfile, '</pre>'
    return title


docutils_settings = None
"""Runtime settings object used by Docutils.  Can be set by the client
application when this module is imported."""

def fix_rst_pep(inpath, input_lines, outfile):
    from docutils import core
    from docutils.transforms.peps import Headers
    Headers.pep_cvs_url = PEPCVSURL
    parts = core.publish_parts(
        source=''.join(input_lines),
        source_path=inpath,
        destination_path=outfile.name,
        reader_name='pep',
        parser_name='restructuredtext',
        writer_name='pep_html',
        settings=docutils_settings,
        # Allow Docutils traceback if there's an exception:
        settings_overrides={'traceback': 1})
    outfile.write(parts['whole'])
    title = 'PEP %s -- %s' % (parts['pepnum'], parts['title'][0])
    return title


def get_pep_type(input_lines):
    """
    Return the Content-Type of the input.  "text/plain" is the default.
    Return ``None`` if the input is not a PEP.
    """
    pep_type = None
    for line in input_lines:
        line = line.rstrip().lower()
        if not line:
            # End of the RFC 2822 header (first blank line).
            break
        elif line.startswith('content-type: '):
            pep_type = line.split()[1] or 'text/plain'
            break
        elif line.startswith('pep: '):
            # Default PEP type, used if no explicit content-type specified:
            pep_type = 'text/plain'
    return pep_type


def get_input_lines(inpath):
    try:
        infile = codecs.open(inpath, 'r', 'utf-8')
    except IOError, e:
        if e.errno <> errno.ENOENT: raise
        print >> sys.stderr, 'Error: Skipping missing PEP file:', e.filename
        sys.stderr.flush()
        return None, None
    lines = infile.read().splitlines(1) # handles x-platform line endings
    infile.close()
    return lines


def find_pep(pep_str):
    """Find the .txt file indicated by a cmd line argument"""
    if os.path.exists(pep_str):
        return pep_str
    num = int(pep_str)
    return "pep-%04d.txt" % num

def make_html(inpath):
    input_lines = get_input_lines(inpath)
    pep_type = get_pep_type(input_lines)
    if pep_type is None:
        print >> sys.stderr, 'Error: Input file %s is not a PEP.' % inpath
        sys.stdout.flush()
        return None
    elif not PEP_TYPE_DISPATCH.has_key(pep_type):
        print >> sys.stderr, ('Error: Unknown PEP type for input file %s: %s'
                              % (inpath, pep_type))
        sys.stdout.flush()
        return None
    elif PEP_TYPE_DISPATCH[pep_type] == None:
        pep_type_error(inpath, pep_type)
        return None
    destDir, needSvn, pepnum = set_up_pyramid(inpath)
    outpath = os.path.join(destDir, 'body.html')
    if ( not settings.force_rebuild
         and (os.path.exists(outpath) 
              and os.stat(inpath).st_mtime <= os.stat(outpath).st_mtime)):
        if settings.verbose:
            print "Skipping %s (outfile up to date)"%(inpath)
        return
    if settings.verbose:
        print inpath, "(%s)" % pep_type, "->", outpath
        sys.stdout.flush()
    outfile = codecs.open(outpath, "w", "utf-8")
    title = PEP_TYPE_DISPATCH[pep_type](inpath, input_lines, outfile)
    outfile.close()
    os.chmod(outfile.name, 0664)
    write_pyramid_index(destDir, title)
    # for PEP 0, copy body to parent directory as well
    if pepnum == '0000':
        shutil.copyfile(outpath, os.path.join(destDir, '..', 'body.html'))
    copy_aux_files(inpath, destDir)
    return outpath

def set_up_pyramid(inpath):
    m = re.search(r'pep-(\d+)\.', inpath)
    if not m:
        print >>sys.stderr, "Can't find PEP number in file name."
        sys.exit(1)
    pepnum = m.group(1)
    destDir = os.path.join(settings.dest_dir_base, 'pep-%s' % pepnum)

    needSvn = 0
    if not os.path.exists(destDir):
        needSvn = 1
        os.makedirs(destDir)

        #  write content.html
        foofilename = os.path.join(destDir, 'content.html')
        fp = codecs.open(foofilename, 'w', 'utf-8')
        fp.write(CONTENT_HTML)
        fp.close()
        os.chmod(foofilename, 0664)

        #  write content.yml
        foofilename = os.path.join(destDir, 'content.yml')
        fp = codecs.open(foofilename, 'w', 'utf-8')
        fp.write(CONTENT_YML)
        os.chmod(foofilename, 0664)
    return destDir, needSvn, pepnum

def write_pyramid_index(destDir, title):
    filename = os.path.join(destDir, 'index.yml')
    fp = codecs.open(filename, 'w', 'utf-8')
    title = title.replace('\\', '\\\\') # Escape existing backslashes
    fp.write(INDEX_YML % title.replace('"', '\\"'))
    fp.close()
    os.chmod(filename, 0664)

def copy_aux_files(pep_path, dest_dir):
    """
    Copy auxiliary files whose names match 'pep-XXXX-*.*'.
    """
    dirname, pepname = os.path.split(pep_path)
    base, ext = os.path.splitext(pepname)
    files = glob.glob(os.path.join(dirname, base) + '-*.*')
    for path in files:
        filename = os.path.basename(path)
        dest_path = os.path.join(dest_dir, filename)
        print '%s -> %s' % (path, dest_path)
        shutil.copy(path, dest_path)



PEP_TYPE_DISPATCH = {'text/plain': fixfile,
                     'text/x-rst': fix_rst_pep}
PEP_TYPE_MESSAGES = {}

def check_requirements():
    # Check Python:
    try:
        from email.Utils import parseaddr
    except ImportError:
        PEP_TYPE_DISPATCH['text/plain'] = None
        PEP_TYPE_MESSAGES['text/plain'] = (
            'Python %s or better required for "%%(pep_type)s" PEP '
            'processing; %s present (%%(inpath)s).'
            % (REQUIRES['python'], sys.version.split()[0]))
    # Check Docutils:
    try:
        import docutils
    except ImportError:
        PEP_TYPE_DISPATCH['text/x-rst'] = None
        PEP_TYPE_MESSAGES['text/x-rst'] = (
            'Docutils not present for "%(pep_type)s" PEP file %(inpath)s.  '
            'See README.txt for installation.')
    else:
        installed = [int(part) for part in docutils.__version__.split('.')]
        required = [int(part) for part in REQUIRES['docutils'].split('.')]
        if installed < required:
            PEP_TYPE_DISPATCH['text/x-rst'] = None
            PEP_TYPE_MESSAGES['text/x-rst'] = (
                'Docutils must be reinstalled for "%%(pep_type)s" PEP '
                'processing (%%(inpath)s).  Version %s or better required; '
                '%s present.  See README.txt for installation.'
                % (REQUIRES['docutils'], docutils.__version__))

def pep_type_error(inpath, pep_type):
    print >> sys.stderr, 'Error: ' + PEP_TYPE_MESSAGES[pep_type] % locals()
    sys.stdout.flush()


def build_peps(args=None):
    if args:
        filenames = pep_filename_generator(args)
    else:
        # do them all
        filenames = glob.glob("pep-*.txt")
        filenames.sort()
    for filename in filenames:
        try:
            make_html(filename)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            print "While building PEPs: %s" % filename
            if settings.keep_going:
                ee, ev, et = sys.exc_info()
                traceback.print_exception(ee, ev, et, file=sys.stdout)
                print "--keep-going/-k specified, continuing"
                continue
            else:
                raise

def pep_filename_generator(args):
    for pep in args:
        filename = find_pep(pep)
        yield filename


def main(argv=None):
    check_requirements()

    if argv is None:
        argv = sys.argv[1:]

    try:
        opts, args = getopt.getopt(
            argv, 'hd:fkq',
            ['help', 'destdir=', 'force', 'keep-going', 'quiet'])
    except getopt.error, msg:
        usage(1, msg)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-d', '--destdir'):
            settings.dest_dir_base = arg
        elif opt in ('-f', '--force'):
            settings.force_rebuild = True
        elif opt in ('-k', '--keep-going'):
            settings.force_rebuild = True
        elif opt in ('-q', '--quiet'):
            settings.verbose = False

    build_peps(args)



if __name__ == "__main__":
    main()
