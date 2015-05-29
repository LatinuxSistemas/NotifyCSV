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

import sh  # fades.pypi
import pyinotify  # fades.pypi
import csv

if __name__ == '__main__':
    PROGRAM_NAME = 'NotifyCSV'
    import logging
    logger = logging.getLogger(PROGRAM_NAME)

    from argparse import ArgumentParser

    parser = ArgumentParser(prog=PROGRAM_NAME)

    parser.add_argument("-s", "--separator", help="Specify field separator. Default: '\\t'")
    parser.add_argument("-m", "--match", default='.+.[Cc][Ss][Vv]',
                        help=("Use this regex to match names in watched dir. Can be any valid "
                              "Python regex. Default: '.+.[Cc][Ss][Vv]'")
                        )
    parser.add_argument("-l", "--logfile", help="Log to this file")
    parser.add_argument("-u", "--user", help="OpenERP/Odoo user. Default: admin", default="admin")
    parser.add_argument("-p", "--password", help="OpenERP/Odoo user password. Default: admin",
                        default="admin")
    parser.add_argument("-P", "--port", help="Port OpenERP/Odoo is listening. Default: 8069",
                        default=8069)
    parser.add_argument("-d", "--db", help="OpenERP/Odoo database to use. Required!",
                        required=True)

    options = parser.parse_args()
