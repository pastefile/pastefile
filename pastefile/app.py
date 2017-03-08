#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, abort, jsonify
from flask import render_template
from pastefile import utils
from pastefile import controller

default_config = {
    'UPLOAD_FOLDER': {
        'value': '/opt/pastefile/files',
        'type': str()},
    'FILE_LIST': {
        'value': '/opt/pastefile/uploaded_files_jsondb',
        'type': str()},
    'TMP_FOLDER': {
        'value': '/opt/pastefile/tmp',
        'type': str()},
    'EXPIRE': {
        'value': '86400',
        'type': str()},
    'DEBUG_PORT': {
        'value': '5000',
        'type': str()},
    'LOG': {
        'value': '/opt/pastefile/pastefile.log',
        'type': str()},
    'DISABLED_FEATURE': {
        'value': 'ls',
        'type': list()},
    'DISPLAY_FOR': {
        'value': 'chrome,firefox',
        'type': list()}
    }
app = Flask("pastefile")
LOG = app.logger
LOG.setLevel(logging.DEBUG)
hdl_stream = logging.StreamHandler()
hdl_stream.setLevel(logging.INFO)
formatter_stream = logging.Formatter('%(asctime)s - '
                                     '%(name)s - '
                                     '%(levelname)s - %(message)s')
hdl_stream.setFormatter(formatter_stream)
LOG.addHandler(hdl_stream)


def validate(config, default):
    for config_name, value in config.iteritems():
        if config_name not in default.keys():
            continue
        if default[config_name]['type'] == list() and type(value) == str:
            config[config_name] = [i.strip() for i in value.split(',')]


def set_default(_app, default):
    for config_name, _default in default.iteritems():
        _app.config[config_name] = os.getenv(config_name, _default['value'])


def init_check_directories(_app):
    for key in ["UPLOAD_FOLDER", "FILE_LIST", "TMP_FOLDER", "LOG"]:
        directory = _app.config[key].rstrip('/')
        if not os.path.isdir(os.path.dirname(directory)):
            LOG.error("'%s' doesn't exist or is not a directory" %
                      os.path.dirname(directory))
            return False

    for key in ["UPLOAD_FOLDER", "TMP_FOLDER"]:
        directory = _app.config[key].rstrip('/')
        if os.path.exists(directory):
            LOG.info("%s already exists, skipping creation." % directory)
            continue
        LOG.warning("'%s' doesn't exist, creating" % directory)
        try:
            os.makedirs(directory)
            LOG.warning("%s directory created" % directory)
        except OSError as e:
            LOG.error("%s" % e)
            return False

    return True


# Set default configuration values
set_default(_app=app, default=default_config)
try:
    LOG.debug("CWD=%s" % os.getcwd())
    LOG.debug("Trying to set from configuration file %s" %
              os.getenv('PASTEFILE_SETTINGS'))
    app.config.from_envvar('PASTEFILE_SETTINGS')
    app.config['instance_path'] = app.instance_path
except (RuntimeError, IOError) as e:
    LOG.warning('PASTEFILE_SETTINGS configuration'
                ' file not available.\n'
                'message was: %s' % e)
finally:
    validate(config=app.config, default=default_config)
    LOG.debug("%s" % app.config)

if not os.getenv('TESTING') == 'TRUE':
    LOG.info("Checking directories...")
# check dirs only in non testing mode
    if not init_check_directories(_app=app):
        exit(1)
    LOG.info("Directories OK")

LOG.warning("===== Running config =====")
for c, v in app.config.iteritems():
    LOG.warning("%s: %s" % (c, v))


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        controller.clean_files(dbfile=app.config['FILE_LIST'],
                               expire=app.config['EXPIRE'])
        return controller.upload_file(request=request, config=app.config)
    else:
        # In case no file, return help
        return abort(404)


@app.route('/<id_file>/infos', methods=['GET'])
def display_file_infos(id_file):
    file_infos = controller.get_file_info(id_file=id_file,
                                          config=app.config,
                                          env=request.environ)
    if not file_infos:
        return abort(404)
    return jsonify(file_infos)


@app.route('/<id_file>', methods=['GET', 'DELETE'])
def get_or_delete_file(id_file):
    if request.method == 'GET':
        return controller.get_file(request=request,
                                   id_file=id_file,
                                   config=app.config)
    if request.method == 'DELETE':
        try:
            if 'delete' in app.config['DISABLED_FEATURE']:
                LOG.info("[delete] Tried to call"
                         "delete but this url is disabled")
                return 'Administrator disabled the delete option.\n'
        except (KeyError, TypeError):
            pass
        return controller.delete_file(request=request,
                                      id_file=id_file,
                                      dbfile=app.config['FILE_LIST'])


@app.route('/ls', methods=['GET'])
def list_all_files():
    try:
        if 'ls' in app.config['DISABLED_FEATURE']:
            LOG.info("[LS] Tried to call /ls but this url is disabled")
            return 'Administrator disabled the /ls option.\n'
    except (KeyError, TypeError):
        pass

    controller.clean_files(dbfile=app.config['FILE_LIST'],
                           expire=app.config['EXPIRE'])

    return jsonify(controller.get_all_files(
                   request=request, config=app.config))


@app.errorhandler(404)
def page_not_found(e):
    # request.method == 'GET'
    base_url = utils.build_base_url(env=request.environ)

    helps = (
        ("Upload a file:", "curl %s -F file=@**filename**" % base_url),
        ("View all uploaded files:", "curl %s/ls" % base_url),
        ("Get infos about one file:", "curl %s/**file_id**/infos" % base_url),
        ("Get a file:", "curl -JO %s/**file_id**" % base_url),
        ("Delete a file:", "curl -XDELETE %s/**id**" % base_url),
        ("Create an alias for cli usage",
         'pastefile() { curl -F file=@"$1" %s; }' % base_url),
    )
    context = {'user_agent': request.headers.get('User-Agent', ''),
               'helps': helps}
    return render_template('404.html', **context), 404
