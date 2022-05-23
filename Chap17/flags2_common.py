import os
import time
import sys
import string
import argparse
from collections import namedtuple
from enum import Enum


Result = namedtuple('Result', 'status data')
HTTPStatus = Enum('Status', 'ok not_found error')

POP20_CC = ('CN IN US ID BR PK NK BD RU JP'
            'MX PH VN ET EG DE IR TR CD FR').split()

SERVER = 'http://flupy.org/data/flags'

DEST_DIR = 'downloads/'


def save_flag(img, filename):
    if not os.path.exists(DEST_DIR):
        os.mkdir(DEST_DIR)
    path = os.path.join(DEST_DIR, filename)
    with open(path, 'wb') as fp:
        fp.write(img)

def initial_report(cc_list, actual_req):
    msg = 'Searching for {} flag(s) from {}.'
    print(msg.format(len(cc_list), SERVER))
    msg = '{} concurrent connection(s) will be used.'
    print(msg.format(actual_req))

def final_report(counter, start_time):
    elapsed = time.time() - start_time
    print('-' * 20)
    msg = '{} flag(s) downloaded.'
    print(msg.format(counter[HTTPStatus.ok]))
    if counter[HTTPStatus.not_found]:
        print(counter[HTTPStatus.not_found], 'not found.')
    if counter[HTTPStatus.error]:
        print('{} error(s) occurred.'.format(counter[HTTPStatus.error]))
    print(f'Elapsed time: {elapsed:.2f}s')

def expand_cc_args(every_cc, cc_args, limit):
    codes = set()
    AZ = string.ascii_uppercase
    if every_cc:
        codes.update(a+b for a in AZ for b in AZ)
    else:
        for cc in (c.upper() for c in cc_args):
            if len(cc) == 2 and all(c in AZ for c in cc):
                codes.add(cc)
            else:
                msg = 'each CC argument must be from AA to ZZ'
                raise ValueError('*** Usage error: '+msg)
    return sorted(codes)[:limit]

def process_args(default_concur_req):
    parser = argparse.ArgumentParser(
        description='Download flags for country codes. '
        'Default: top 20 countries by population.')
    parser.add_argument('cc', metavar='CC', nargs='*',
                        help='country code (eg. BZ)')
    parser.add_argument('-e', '--every', action='store_true',
                        help='get flags for every possible code (AA...ZZ)')
    parser.add_argument('-l', '--limit', metavar='N', type=int,
                        help='limit to N first codes', default=sys.maxsize)
    parser.add_argument('-m', '--max_req', metavar='CONCURRENT', type=int,
                        default=default_concur_req,
                        help=f'maximum concurrent requets (default={default_concur_req})')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='output detailed progress info')
    args = parser.parse_args()

    if args.max_req < 1:
        print('*** Usage error: --max_req CONCURRENT must be >= 1')
        parser.print_usage()
        sys.exit(1)
    if args.limit < 1:
        print('*** Usage error: --limit N must be >= 1')
        parser.print_usage()
        sys.exit(1)
    try:
        cc_list = expand_cc_args(args.every, args.cc, args.limit)
    except ValueError as exc:
        print(exc.args[0])
        parser.print_usage()
        sys.exit(1)
    if not cc_list:
        cc_list = sorted(POP20_CC)
    return args, cc_list

def main(download_many, default_concur_req=1, max_concur_req=1):
    args, cc_list = process_args(default_concur_req)
    actual_req = min(args.max_req, max_concur_req, len(cc_list))
    initial_report(cc_list, actual_req)
    base_url = SERVER
    t0 = time.time()
    counter = download_many(cc_list, base_url, args.verbose, actual_req)
    assert sum(counter.values()) == len(cc_list), 'some downloads are unaccounted for'
    final_report(counter, t0)

