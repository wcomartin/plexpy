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




class ApiSystem(Api):
    cmd_list = ['getLogs', 'getVersion', 'checkGithub', 'shutdown',
                'getSettings', 'restart', 'update', 'getApikey', 'getSync']

    def _getApikey(self, username='', password=''):
        """ Returns api key, requires username and password is active """

        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        if plexpy.CONFIG.HTTP_USERNAME and plexpy.CONFIG.HTTP_PASSWORD:
            if username == plexpy.HTTP_USERNAME and password == plexpy.CONFIG.HTTP_PASSWORD:
                if plexpy.CONFIG.API_KEY:
                    self.data = plexpy.CONFIG.API_KEY
                else:
                    self.data = apikey
                    plexpy.CONFIG.API_KEY = apikey
                    plexpy.CONFIG.write()
            else:
                self.msg = 'Authentication is enabled, please add the correct username and password to the parameters'
        else:
            if plexpy.CONFIG.API_KEY:
                self.data = plexpy.CONFIG.API_KEY
            else:
                # Make a apikey if the doesn't exist
                self.data = apikey
                plexpy.CONFIG.API_KEY = apikey
                plexpy.CONFIG.write()

        return self.data

    def _getLogs(self, sort='', search='', order='desc', regex='', **kwargs):
        """
            Returns the log

            Returns [{"response":
                                {"msg": "Hey",
                                 "result": "success"},
                                 "data": [{"time": "29-sept.2015",
                                            "thread: "MainThread",
                                            "msg: "Called x from y",
                                            "loglevel": "DEBUG"
                                           }
                                        ]

                                }
                    ]
        """
        logfile = os.path.join(plexpy.CONFIG.LOG_DIR, 'plexpy.log')
        templog = []
        start = int(kwargs.get('start', 0))
        end = int(kwargs.get('end', 0))

        if regex:
            logger.debug('Filtering log using regex %s' % regex)
            reg = re.compile('u' + regex, flags=re.I)

        for line in open(logfile, 'r').readlines():
            temp_loglevel_and_time = None

            try:
                temp_loglevel_and_time = line.split('- ')
                loglvl = temp_loglevel_and_time[1].split(' :')[0].strip()
                tl_tread = line.split(' :: ')
                if loglvl is None:
                    msg = line.replace('\n', '')
                else:
                    msg = line.split(' : ')[1].replace('\n', '')
                thread = tl_tread[1].split(' : ')[0]
            except IndexError:
                # We assume this is a traceback
                tl = (len(templog) - 1)
                templog[tl]['msg'] += line.replace('\n', '')
                continue

            if len(line) > 1 and temp_loglevel_and_time is not None and loglvl in line:

                d = {
                    'time': temp_loglevel_and_time[0],
                    'loglevel': loglvl,
                    'msg': msg.replace('\n', ''),
                    'thread': thread
                }
                templog.append(d)

        if end > 0:
                logger.debug('Slicing the log from %s to %s' % (start, end))
                templog = templog[start:end]

        if sort:
            logger.debug('Sorting log based on %s' % sort)
            templog = sorted(templog, key=lambda k: k[sort])

        if search:
            logger.debug('Searching log values for %s' % search)
            tt = [d for d in templog for k, v in d.items() if search.lower() in v.lower()]

            if len(tt):
                templog = tt

        if regex:
            tt = []
            for l in templog:
                stringdict = ' '.join('{}{}'.format(k, v) for k, v in l.items())
                if reg.search(stringdict):
                    tt.append(l)

            if len(tt):
                templog = tt

        if order == 'desc':
            templog = templog[::-1]

        self.data = templog
        return templog

    def _getVersion(self, **kwargs):
        self.data = {
            'git_path': plexpy.CONFIG.GIT_PATH,
            'install_type': plexpy.INSTALL_TYPE,
            'current_version': plexpy.CURRENT_VERSION,
            'latest_version': plexpy.LATEST_VERSION,
            'commits_behind': plexpy.COMMITS_BEHIND,
        }
        self.result_type = 'success'

    def _checkGithub(self, **kwargs):
        versioncheck.checkGithub()
        self._getVersion()

    def _shutdown(self, **kwargs):
        plexpy.SIGNAL = 'shutdown'
        self.msg = 'Shutting down plexpy'
        self.result_type = 'success'

    def _restart(self, **kwargs):
        plexpy.SIGNAL = 'restart'
        self.msg = 'Restarting plexpy'
        self.result_type = 'success'

    def _update(self, **kwargs):
        plexpy.SIGNAL = 'update'
        self.msg = 'Updating plexpy'
        self.result_type = 'success'

    def _getSync(self, machine_id=None, user_id=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        server_id = pms_connect.get_server_identity()

        plex_tv = plextv.PlexTV()
        if not machine_id:
            result = plex_tv.get_synced_items(machine_id=server_id['machine_identifier'], user_id=user_id)
        else:
            result = plex_tv.get_synced_items(machine_id=machine_id, user_id=user_id)

        if result:
            self.data = result
            return result
        else:
            self.msg = 'Unable to retrieve sync data for user'
            logger.warn('Unable to retrieve sync data for user.')

    def _getSettings(self):
        interface_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if
                          os.path.isdir(os.path.join(interface_dir, name))]

        config = {
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": plexpy.CONFIG.HTTP_PASSWORD,
            "launch_browser": bool(plexpy.CONFIG.LAUNCH_BROWSER),
            "enable_https": bool(plexpy.CONFIG.ENABLE_HTTPS),
            "https_cert": plexpy.CONFIG.HTTPS_CERT,
            "https_key": plexpy.CONFIG.HTTPS_KEY,
            "api_enabled": plexpy.CONFIG.API_ENABLED,
            "api_key": plexpy.CONFIG.API_KEY,
            "update_db_interval": plexpy.CONFIG.UPDATE_DB_INTERVAL,
            "freeze_db": bool(plexpy.CONFIG.FREEZE_DB),
            "log_dir": plexpy.CONFIG.LOG_DIR,
            "cache_dir": plexpy.CONFIG.CACHE_DIR,
            "check_github": bool(plexpy.CONFIG.CHECK_GITHUB),
            "interface_list": interface_list,
            "cache_sizemb": plexpy.CONFIG.CACHE_SIZEMB,
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_logs_folder": plexpy.CONFIG.PMS_LOGS_FOLDER,
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "pms_ssl": bool(plexpy.CONFIG.PMS_SSL),
            "pms_use_bif": bool(plexpy.CONFIG.PMS_USE_BIF),
            "pms_uuid": plexpy.CONFIG.PMS_UUID,
            "date_format": plexpy.CONFIG.DATE_FORMAT,
            "time_format": plexpy.CONFIG.TIME_FORMAT,
            "grouping_global_history": bool(plexpy.CONFIG.GROUPING_GLOBAL_HISTORY),
            "grouping_user_history": bool(plexpy.CONFIG.GROUPING_USER_HISTORY),
            "grouping_charts": bool(plexpy.CONFIG.GROUPING_CHARTS),
            "tv_notify_enable": bool(plexpy.CONFIG.TV_NOTIFY_ENABLE),
            "movie_notify_enable": bool(plexpy.CONFIG.MOVIE_NOTIFY_ENABLE),
            "music_notify_enable": bool(plexpy.CONFIG.MUSIC_NOTIFY_ENABLE),
            "tv_notify_on_start": bool(plexpy.CONFIG.TV_NOTIFY_ON_START),
            "movie_notify_on_start": bool(plexpy.CONFIG.MOVIE_NOTIFY_ON_START),
            "music_notify_on_start": bool(plexpy.CONFIG.MUSIC_NOTIFY_ON_START),
            "tv_notify_on_stop": bool(plexpy.CONFIG.TV_NOTIFY_ON_STOP),
            "movie_notify_on_stop": bool(plexpy.CONFIG.MOVIE_NOTIFY_ON_STOP),
            "music_notify_on_stop": bool(plexpy.CONFIG.MUSIC_NOTIFY_ON_STOP),
            "tv_notify_on_pause": bool(plexpy.CONFIG.TV_NOTIFY_ON_PAUSE),
            "movie_notify_on_pause": bool(plexpy.CONFIG.MOVIE_NOTIFY_ON_PAUSE),
            "music_notify_on_pause": bool(plexpy.CONFIG.MUSIC_NOTIFY_ON_PAUSE),
            "monitoring_interval": plexpy.CONFIG.MONITORING_INTERVAL,
            "refresh_users_interval": plexpy.CONFIG.REFRESH_USERS_INTERVAL,
            "refresh_users_on_startup": bool(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "ip_logging_enable": bool(plexpy.CONFIG.IP_LOGGING_ENABLE),
            "video_logging_enable": bool(plexpy.CONFIG.VIDEO_LOGGING_ENABLE),
            "music_logging_enable": bool(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "pms_is_remote": bool(plexpy.CONFIG.PMS_IS_REMOTE),
            "notify_watched_percent": plexpy.CONFIG.NOTIFY_WATCHED_PERCENT,
            "notify_on_start_subject_text": plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT,
            "notify_on_start_body_text": plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT,
            "notify_on_stop_subject_text": plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT,
            "notify_on_stop_body_text": plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT,
            "notify_on_pause_subject_text": plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT,
            "notify_on_pause_body_text": plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT,
            "notify_on_resume_subject_text": plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT,
            "notify_on_resume_body_text": plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT,
            "notify_on_buffer_subject_text": plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT,
            "notify_on_buffer_body_text": plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT,
            "notify_on_watched_subject_text": plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT,
            "notify_on_watched_body_text": plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT,
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_type": bool(plexpy.CONFIG.HOME_STATS_TYPE),
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "home_stats_cards": plexpy.CONFIG.HOME_STATS_CARDS,
            "home_library_cards": plexpy.CONFIG.HOME_LIBRARY_CARDS,
            "buffer_threshold": plexpy.CONFIG.BUFFER_THRESHOLD,
            "buffer_wait": plexpy.CONFIG.BUFFER_WAIT
        }

        self.data = config
        return config
