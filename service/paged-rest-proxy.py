import json

from flask import Flask, request, Response
import os
import requests
import logging
import dotdictify
from time import sleep

app = Flask(__name__)
logger = None
format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger('paged-datasource-service')

# Log to stdout
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

prop = os.environ.get('response_property', 'response')
response = None

headers = {}
if os.environ.get('headers') is not None:
    headers = json.loads(os.environ.get('headers').replace("'","\""))


class DataAccess:

    def __get_all_paged_entities(self, path, url_parameters):
        logger.info("Fetching data from paged url: %s", path)
        url = os.environ.get("baseurl") + path
        url = call_url(url, url_parameters, url_parameters.get(os.environ.get('startpage')))
        has_more_results = True
        page_counter = 1

        while has_more_results:
            if os.environ.get('sleep') is not None:
                logger.info("sleeping for %s milliseconds", os.environ.get('sleep') )
                sleep(float(os.environ.get('sleep')))

            logger.info("Fetching data from url: %s", url)
            req = requests.get(url, headers=headers)
            if req.status_code != 200:
                logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
                raise AssertionError ("Unexpected response status code: %d with response text %s"%(req.status_code, req.text))
            dict = dotdictify.dotdictify(json.loads(req.text))
            for entity in dict.results:
                yield entity
            if str_to_bool(dict.get(os.environ.get('next_page_path'))):
                page_counter += 1
                url = os.environ.get("baseurl") + path
                url = call_url(url, url_parameters, str(page_counter))
            else:
                has_more_results = False
        logger.info('Returning entities from %i pages', page_counter)


    def get_paged_entities(self, path, url_parameters):
        print("getting all paged")
        return self.__get_all_paged_entities(path, url_parameters)

    def get(self, path):
        print('getting all users')
        return self.__get_all_users(path)

data_access_layer = DataAccess()


def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'

def call_url(base_url, url_parameters, page):
    call_url = base_url
    first = True
    for k, v in url_parameters.items():
        if first:
            if k == os.environ.get('startpage'):
                call_url += '?' + k + '=' + page
            else:
                call_url += '?' + k + '=' + v
        else:
            if  k == os.environ.get('startpage'):
                call_url += '&' + k + '=' + page
            else:
                call_url += '&' + k + '=' + v
        first = False
    return call_url

def str_to_bool(string_input):
    return str(string_input).lower() == "true"


@app.route("/<path:path>", methods=["GET"])
def get(path):
    entities = data_access_layer.get_paged_entities(path, request.args)
    return Response(
        stream_json(entities),
        mimetype='application/json'
    )


@app.route("/", methods=[ "POST"])
def postreceiver():
    entities = request.get_json()
    header = json.loads(os.environ.get('headers').replace("'","\""))
    logger.info("Receiving entities")

    response_list = []
    client = app.test_client()
    statuscode = None
    if not isinstance(entities,list):
        entities = [entities]
    for entity in entities:
        for k,v in entity.items():
            if k == os.environ.get('post_url', 'post_url'):
                logger.info("processing: " + v)
                response = client.get(v, headers=header)
                data = response.data
                statuscode = response.status_code
                if not len(data.decode("utf-8")) == 4:
                    response_list += json.loads(data.decode("utf-8"))

    if len(response_list)== 0:
        response_list.append({})
    return Response(json.dumps(response_list),status=statuscode, mimetype='application/json')


@app.route("/notpaged/", methods=["POST"])
def notpaged():
    baseurl = os.environ.get('baseurl')

    entities = request.get_json()
    header = json.loads(os.environ.get('headers').replace("'","\""))

    logger.info("Receiving entities")

    if not isinstance(entities, list):
        entities = [entities]
    for entity in entities:
        for k, v in entity.items():
            if k == os.environ.get('post_url', 'post_url'):
                url = baseurl+v
        logger.info("Fetching entity with url: " + str(url))
        response = requests.get(url, headers=header)
        if response.status_code is not 200:
            logger.error("Got Error Code: " + str(response.status_code) + " with text: " + response.text)
            return Response(response.text, status=response.status_code, mimetype='application/json')
        entity[prop] = {
            "status_code": response.status_code,
            "response_text": json.loads(response.text)

        }
    logger.info("Prosessed " + str(len(entities)) + " entities")
    return Response(json.dumps(entities), status=response.status_code, mimetype='application/json')


if __name__ == '__main__':
    app.run(threaded=True, debug=True, host='0.0.0.0', port=os.environ.get('port',5002))
