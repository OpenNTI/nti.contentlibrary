#!/usr/bin/env python
# -*- coding: utf-8 -*-
# JAM: NTI branched from github post 2.5.2.

# Copyright (c) 2006,2007,2008 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# TODO: Port to argparse
usage_string = """
SYNOPSIS
    s3put [-a/--access_key <access_key>] [-s/--secret_key <secret_key>]
          -b/--bucket <bucket_name> [-c/--callback <num_cb>]
          [-d/--debug <debug_level>] [-i/--ignore <ignore_dirs>]
          [-n/--no_op] [-p/--prefix <prefix>] [-q/--quiet]
          [-g/--grant grant] [-w/--no_overwrite] [-r/--reduced] path

    Where
        access_key - Your AWS Access Key ID.  If not supplied, boto will
                     use the value of the environment variable
                     AWS_ACCESS_KEY_ID
        secret_key - Your AWS Secret Access Key.  If not supplied, boto
                     will use the value of the environment variable
                     AWS_SECRET_ACCESS_KEY
        bucket_name - The name of the S3 bucket the file(s) should be
                      copied to.
        path - A path to a directory or file that represents the items
               to be uploaded.    If the path points to an individual file,
               that file will be uploaded to the specified bucket.    If the
               path points to a directory, s3_it will recursively traverse
               the directory and upload all files to the specified bucket.
        debug_level - 0 means no debug output (default), 1 means normal
                      debug output from boto, and 2 means boto debug output
                      plus request/response output from httplib
        ignore_dirs - a comma-separated list of directory names that will
                      be ignored and not uploaded to S3.
        num_cb - The number of progress callbacks to display.  The default
                 is zero which means no callbacks.    If you supplied a value
                 of "-c 10" for example, the progress callback would be
                 called 10 times for each file transferred.
        prefix - A file path prefix that will be stripped from the full
                 path of the file when determining the key name in S3.
                 For example, if the full path of a file is:
                     /home/foo/bar/fie.baz
                 and the prefix is specified as "-p /home/foo/" the
                 resulting key name in S3 will be:
                     /bar/fie.baz
                 The prefix must end in a trailing separator and if it
                 does not then one will be added.
        grant - A canned ACL policy that will be granted on each file
                transferred to S3.    The value of provided must be one
                of the "canned" ACL policies supported by S3:
                private|public-read|public-read-write|authenticated-read
        no_overwrite - No files will be overwritten on S3, if the file/key
                       exists on s3 it will be kept. This is useful for
                       resuming interrupted transfers. Note this is not a
                       sync, even if the file has been updated locally if
                       the key exists on s3 the file on s3 will not be
                       updated.
        reduced - Use Reduced Redundancy storage


     If the -n option is provided, no files will be transferred to S3 but
     informational messages will be printed about what would happen.

     Certain content types will be gzipped on upload; pulls in the
     content fragment package to be sure the right types get set. Does
     not skip dot files, with the exception of certain version
     control directories (.svn and .git), Mac OS X barfs ('.DS_Store')
     and python/emacs configs..
"""

import os
import sys
import gzip
import getopt
import logging
from six import StringIO

import boto

import mimetypes

from zope.configuration import xmlconfig

from zope.exceptions.log import Formatter

#: Content types we will gzip on upload
GZIP_TYPES = ('text/csv', 'text/css', 'text/html', 'text/xml', 'application/xml',
              'application/json', 'application/javascript')

#: Anything we explicitly want to exclude from gzipping, like .json
#: data
NOT_GZIP_EXT = ()

#: Unix dotfiles we will always ignore
IGNORED_DOTFILES = ('.svn', '.git', '.DS_Store', '.coverage', '.noseids',
                    '.dir_locals.el', '.installed.cfg')


logger = __import__('logging').getLogger(__name__)


def usage():
    print(usage_string)
    sys.exit()


def submit_cb(bytes_so_far, total_bytes):
    print('%d bytes transferred / %d bytes total' %
          (bytes_so_far, total_bytes))


def get_key_name(fullpath, prefix):
    key_name = fullpath[len(prefix):]
    l = key_name.split(os.sep)
    return '/'.join(l)


def set_log_formatter():
    ei = '%(asctime)s %(levelname)-5.5s [%(name)s][%(thread)d][%(threadName)s] %(message)s'
    logging.root.handlers[0].setFormatter(Formatter(ei))


def s3_upload_file(key, fullpath, cb=None, num_cb=None, policy=None,
                   reduced_redundancy=None, headers=None,
                   gzip_types=GZIP_TYPES, gz_ext_exclude=NOT_GZIP_EXT):
    """
    Upload a file to s3

    :param key - S3 key
    :param fullpath - file to upload
    :param cb - callback
    :param: num_cb - The number of progress callbacks to display.
    :param: policy - A canned ACL policy that will be granted on each file
                     transferred to S3. 
                     private|public-read|public-read-write|authenticated-read
    :param: reduced_redundancy - Use Reduced Redundancy storage
    :param: headers - Transfer file headers
    :param: gzip_types - Mime types to upload as gzip
    :param: gz_ext_exclude - exclude exts files from gzipping
    """

    if headers is not None:
        headers = dict(headers)
    else:
        headers = {}

    mt = mimetypes.guess_type(fullpath)
    if mt and mt[0]:
        headers['Content-Type'] = mt[0]

    if      headers.get('Content-Type') in gzip_types \
        and not os.path.splitext(fullpath)[-1] in gz_ext_exclude:
        mtime = os.stat(fullpath).st_mtime
        filename = os.path.basename(fullpath)
        strio = StringIO()
        with gzip.GzipFile(fileobj=strio,
                           mode='wb',
                           filename=filename,
                           mtime=mtime) as gzipped:
            with open(fullpath, 'rb') as f:
                gzipped.write(f.read())
        data = strio.getvalue()
        headers['Content-Encoding'] = 'gzip'
        key.set_contents_from_string(data,
                                     cb=cb,
                                     num_cb=num_cb,
                                     policy=policy,
                                     reduced_redundancy=reduced_redundancy,
                                     headers=headers)
    else:
        key.set_contents_from_filename(fullpath,
                                       cb=cb,
                                       num_cb=num_cb,
                                       policy=policy,
                                       reduced_redundancy=reduced_redundancy,
                                       headers=headers)

    return headers
_upload_file = s3_upload_file


def main():
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], 'a:b:c::d:g:hi:np:qs:vwr',
            ['access_key=', 'bucket=', 'callback=', 'debug=', 'help',
             'grant=', 'ignore=', 'no_op', 'prefix=', 'quiet',
             'secret_key=', 'no_overwrite', 'reduced', "header="]
        )
    except:
        usage()

    cb = None
    debug = 0
    total = 0
    num_cb = 0
    headers = {}
    prefix = '/'
    grant = None
    quiet = False
    no_op = False
    reduced = False
    ignore_dirs = []
    bucket_name = ''
    no_overwrite = False
    aws_access_key_id = None
    aws_secret_access_key = None

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-a', '--access_key'):
            aws_access_key_id = a
        if o in ('-b', '--bucket'):
            bucket_name = a
        if o in ('-c', '--callback'):
            num_cb = int(a)
            cb = submit_cb
        if o in ('-d', '--debug'):
            debug = int(a)
        if o in ('-g', '--grant'):
            grant = a
        if o in ('-i', '--ignore'):
            ignore_dirs = a.split(',')
        if o in ('-n', '--no_op'):
            no_op = True
        if o in ('-w', '--no_overwrite'):
            no_overwrite = True
        if o in ('-r', '--reduced'):
            reduced = True
        if o in ('-p', '--prefix'):
            prefix = a
            if prefix[-1] != os.sep:
                prefix = prefix + os.sep
        if o in ('-q', '--quiet'):
            quiet = True
        if o in ('-s', '--secret_key'):
            aws_secret_access_key = a
        if o in ('--header'):
            # JAM: FIXME: The lowlevel boto layer has a bug uploading the cache-control header,
            # it prematurely escapes the = in max age, so we get a bad value
            # JAM: = is valid on the RHS in things like Cache-Control
            (k, v) = a.split("=", 1)
            headers[k] = v
    if len(args) != 1:
        print(usage())

    import nti.contentfragments
    xmlconfig.file(package=nti.contentfragments,
                   name="configure.zcml")

    path = os.path.expanduser(args[0])
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    if bucket_name:
        c = boto.connect_s3(aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key)
        c.debug = debug
        b = c.get_bucket(bucket_name)
        if os.path.isdir(path):
            if no_overwrite:
                if not quiet:
                    print('Getting list of existing keys to check against')
                keys = []
                for key in b.list(get_key_name(path, prefix)):
                    keys.append(key.name)
            for root, dirs, files in os.walk(path):
                for ignore in ignore_dirs:
                    if ignore in dirs:
                        dirs.remove(ignore)
                for filename in files:
                    if filename in IGNORED_DOTFILES:
                        continue

                    fullpath = os.path.join(root, filename)
                    key_name = get_key_name(fullpath, prefix)
                    copy_file = True
                    if no_overwrite:
                        if key_name in keys:
                            copy_file = False
                            if not quiet:
                                print('Skipping %s as it exists in s3' %
                                      filename)
                    if copy_file:
                        if not quiet and no_op:
                            print('Copying %s to %s/%s' %
                                  (filename, bucket_name, key_name))
                        if not no_op:
                            k = b.new_key(key_name)
                            file_headers = _upload_file(k, fullpath,
                                                        cb=cb,
                                                        policy=grant,
                                                        num_cb=num_cb,
                                                        headers=headers,
                                                        reduced_redundancy=reduced)
                            if not quiet:
                                print('Copied %s to %s/%s as type %s encoding %s'
                                      % (filename, bucket_name, key_name,
                                          file_headers.get(
                                              'Content-Type',
                                              'application/octet-stream'),
                                          file_headers.get('Content-Encoding', 'identity')))
                    total += 1
        elif os.path.isfile(path):
            copy_file = True
            key_name = get_key_name(path, prefix)
            if no_overwrite:
                if b.get_key(key_name):  # FIXME: maybe none
                    copy_file = False
                    if not quiet:
                        print('Skipping %s as it exists in s3' % path)
            if copy_file:
                k = b.new_key(key_name)
                _upload_file(k, path, cb=cb, num_cb=num_cb,
                             policy=grant,
                             reduced_redundancy=reduced, headers=headers)
    else:
        print(usage())


if __name__ == "__main__":
    main()
