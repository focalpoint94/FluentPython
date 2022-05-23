import asyncio
import collections
import sys

import aiohttp
from aiohttp import web
import tqdm

from flags2_common import main, HTTPStatus, Result, save_flag


DEFAULT_CONCUR_REQ = 5
MAX_CONCUR_REQ = 1000


class FetchError(Exception):
    def __init__(self, country_code):
        self.country_code = country_code

async def http_get(session, url):
    async with session.get(url) as resp:
        if resp.status == 200:
            ctype = resp.headers.get('Content-type', '').lower()
            if 'json' in ctype or url.endswith('json'):
                data = await resp.json()
            else:
                data = await resp.read()
            return data
        elif resp.status == 404:
            raise web.HTTPNotFound()
        else:
            raise aiohttp.HttpProcessingError(
                code=resp.status, message=resp.reason,
                headers=resp.headers)

async def get_country(session, base_url, cc):
    url = '{}/{cc}/metadata.json'.format(base_url, cc=cc.lower())
    metadata = await http_get(session, url)
    return metadata['country']

async def get_flag(session, base_url, cc):
    url = '{}/{cc}/{cc}.gif'.format(base_url, cc=cc.lower())
    return await http_get(session, url)

async def download_one(session, cc, base_url, semaphore, verbose):
    async with semaphore:
        try:
            image = await get_flag(session, base_url, cc)
            country = await get_country(session, base_url, cc)
        except web.HTTPNotFound:
            status = HTTPStatus.not_found
            msg = 'not found'
        except Exception as exc:
            raise FetchError(cc) from exc
        else:
            country = country.replace(' ', '_')
            filename = '{}-{}.gif'.format(country, cc)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, save_flag, image, filename)
            status = HTTPStatus.ok
            msg = 'OK'
        if verbose and msg:
            print(cc, msg)
        return Result(status, cc)

async def download_coro(cc_list, base_url, verbose, concur_req):
    async with aiohttp.ClientSession() as session:
        counter = collections.Counter()
        semaphore = asyncio.Semaphore(concur_req)

        to_do = [download_one(session, cc, base_url, semaphore, verbose) for cc in sorted(cc_list)]
        to_do = asyncio.as_completed(to_do)
        if not verbose:
            to_do = tqdm.tqdm(to_do, total=len(cc_list))

        for future in to_do:
            try:
                res = await future
            except FetchError as exc:
                country_code = exc.country_code
                try:
                    error_msg = exc.__cause__.args[0]
                except IndexError:
                    error_msg = exc.__cause__.__clas__.__name__
                if verbose and error_msg:
                    print('*** Error for {}: {}'.format(country_code, error_msg))
            else:
                status = res.status
            counter[status] += 1
        return counter

def download_many(cc_list, base_url, verbose, concur_req):
    loop = asyncio.get_event_loop()
    coro = download_coro(cc_list, base_url, verbose, concur_req)
    counter = loop.run_until_complete(coro)
    loop.close()
    return counter


if __name__ == '__main__':
    py_ver = int(f"{sys.version_info.major}{sys.version_info.minor}")
    if py_ver > 37 and sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main(download_many, DEFAULT_CONCUR_REQ, MAX_CONCUR_REQ)

