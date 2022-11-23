from sqlalchemy import Column, Integer, String, DateTime, Numeric
from base import Base
import datetime


class Event(Base):
    """ Events """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    num_devices = Column(Integer, nullable=False)
    max_device_latency = Column(Integer, nullable=False)
    num_networks = Column(Integer, nullable=False)
    max_network_device_count = Column(Integer, nullable=False)
    last_update = Column(DateTime, nullable=False)

    def __init__(self, num_devices, max_device_latency, num_networks, max_network_device_count, last_update):
        """ Initializes a new device with attributes """
        self.num_devices = num_devices
        self.max_device_latency = max_device_latency
        self.num_networks = num_networks
        self.max_network_device_count = max_network_device_count
        self.last_update = last_update

    def to_dict(self):
        device_dictionary = {'num_devices': self.num_devices, 'max_device_latency': self.max_device_latency,
                             'num_networks': self.num_networks,
                             'max_network_device_count': self.max_network_device_count,
                             'last_update': self.last_update}

        return device_dictionary
