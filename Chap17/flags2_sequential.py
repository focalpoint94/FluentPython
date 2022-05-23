import collections

import requests
import tqdm

from flags2_common import main, save_flag, HTTPStatus, Result

def get_flag(base_url, cc):
    url = '{}/{cc}/{cc}.gif'.format(base_url, cc=cc.lower())
    resp = requests.get(url)
    if resp.status_code != 200:
        resp.raise_for_status()
    return resp.content

def download_one(cc, base_url, verbose=False):
    try:
        image = get_flag(base_url, cc)
    except requests.exceptions.HTTPError as exc:
        res = exc.response
        if res.status_code == 404:
            status = HTTPStatus.not_found
            msg = 'not found'
        else:
            raise
    else:
        save_flag(image, cc.lower() + '.gif')
        status = HTTPStatus.ok
        msg = 'ok'

    if verbose:
        print(cc, msg)

    return Result(status, cc)

def download_many(cc_list, base_url, verbose, concur_req):
    counter = collections.Counter()
    cc_list = sorted(cc_list)
    if not verbose:
        cc_list = tqdm.tqdm(cc_list)
    for cc in cc_list:
        try:
            res = download_one(cc, base_url, verbose)
        except requests.exceptions.HTTPError as exc:
            error_msg = 'HTTP error {res.status_code} - {res.reason}'.format(res=exc.response)
            status = HTTPStatus.error
        except requests.exceptions.ConnectionError:
            error_msg = 'Connection error'
            status = HTTPStatus.error
        else:
            error_msg = ''
            status = res.status

        counter[status] += 1
        if verbose and error_msg:
            print('*** Error for {}: {}'.format(cc, error_msg))

    return counter

if __name__ == '__main__':
    main(download_many)



