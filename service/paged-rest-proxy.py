import json

from flask import Flask, request, Response
import os
import requests
import logging

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
header_values= os.environ.get('header_values', 'Content-Type').split(',')
response = None

@app.route("/", methods=[ "POST"])
def postreceiver():
    entities = request.get_json()
    header = {}
    logger.info("Receiving entities")
    for k,v in dict(request.headers).items():
        if k in header_values:
            header[k] = v

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
    header = {}
    logger.info("Receiving entities")
    for k, v in dict(request.headers).items():
        if k in header_values:
            header[k] = v
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

@app.route("/<url>", methods=["GET"])
def receiver(url):
    baseurl = os.environ.get('baseurl') + url + "?"

    response_list = processor(baseurl, request)
    if len(response_list)== 0:
        response_list.append({})
    elif response_list[0] == "Error":
        return Response(response_list[1], status=response_list[2], mimetype='application/json')
    return Response(response=json.dumps(response_list), mimetype='application/json')

@app.route("/<url1>/<url2>", methods=["GET"])
def receiver2(url1, url2):
    baseurl = os.environ.get('baseurl') + url1 + "/" + url2 + "?"
    response_list = processor(baseurl, request)
    if len(response_list)== 0:
        response_list.append({})
    elif response_list[0] == "Error":
        return Response(response_list[1], status=response_list[2], mimetype='application/json')
    return Response(response=json.dumps(response_list), mimetype='application/json')

@app.route("/<url1>/<url2>/<url3>", methods=["GET"])
def receiver3(url1, url2, url3):
    baseurl = os.environ.get('baseurl') + url1 + "/" + url2 + "/" + url3 + "?"
    response_list = processor(baseurl, request)
    if len(response_list)== 0:
        response_list.append({})
    elif response_list[0] == "Error":
        return Response(response_list[1], status=response_list[2], mimetype='application/json')
    return Response(response=json.dumps(response_list), mimetype='application/json')

def processor(baseurl, request):
    header = {}

    for k, v in dict(request.headers).items():
        if k in header_values:
            header[k] = v
    pagesize = int(request.args.get(os.environ.get('pagesize')))
    startPage = int(request.args.get(os.environ.get('startpage')))
    logger.info("Processing data from baseurl: " + str(baseurl))

    for k, v in request.args.to_dict(True).items():
        if (k != os.environ.get('pagesize')) and (k != os.environ.get('startpage')):
            baseurl += k + "=" + v + "&"

    response_list = []
    pagecounter = 0

    response = call_service(baseurl,pagesize,startPage,header)
    logger.info(response)
    if response.status_code is not 200:
        logger.error("Got Error Code: " + str(response.status_code) + " with text: " + response.text)
        response_list.append(str("Error"))
        response_list.append(str(response.text))
        response_list.append(str(response.status_code))
        return response_list
    else:
        if not next_page(json.loads(response.text)):
            response_list += get_entities(json.loads(response.text))

    while next_page(json.loads(response.text)):

        response = call_service(baseurl, pagesize, startPage+pagecounter, header)
        if response.status_code is not 200:
            logger.error("Got Error Code: " + str(response.status_code) + " with text: " + response.text)
            response_list.append(str("Error"))
            response_list.append(str(response.text))
            response_list.append(str(response.status_code))
            return response_list

        response_list += get_entities(json.loads(response.text))
        logger.info("Got status code " + str(response.status_code) + " from page. "+ str(startPage+pagecounter) + ". Processing pagedata.")
        pagecounter +=1

    logger.info("fetched " +str(pagecounter) + " pages from start page " + str(startPage))
    return response_list

def next_page(hasnext):
    has_next = hasnext.get(os.environ.get('next_page_property', 'hasMoreResults'))
    logger.info("Next page exists: " + str(has_next))
    return has_next

def get_entities(entities):
    for k, v in entities.items():
        if k == os.environ.get('entity_property'):
            return v

def call_service(baseurl, pagesize,startPage,header):
    request = requests.get(
        baseurl + os.environ.get('pagesize') + "=" + str(pagesize) + "&" + os.environ.get('startpage') + "=" + str(startPage),
        headers=header)
    return request

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('port',5001))
