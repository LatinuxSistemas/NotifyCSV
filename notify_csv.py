#!/usr/bin/env fades
# -*- coding: utf-8 -*-
##############################################################################
#
#    NotifyCSV script, watch a directory and parse its .csv files
#    Copyright (C) 2015 Latinux S.A. (<http://www.latinux.com.ar>)
#
#    This file is a part of NotifyCSV
#
#    NotifyCSV is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    NotifyCSV is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import csv
import os
import re
import sys

import sh  # fades.pypi
from pyinotify import (IN_CLOSE_WRITE, IN_DELETE, IN_DELETE_SELF,  # fades.pypi
                       Notifier, ProcessEvent, WatchManager)


class EventHandler(ProcessEvent):

    def my_init(self, logger=None, dir_to_watch=None, masks=None, regex='.*', delimiter='\t'):
        self.logger = logger
        self.logger.info("Starting event handler")
        self.regex = regex
        self.delimiter = delimiter
        self._create_dir(dir_to_watch)
        self._fieldnames = ("name", "surname", "birthdate", "city", "country")
        if masks is None:
            self.masks = IN_CLOSE_WRITE | IN_DELETE | IN_DELETE_SELF
        else:
            self.masks = masks
        wm = WatchManager()
        wm.add_watch(self.dir_to_watch, self.masks)
        notifier = Notifier(wm, self)
        notifier.loop()

    @property
    def regex(self):
        return self._regex

    @regex.setter
    def regex(self, regex):
        self._regex = re.compile(regex)

    @property
    def fieldnames(self):
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, values):
        self._fieldnames = values

    def _create_dir(self, dir_to_watch):
        if not os.path.exists(dir_to_watch):
            self.logger.info("Creating dir to watch: %s" % dir_to_watch)
            sh.mkdir(dir_to_watch)
        self.dir_to_watch = dir_to_watch

    def process_IN_DELETE_SELF(self, event):
        self.logger.warning("Someone removed %s, we re-create it." % event.pathname)
        self._create_dir(event.pathname)

    def process_IN_DELETE(self, event):
        """
        Write log info when file is deleted
        """
        self.logger.info("Deleted file: %s" % event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        """
        When file is written
        """
        pathname = event.pathname
        self.logger.info("close_write On file: %s" % pathname)
        if re.match(self.regex, pathname):
            logger.info("CSV file found: %s, let's parse it!" % pathname)
            with open(pathname, newline='') as csvfile:
                csvdict = csv.DictReader(
                    csvfile,
                    fieldnames=self.fieldnames,
                    delimiter=self.delimiter,
                )
                for line in csvdict:
                    print(line)
        return True

if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    prog_name = 'NotifyCSV'
    default_dir = os.path.join(os.environ['HOME'], "csv-input")
    logger = logging.getLogger(prog_name)
    parser = ArgumentParser(prog=prog_name)

    parser.add_argument("-d", "--delimiter", help="Specify field delimiter. Default: '\\t'",
                        default='\t')
    parser.add_argument("-r", "--regex", default='.+.[Cc][Ss][Vv]',
                        help=("Use this regex to match names in watched dir. Can be any valid "
                              "Python regex. Default: '^.+\.[cC][sS][vV]$'")
                        )
    parser.add_argument("-l", "--logfile", help="Log to this file")
    parser.add_argument("-w", "--watch-dir", help="Dir to watch. Default: %s" % default_dir,
                        default=default_dir)
    parser.add_argument("-l", "--logfile", help="Log to this file")
    parser.add_argument("-u", "--user", help="OpenERP/Odoo user. Default: admin", default="admin")
    parser.add_argument("-p", "--password", help="OpenERP/Odoo user password. Default: admin",
                        default="admin")
    parser.add_argument("-P", "--port", help="Port OpenERP/Odoo is listening. Default: 8069",
                        default=8069)
    parser.add_argument("-d", "--db", help="OpenERP/Odoo database to use. Required!",
                        required=True)

    options = parser.parse_args()

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
    logfile = options.logfile
    if logfile is None:
        streamH = logging.StreamHandler(sys.stdout)
    else:
        streamH = logging.FileHandler(logfile)
    streamH.setFormatter(formatter)
    logger.addHandler(streamH)

    logger.info("Started")

    event_handler = EventHandler(
        logger=logger,
        dir_to_watch=options.watch_dir,
        regex=options.regex,
        delimiter=options.delimiter,
    )
    # notifier = EventHandler.notifier
    # notifier.loop()
