from apscheduler.schedulers.background import BackgroundScheduler
import connexion
from connexion import NoContent
import yaml
import logging
import logging.config
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from base import Base
from event import Event
import requests
import json
from flask_cors import CORS, cross_origin
import sqlite3
import os


if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
    datastore = app_config['datastore']

with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')
logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

if os.path.exists(datastore['filename']) == False:
    conn = sqlite3.connect(datastore['filename'])
    c = conn.cursor()
    c.execute('''
            CREATE TABLE events
            (id INTEGER PRIMARY KEY ASC,
            num_devices INTEGER NOT NULL,
            max_device_latency INTEGER NOT NULL,
            num_networks INTEGER NOT NULL,
            max_network_device_count INTEGER NOT NULL,
            last_update VARCHAR(100) NOT NULL)
            ''')

    conn.commit()
    conn.close()

def get_health():
    return 200

DB_ENGINE = create_engine(f"sqlite:///{datastore['filename']}")
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

def get_stats():
    session = DB_SESSION()
    logger.info(f"request started")
    latest_row = session.query(Event).order_by(Event.id.desc()).first()
    if latest_row is None:
        logger.error("Latest row for get_stats attempted to load but do not exist")
        return "Statistics do not exist", 404
    else:
        network_stats = {'num_devices': latest_row.num_devices,
                         'max_device_latency': latest_row.max_device_latency,
                         'num_networks': latest_row.num_networks,
                         'max_network_device_count': latest_row.max_network_device_count,
                         'last_updated': latest_row.last_update}
        logger.debug(f"{network_stats}")
        logger.info(f"get_stats request completed.")
        return network_stats, 200


def populate_stats():
    """ Periodically update stats """
    logger.info(f"Start Periodic Processing")
    session = DB_SESSION()
    latest_row = session.query(Event).order_by(Event.id.desc()).first()

    if latest_row is None:
        last_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        print(last_update)
    else:
        last_update = latest_row.last_update

    new_time = datetime.datetime.now()
    current_timestamp = new_time.strftime("%Y-%m-%d %H:%M:%S.%f")

    request_params = {'start_timestamp': f"{last_update}", 'end_timestamp': f"{current_timestamp}"}

    network_request_uri = f"{app_config['eventstore']['url']}/networks"
    network_response = requests.get(network_request_uri, params=request_params)

    device_request_uri = f"{app_config['eventstore']['url']}/devices"
    device_response = requests.get(device_request_uri, params=request_params)

    if network_response.status_code != 200 or device_response.status_code != 200:
        logger.error("failed to get events")

    network_body = network_response.json()
    num_networks = len(network_body)

    device_body = device_response.json()
    num_devices = len(device_body)

    logger.info(f"number of events received were {num_devices + num_networks}")


    prev_event = session.query(Event).order_by(Event.id.desc()).first()

    if prev_event is not None:
        new_num_devices = prev_event.num_devices + num_devices
        new_num_networks = prev_event.num_networks + num_networks
        max_network_device_count = prev_event.max_network_device_count
        max_device_latency = prev_event.max_device_latency
    else:
        new_num_devices = 0
        new_num_networks = 0
        max_device_latency = 0
        max_network_device_count = 0

    if len(network_body) > 0:
        for network in network_body:
            if network['device_count'] > max_network_device_count:
                max_network_device_count = network['device_count']
            logger.debug(f"Stored event post_network request with a trace id of {network['trace_id']}")

    if len(device_body) > 0:
        for device in device_body:
            if device['latency'] > max_device_latency:
                max_device_latency = device['latency']
            logger.debug(f"Stored event post_network request with a trace id of {device['trace_id']}")

    event = Event(new_num_devices, max_device_latency, new_num_networks, max_network_device_count, new_time)

    logger.debug(f"new values num_device={num_devices}, max_device_latency={max_device_latency}, "
                 f"num_networks={num_networks}, max_network_device_count={max_network_device_count}, "
                 f"last_update={new_time}")

    logger.info(f"Ended Periodic Processing")
    session.add(event)
    session.commit()
    session.close()


def init_scheduler():
    schedule = BackgroundScheduler(daemon=True)
    schedule.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['period_sec'])
    schedule.start()

#Added Cors now
app = connexion.FlaskApp(__name__, specification_dir='')

app.add_api("openapi.yml",
            base_path="/processing",
            strict_validation=True,
            validate_responses=True)

if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'

if __name__ == "__main__":
    init_scheduler()
    # app.debug = True
    app.run(port=8100)

# legacy stuff
# headers = {'User-Agent': 'PostmanRuntime/7.29.2'}
# # request_params = {'last_update': datetime.datetime.now()}
# request_params = {'last_update': "2022-10-04 10:05:02.000001"}
# network_request_uri = f"{app_config['eventstore']['url']}/networks"
# network_response = requests.get(network_request_uri, params=request_params)
# network_body = network_response.json()
# num_networks = len(network_body)
# max_network_device_count = 0
# if len(network_body) > 0:
#     for network in network_body:
#         if network['device_count'] > max_network_device_count:
#             max_network_device_count = network['device_count']
#
# device_request_uri = f"{app_config['eventstore']['url']}/devices"
# device_response = requests.get(device_request_uri, params=request_params)
# device_body = device_response.json()
# num_devices = len(device_body)
# max_device_latency = 0
# if len(device_body) > 0:
#     for device in device_body:
#         if device['latency'] > max_device_latency:
#             max_device_latency = device['latency']
#
# # num_devices = session.query(Device).count()
# # max_device_latency = session.query(func.max(Device.latency)).all()[0][0]
# # num_networks = session.query(Network).count()
# # max_network_device_count = session.query(func.max(Network.device_count)).all()[0][0]
#
# network_stats = [{'num_devices': num_devices,
#                   'max_device_latency': max_device_latency,
#                   'num_networks': num_networks,
#                   'max_network_device_count': max_network_device_count}]
