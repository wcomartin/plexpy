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
from plexpy.api import Api
import os
import plexpy
import json
import traceback
import cherrypy
import re
import hashlib
import random
import xmltodict


class ApiData(Api):
    cmd_list = ['getHistory', 'getMetadata', 'getUserips', 'getPlayby', 'getUsers', 'getActivities']

    def _getHistory(self, user=None, user_id=None, rating_key='', parent_rating_key='', grandparent_rating_key='', start_date='', **kwargs):

        custom_where = []
        if user_id:
            custom_where = [['user_id', user_id]]
        elif user:
            custom_where = [['user', user]]
        if 'rating_key' in kwargs:
            rating_key = kwargs.get('rating_key', "")
            custom_where = [['rating_key', rating_key]]
        if 'parent_rating_key' in kwargs:
            rating_key = kwargs.get('parent_rating_key', "")
            custom_where = [['parent_rating_key', rating_key]]
        if 'grandparent_rating_key' in kwargs:
            rating_key = kwargs.get('grandparent_rating_key', "")
            custom_where = [['grandparent_rating_key', rating_key]]
        if 'start_date' in kwargs:
            start_date = kwargs.get('start_date', "")
            custom_where = [['strftime("%Y-%m-%d", datetime(date, "unixepoch", "localtime"))', start_date]]

        data_factory = datafactory.DataFactory()
        history = data_factory.get_history(kwargs=kwargs, custom_where=custom_where)

        self.data = history
        return self.data

    def _getMetadata(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata(rating_key, 'dict')

        if result:
            self.data = result
            return result
        else:
            self.msg = 'Unable to retrive metadata %s' % rating_key
            logger.warn('Unable to retrieve data.')

    def _getUserips(self, user_id=None, user=None, **kwargs):
        custom_where = []
        if user_id:
            custom_where = [['user_id', user_id]]
        elif user:
            custom_where = [['user', user]]

        user_data = users.Users()
        history = user_data.get_user_unique_ips(kwargs=kwargs,
                                                custom_where=custom_where)

        if history:
            self.data = history
            return history
        else:
            self.msg = 'Failed to find users ips'

    def _getPlayby(self, time_range='30', y_axis='plays', playtype='total_plays_per_month', **kwargs):

        graph = graphs.Graphs()
        if playtype == 'total_plays_per_month':
            result = graph.get_total_plays_per_month(y_axis=y_axis)

        elif playtype == 'total_plays_per_day':
            result = graph.get_total_plays_per_day(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_per_hourofday':
            result = graph.get_total_plays_per_hourofday(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_per_dayofweek':
            result = graph.get_total_plays_per_dayofweek(time_range=time_range, y_axis=y_axis)

        elif playtype == 'stream_type_by_top_10_users':
            result = graph.get_stream_type_by_top_10_users(time_range=time_range, y_axis=y_axis)

        elif playtype == 'stream_type_by_top_10_platforms':
            result = graph.get_stream_type_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_stream_resolution':
            result = graph.get_total_plays_by_stream_resolution(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_source_resolution':
            result = graph.get_total_plays_by_source_resolution(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_per_stream_type':
            result = graph.get_total_plays_per_stream_type(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_top_10_users':
            result = graph.get_total_plays_by_top_10_users(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_top_10_platforms':
            result = graph.get_total_plays_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        if result:
            self.data = result
            return result
        else:
            logger.warn('Unable to retrieve %s from db' % playtype)

    def _getUsers(self, **kwargs):
        user_data = users.Users()
        self.data = user_data.get_user_list(kwargs=kwargs)

        return self.data

    def _getActivities(self):
        pms_connect = pmsconnect.PmsConnect()
        self.data = pms_connect.get_current_activity()['sessions']
        print(pms_connect.get_current_activity()['sessions'])

        return self.data
