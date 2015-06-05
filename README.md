NotifyCSV
=========

Watch a directory and parse its .csv files


Install it
----------

You need Python3.x to run it 

### Using fades

Install [fades](https://github.com/PyAr/fades) (I prefer to clone it rather than gettin it from pip) and then simply run:

    ~$ fades notify_csv.py

It's running!

### Long install 

    ~$ pip3 install sh pyinotify erppeek
    ~$ python notify_csv.py  # Remember: it must be Python 3+


Use it 
------

    ~$ fades notify_csv.py -h

    usage: NotifyCSV [-h] [-d DELIMITER] [-r REGEX] [-l LOGFILE] [-w WATCH_DIR]
                     [-u USER] [-p PASSWORD] [-s HOST] [-P PORT] -b DB

    optional arguments:
      -h, --help            show this help message and exit
      -d DELIMITER, --delimiter DELIMITER
                        Specify field delimiter. Default: '\t'
      -r REGEX, --regex REGEX
                            Use this regex to match names in watched dir. Can be
                            any valid Python regex. Default: '^.+\.[cC][sS][vV]$'
      -l LOGFILE, --logfile LOGFILE
                            Log to this file
      -w WATCH_DIR, --watch-dir WATCH_DIR
                            Dir to watch. Default: /home/gabriel/csv-input
      -u USER, --user USER  OpenERP/Odoo user. Default: admin
      -p PASSWORD, --password PASSWORD
                            OpenERP/Odoo user password. Default: admin
      -s HOST, --host HOST  OpenERP/Odoo host. Default: localhost
      -P PORT, --port PORT  Port OpenERP/Odoo is listening. Default: 8069
      -b DB, --db DB        OpenERP/Odoo database to use. Required!

    ~$ fades notify_csv.py 

    2015-06-01 12:45:58,940 NotifyCSV INFO: Started
    2015-06-01 12:45:58,940 NotifyCSV INFO: Starting event handler
