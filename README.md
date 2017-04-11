# Paged REST proxy
[![Build Status](https://travis-ci.org/sesam-community/sesam-paged-rest-proxy.svg?branch=master)](https://travis-ci.org/sesam-community/paged-rest-proxy)

A small microservice to get/post entities from/to a REST api.

This microservice needs information about startpage and number of entities per page.


##### POST example paged-entity
```
{
  "_id":"someid",
  "post_url": "example?q=(exampleid!=1)&count=10&startPage=1"
}
```
The microservice will then create calls and return all data from all of the pages the REST api returns.
This POST call needs to be sent to `microservice:port/`
##### RETURNED example paged-entity
```
[
    {
        "id":"2",
        "foo": "bar"
    },
    {
        "id":"3",
        "foo": "baz"
    }
]
```

##### POST example notpaged-entity
```
{
  "_id":"someid",
  "post_url": "example/exampleid2/info"
}
```
The microservice will then create calls and return data from a single page.
This POST call needs to be sent to `microservice:port/notpaged/`
##### RETURNED example notpaged-entity
```
[
    {
        "_id": "someid",
        "post_url": "example/exampleid2/info",
        "response": {
            "response_text": {
            "foo": "bar",
            "status_code": 200
            }
    }
]
```

##### GET example paged-entity - pipe config
```
[
    "_id": "example-paged-source",
    "type": "pipe",
    "source": {
        "type": "json",
        "system": "example-service",
        "url": "example?count=2&startPage=1&includeDetails=true"
    }
]
```
This configuration will go through all the pages and return all entities that exists from x page.
If the total amount of entities in example is 20 you can also say count=20. Then all entities will be on page one.

You can also have up to 2 slashes from base url like `example/foo/bar?count=10&startPage=1&includeDetails=true`

##### Example result from GET method
```
{
    "facets": [],
    "hasMoreResults": true,
    "itemsPerPage": 2,
    "results": [
        {
            {
                "id": "1",
                "foo": "bar"
            },
            {
                "id": "1",
                "foo": "baz"
            }
        }
    ]
}
```
This will result into returned entities:
```
[
    {
        "id": "1",
        "foo": "bar"
    },
    {
        "id": "1",
        "foo": "baz"
    }
]
```

##### Example configuration:

```
{
  "_id": "example-service",
  "type": "system:microservice",
  "docker": {
    "environment": {
      "baseurl": "https://some-rest-service.com/v1/",
      "entity_property": "results", #in which property your entities reside in the result from GET
      "pagesize": "count",
      "startpage": "startPage",
      "header_values": "Content-Type,Some-certificate",
      # optional values below
      "post_url": "post_url", #post_url for POST
      "response_property": "response" #element name in POST response
    },
    "image": "sesamcommunity/paged-rest-proxy:latest",
    "port": 5001
  }
}
```

