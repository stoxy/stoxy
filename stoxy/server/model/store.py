from __future__ import absolute_import

from zope.interface import Interface


class IDataStore(Interface):

    def save(data):
        """ Store data to the data store """

    def load():
        """ Retrieve data from the data store """


class IDataStoreFactory(Interface):

    def create():
        """ Create a data store manager for the data object """
