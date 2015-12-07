#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

from plexpy import versioncheck, logger, plextv, pmsconnect, datafactory, graphs, users
import os
import plexpy
import json
import traceback
import cherrypy
import re
import hashlib
import random
import xmltodict

# self.cmd_list = ['getLogs', 'getVersion', 'checkGithub', 'shutdown',
#             'getSettings', 'restart', 'update', 'getApikey', 'getHistory',
#             'getMetadata', 'getUserips', 'getPlayby', 'getSync']


class Api(object):
    def __init__(self, out='json'):

        self.apikey = None
        self.authenticated = False
        self.cmd = None
        self.kwargs = None
        # For the responses
        self.data = None
        self.msg = None
        self.result_type = 'error'
        # Possible general params
        self.callback = None
        self.out_type = out
        self.debug = None

    def checkParams(self, *args, **kwargs):

        if not plexpy.CONFIG.API_ENABLED:
            self.msg = 'API not enabled'
        elif not plexpy.CONFIG.API_KEY:
            self.msg = 'API key not generated'
        elif len(plexpy.CONFIG.API_KEY) != 32:
            self.msg = 'API key not generated correctly'
        elif 'apikey' not in kwargs:
            self.msg = 'Parameter apikey is required'
        elif kwargs.get('apikey', '') != plexpy.CONFIG.API_KEY:
            self.msg = 'Invalid apikey'
        elif 'cmd' not in kwargs:
            self.msg = 'Parameter %s required. possible commands are: %s' % ', '.join(self.cmd_list)
        elif 'cmd' in kwargs and kwargs.get('cmd') not in self.cmd_list:
            self.msg = 'Unknown command, %s possible commands are: %s' % (kwargs.get('cmd', ''), ', '.join(self.cmd_list))

        # Set default values or remove them from kwargs

        self.callback = kwargs.pop('callback', None)
        self.apikey = kwargs.pop('apikey', None)
        self.cmd = kwargs.pop('cmd', None)
        self.debug = kwargs.pop('debug', False)
        # Allow override for the api.
        self.out_type = kwargs.pop('out_type', 'json')

        if self.apikey == plexpy.CONFIG.API_KEY and plexpy.CONFIG.API_ENABLED and self.cmd in self.cmd_list:
            self.authenticated = True
            self.msg = None
        elif self.cmd == 'getApikey' and plexpy.CONFIG.API_ENABLED:
            self.authenticated = True
            # Remove the old error msg
            self.msg = None

        self.kwargs = kwargs

    def _responds(self, result_type='success', data=None, msg=''):

        if data is None:
            data = {}
        return {"response": {"result": result_type, "message": msg, "data": data}}

    def _out_as(self, out):

        if self.out_type == 'json':
            cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
            try:
                out = json.dumps(out, indent=4, sort_keys=True)
                if self.callback is not None:
                    cherrypy.response.headers['Content-Type'] = 'application/javascript'
                    # wrap with JSONP call if requested
                    out = self.callback + '(' + out + ');'
            # if we fail to generate the output fake an error
            except Exception as e:
                logger.info(u"API :: " + traceback.format_exc())
                out['message'] = traceback.format_exc()
                out['result'] = 'error'
        if self.out_type == 'xml':
            cherrypy.response.headers['Content-Type'] = 'application/xml'
            try:
                out = xmltodict.unparse(out, pretty=True)
            except ValueError as e:
                logger.error('Failed to parse xml result')
                try:
                    out['message'] = e
                    out['result'] = 'error'
                    out = xmltodict.unparse(out, pretty=True)

                except Exception as e:
                    logger.error('Failed to parse xml result error message')
                    out = '''<?xml version="1.0" encoding="utf-8"?>
                                <response>
                                    <message>%s</message>
                                    <data></data>
                                    <result>error</result>
                                </response>
                          ''' % e

        return out

    def fetchData(self):

        logger.info('Recieved API command: %s' % self.cmd)
        if self.cmd and self.authenticated:
            methodtocall = getattr(self, "_" + self.cmd)
            # Let the traceback hit cherrypy so we can
            # see the traceback there
            if self.debug:
                methodtocall(**self.kwargs)
            else:
                try:
                    methodtocall(**self.kwargs)
                except Exception as e:
                    logger.error(traceback.format_exc())

        # Im just lazy, fix me plx
        if self.data or isinstance(self.data, (dict, list)):
            if len(self.data):
                self.result_type = 'success'

        return self._out_as(self._responds(result_type=self.result_type, msg=self.msg, data=self.data))

    def _dic_from_query(self, query):

        myDB = database.DBConnection()
        rows = myDB.select(query)

        rows_as_dic = []

        for row in rows:
            row_as_dic = dict(zip(row.keys(), row))
            rows_as_dic.append(row_as_dic)

        return rows_as_dic
