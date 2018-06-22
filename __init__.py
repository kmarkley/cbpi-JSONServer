# -*- coding: utf-8 -*-
################################################################################

from modules import cbpi
from ast import literal_eval as literal
import time
import json
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import parse_qs
from threading import Thread


from modules.core.step import StepBase

################################################################################
# Globals
################################################################################

DEFAULT_SERVER_PORT = 8008
DEFAULT_CACHE_AGE = 5
TIME_LAST_DATA = 0.0

PAYLOAD = dict()

################################################################################
# cbpi methods
################################################################################
@cbpi.initalizer(order=99999)
def init(cbpi):
    cbpi.app.logger.info("JSONServer: start init")

    try:

        cbpi.app.logger.info("JSONServer: initiate parameters")
        # setup json server parameters
        param = cbpi.get_config_parameter('json_server_port', None)
        if param is None:
            cbpi.app.logger.info("JSONServer: create json_server_port system parameter")
            try:
                cbpi.add_config_parameter('json_server_port', DEFAULT_SERVER_PORT, 'number', "JSON Server Port")
            except Exception as e:
                cbpi.app.logger.error("JSONServer: {}".format(e))

        param = cbpi.get_config_parameter('json_cache_age', None)
        if param is None:
            cbpi.app.logger.info("JSONServer: create json_cache_age system parameter")
            try:
                cbpi.add_config_parameter('json_cache_age', DEFAULT_CACHE_AGE, 'number', "JSON Data Cache Age (Seconds)")
            except Exception as e:
                cbpi.app.logger.error("JSONServer: {}".format(e))

        cbpi.app.logger.info("JSONServer: initiate http server")
        port = int(cbpi.get_config_parameter('json_server_port', DEFAULT_SERVER_PORT))
        httpd = HTTPServer(('',port), cbpi_json_request_handler)
        server_thread = Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        cbpi.app.logger.info("JSONServer: end init")

    except Exception as e:
        cbpi.app.logger.error(repr(e))


################################################################################
# http server
################################################################################
class cbpi_json_request_handler(BaseHTTPRequestHandler):

    def do_GET (self):
        cbpi.app.logger.info("JSONServer: GET request received")
        try:
            update_payload()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(PAYLOAD))
        except Exception as e:
            cbpi.app.logger.error(repr(e))

################################################################################
# server helpers
################################################################################
def update_payload():
    global TIME_LAST_DATA, PAYLOAD

    if time.time() >= TIME_LAST_DATA + int(cbpi.get_config_parameter('json_cache_age', DEFAULT_CACHE_AGE)):

        TIME_LAST_DATA = time.time()


        # config
        unit = u'°{}'.format(cbpi.get_config_parameter('unit', 'C'))
        PAYLOAD['config'] = {
            'unit'      : unit,
            'brew_name' : strClean(cbpi.get_config_parameter('brew_name', '')),
            'brewery'   : strClean(cbpi.get_config_parameter('brewery_name', '')),
            }

        # sensors
        PAYLOAD['sensors'] = dict()
        for key, sensor in cbpi.cache.get('sensors').items():
            PAYLOAD['sensors'][key] = {
                'id'     : strClean(sensor.id),
                'name'   : strClean(sensor.name),
                'type'   : strClean(sensor.type),
                'value'  : float(sensor.instance.last_value),
                'unit'   : sensor.instance.get_unit().decode('utf-8'),
                }

        # actors
        PAYLOAD['actors'] = dict()
        for key, actor in cbpi.cache.get('actors').items():
            PAYLOAD['actors'][key] = {
            'id'    : intClean(actor.id),
            'name'  : strClean(actor.name),
            'type'  : strClean(actor.type),
            'state' : bool(actor.state),
            'power' : numClean(actor.power),
            }

        # kettles
        PAYLOAD['kettles'] = dict()
        for key, kettle in cbpi.cache.get('kettle').items():
            PAYLOAD['kettles'][key] = {
                'id'       : intClean(kettle.id),
                'name'     : strClean(kettle.name),
                'logic'    : strClean(kettle.logic),
                'state'    : kettle.state,
                'sensor'   : intClean(kettle.sensor),
                'heater'   : intClean(kettle.heater),
                'agitator' : intClean(kettle.agitator),
                'target'   : numClean(kettle.target_temp),
                'unit'     : unit,
                }

        # fermenters
        PAYLOAD['fermenters'] = dict()
        for key, fermenter in cbpi.cache.get('fermenter').items():
            PAYLOAD['fermenters'][key] = {
                'id'      : strClean(fermenter.id),
                'name'    : strClean(fermenter.name),
                'logic'   : strClean(fermenter.logic),
                'brew'    : strClean(fermenter.brewname),
                'sensor1' : intClean(fermenter.sensor),
                'sensor2' : intClean(fermenter.sensor2),
                'sensor3' : intClean(fermenter.sensor3),
                'cooler'  : intClean(fermenter.cooler),
                'heater'  : intClean(fermenter.heater),
                'state'   : fermenter.state,
                'target'  : numClean(fermenter.target_temp),
                'unit'    : unit,
                }

            #fermenter steps
            step_list = list()
            for step in fermenter.steps:
                step_list.append({
                    'id'        : intClean(step.id),
                    'order'     : intClean(step.order),
                    'name'      : strClean(step.name),
                    'temp'      : numClean(step.temp),
                    'days'      : numClean(step.days),
                    'hours'     : numClean(step.hours),
                    'minutes'   : numClean(step.minutes),
                    'state'     : step.state,
                    'direction' : strClean(step.direction),
                    'start'     : step.start,
                    'end'       : step.end,
                    })
            PAYLOAD['fermenters'][key]['steps'] = tuple(sorted(step_list, key=lambda k: k['order']))

        # brew steps
        step_list = list()
        for step in cbpi.cache.get('steps')():
            step_list.append({
                'id'    : intClean(step.id),
                'name'  : strClean(step.name),
                'type'  : strClean(step.type),
                'order' : intClean(step.order),
                'start' : step.start,
                'end'   : step.end,
                'state' : step.state,
                })
        PAYLOAD['steps'] = tuple(sorted(step_list, key=lambda k: k['order']))

        # messages
        PAYLOAD['messages'] = cbpi.cache.get('messages')

        cbpi.app.logger.info("JSONServer: JSON data updated")

################################################################################
# utilities
################################################################################
def intClean(value):
    try:
        return int(value)
    except:
        return 0

def numClean(value):
    if isinstance(value, (int,float)):
        return value
    elif isinstance(value, basestring):
        return literal(value)
    else:
        return 0

def strClean(value):
    if isinstance(value, (basestring, int, float, bool)):
        return unicode(value)
    else:
        return u''
