#!/usr/bin/env python

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


import indigo
import time

if __name__ == "__main__":

    # Start up the indigo instanc
    
    indpy = indigo.indigoPy('takeExposure')

    indpy.start()

    indpy.printProperties()
    
    # sequence of commands

    indpy.sendXml("<getProperties version='2.0'>")
    time.sleep(5)
#    indpy.sendXml("<newSwitchVector device='Imager Agent' name='FILTER_CCD_LIST' state='Ok'> <oneSwitch name='None'>Off</oneSwitch> <oneSwitch name='ZWO ASI1600MM Pro #0'>On</oneSwitch></newSwitchVector>")
    time.sleep(5)
    indpy.sendXml("<newSwitchVector device='ZWO ASI1600MM Pro #0' name='CONNECTION' state='Ok'> <oneSwitch name='DISCONNECTED'>'Off'</oneSwitch> <oneSwitch name='CONNECTED'>'On'</oneSwitch></newSwitchVector>")
    time.sleep(5)
    indpy.sendXml("<newSwitchVector device='ZWO ASI1600MM Pro #0' name='CCD_UPLOAD_MODE' state='Ok'><oneSwitch name='CLIENT'>'Off'</oneSwitch><oneSwitch name='LOCAL'>'On'</oneSwitch><oneSwitch name='BOTH'>'Off'</oneSwitch><oneSwitch name='PREVIEW'>'On'</oneSwitch> <oneSwitch name='PREVIEW_LOCAL'>'Off'</oneSwitch></newSwitchVector>")
#    indpy.sendXml("<newTextVector device='Imager Agent' name='CCD_LOCAL_MODE'> <oneText name='DIR'>'/home/taxelrod/tmp'</oneText></newTextVector>")
    time.sleep(5)
    indpy.sendXml("<newNumberVector device='ZWO ASI1600MM Pro #0' name='CCD_EXPOSURE'> <oneNumber name='EXPOSURE'>'1'</oneNumber></newNumberVector>")

    # Disconnect server

    time.sleep(5)

    indpy.stop()
