from __future__ import absolute_import

from zope.interface import Interface


class IDataStore(Interface):

    def save(datastream):
        """ Store data from datastream to the data store """

    def load(datastream):
        """ Retrieve data from the data store to a datastream"""


class IDataStoreFactory(Interface):

    def create():
        """ Create a data store manager for the data object """
