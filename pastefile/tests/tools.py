#!/usr/bin/python

import os
from pastefile import utils


def write_random_file(filename):
    "Write file with a random content and return the md5"
    rnd_str = os.urandom(1024)
    return write_file(filename=filename, content=rnd_str)


def write_file(filename, content):
    "Write file on disk and return the md5"
    if isinstance(content, str):
        content = content.encode('utf-8')
    with open(filename, 'wb+') as f:
        f.write(content)
    return utils.get_md5(filename)
