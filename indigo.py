# This file is part of indigo_cffi.
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Python classes to interface to indigo.

Because of the way callbacks are defined inside the indigo C, the callbacks cannot be passed an indigoPy class pointer,
so indigoPy is implemented as a singleton, with activeIndigoPy being the active instance.
"""
import sys
import time
import socket
import logging

from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as etree

from _indigo import ffi, lib
from _indigo.lib import indigo_connect_server
from _indigo.lib import indigo_disconnect_server
from _indigo.lib import indigo_start
from _indigo.lib import indigo_build_client

import indigoProperties

activeIndigoPy = None

# class indigoPy contains all functionality for external interaction with indigo

class indigoPy:

    indigoPropDict = {}
    indigoHost = None
    indigoPort = None
    indigoDeviceName = None
    indigoClientPtr = None
    indigoSocket = None

    serverDelay = 1
    maxWaitCount = 30

    indigoServerPtr = None
    indigoServer = None
    
    def __init__(self, deviceName, serverHost=None, serverPort=None):
        self.indigoDeviceName = deviceName
        if serverHost is not None:
            self.indigoHost = serverHost
        else:
            self.indigoHost = "localhost"

        if serverPort is not None:
            self.indigoPort = serverPort
        else:
            self.indigoPort = 7624

        self.updatePending = False
        self.updatePendingName = ''


    def start(self):
        global activeIndigoPy

        if activeIndigoPy is not None:
            raise RuntimeError(f"An indigoPy instance is already active ")
            
        activeIndigoPy = self
        
        result = indigo_start()
        if result != lib.INDIGO_OK:
            raise RuntimeError(f"indigo start failed with error {result}")

        # build the client with callbacks connected

        self.indigoClientPtr = indigo_build_client(b"indigoPy", lib.attach_cb, lib.define_property_cb, lib.update_property_cb, lib.delete_property_cb, lib.send_message_cb, lib.detach_cb)
        
        # Connect to the indigo server

        self.indigoServerPtr = ffi.new("indigo_server_entry * *")  # Note that the indigo_server_entry is serverPtr[0][0]

        result = indigo_connect_server(b"localhost",b"localhost",7624,self.indigoServerPtr)

        if result != lib.INDIGO_OK:
            raise RuntimeError(f"indigo_connect_server failed with error {result}")

        time.sleep(self.serverDelay)

        # get server socket

        self.indigoServer = self.indigoServerPtr[0][0]
        fd=self.indigoServer.socket
        self.indigoSocket = socket.fromfd(fd,socket.AF_INET,socket.SOCK_STREAM)


    def stop(self):
        global activeIndigoPy

        result = indigo_disconnect_server(self.indigoServerPtr[0])
        if result != lib.INDIGO_OK:
            raise RuntimeError(f"indigo_disconnect_server failed with error {result}")

        activeIndigoPy = None
        
    def sendXml(self, xmlString):
        logging.debug('------------- Sending: %s', xmlString)
        self.indigoSocket.send(xmlString)
        time.sleep(self.serverDelay)

    def sendCommand(self, devName, propName, propItemDict):
        # assumed that this is a "newXXX" command
        
        # get dict entry for propName.  If not found, error for now

        dictKey = f"{self.fullIndigoDevName(devName)}.{bytes(propName, 'utf-8')}"

        if not dictKey in self.indigoPropDict:
            logging.warning(f"sendCommand: {dictKey} not in known properties")
            return

        dictProps = self.indigoPropDict[dictKey]

        # poll loop, waiting for self.updatePending = False, set by update_property
        # NEED TIMEOUT

        waitCount = 0
        while self.updatePending and waitCount<self.maxWaitCount:
            time.sleep(self.serverDelay)
            waitCount += 1

        if waitCount >= self.maxWaitCount:
            logging.warning(f"sendCommand: timed out waiting for server update")
            return

        # set self.updatePending = True, self.updatePendingName = propName

        self.updatePending = True
        self.updatePendingName = dictKey

        # build XML for command - depends on property Type

        propType = dictProps[0]

        if propType == lib.INDIGO_TEXT_VECTOR:
            xmlRootTag = 'newTextVector'
            xmlInnerTag = 'oneText'

        elif propType == lib.INDIGO_NUMBER_VECTOR:
            xmlRootTag = 'newNumberVector'
            xmlInnerTag = 'oneNumber'
            
        elif propType == lib.INDIGO_SWITCH_VECTOR:
            xmlRootTag = 'newSwitchVector'
            xmlInnerTag = 'oneSwitch'
            
        else:
            logging.warning(f"sendCommand error: proptype = {propType}.  Command not sent")
            return
        
        xmlString = self.buildXmlCommand(devName, propName, xmlRootTag, xmlInnerTag, propItemDict) 
        self.sendXml(xmlString)
        
    def buildXmlCommand(self, devName, propName, xmlRootTag, xmlInnerTag, propItemDict):
        root = Element(xmlRootTag)
        root.set('device', devName)
        root.set('name', propName)
        for key in propItemDict:
            newEl = Element(xmlInnerTag, attrib={'name':key})
            newEl.text = propItemDict[key]
            root.append(newEl)

        return etree.tostring(root)

    def define_property(self, propPtr):
        pending = True
        (key, value) = indigoProperties.buildPropDictItem(propPtr)
        self.indigoPropDict[key] = value

    def update_property(self, propPtr):
        (key, value) = indigoProperties.buildPropDictItem(propPtr)

        if self.updatePendingName == key:
            self.updatePendingName = ''
            self.updatePending = False
            
        # find property in indigoPropDict - error if not present
        if not key in self.indigoPropDict:
            logging.warning(f"update_property error: {key} not in indigoPropDict for update")
        else:
            # update the value
            self.indigoPropDict[key] = value
            logging.debug("update_property:")
            indigoProperties.printPropDictEntry(key, value, logging.DEBUG)

    def delete_property(self, propPtr):
        (key, value) = indigoProperties.buildPropDictItem(propPtr)

        if self.updatePendingName == key:
            self.updatePendingName = ''
            self.updatePending = False
            
        # find property in indigoPropDict - error if not present
        if not key in self.indigoPropDict:
            logging.warning(f"delete_property error: {key} not in indigoPropDict for delete")
        else:
            self.indigoPropDict.pop(key)
            
    def printProperties(self):
        for key in self.indigoPropDict.keys():
            indigoProperties.printPropDictEntry(key, self.indigoPropDict[key])
        

    def fullIndigoDevName(self, devName):
        return bytes(f"{devName} @ {self.indigoHost}", 'utf-8')

# Callbacks can access members of the (only) active indigoPy through activeIndigoPy

@ffi.def_extern()
def attach_cb(client):
    logging.debug('attach client')
    return 0
            
@ffi.def_extern()
def define_property_cb(client, device, propPtr, message):
    activeIndigoPy.define_property(propPtr)
    prop = propPtr[0]
    logging.debug('define_property: %s %s', ffi.string(prop.device), ffi.string(prop.name))
    return 0

@ffi.def_extern()
def update_property_cb(client, device, propPtr, message):
    activeIndigoPy.update_property(propPtr)
    prop = propPtr[0]
    logging.debug('update_property: %s %s', ffi.string(prop.device), ffi.string(prop.name))
    return 0

@ffi.def_extern()
def delete_property_cb(client, device, propPtr, message):
    activeIndigoPy.delete_property(propPtr)
    prop = propPtr[0]
    logging.debug('delete_property: %s %s', ffi.string(prop.device), ffi.string(prop.name))
    return 0

@ffi.def_extern()
def send_message_cb(client, device, message):
    logging.debug('send_message %s', ffi.string(message))
    return 0

@ffi.def_extern()
def detach_cb(client):
    logging.debug('detach client')
    return 0

