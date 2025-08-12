# Utility functions for Theia_lensIQ_GUI
#
# v.1.0.0 250811 Exctracted functions from Theia_lensIQ_GUI.py v.2.5.7


import os
import sys
import logging
from pathlib import Path
import tomllib
import serial.tools.list_ports

# set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# read main program revision from pyproject.toml
pyprojectPath = Path(__file__).parent / 'pyproject.toml'
with open(pyprojectPath, 'rb') as f:
    pyproject = tomllib.load(f)
    revision = pyproject['project']['version']

# Find file paths based on development or deployment.  
def resourcePath(resource):
    '''
    Set the base path of the exe or development folder
    ### input
    - resource: the resource path to find the path to
    ### return
    [basePath/resourceName]
    '''
    # Get absolute path to resource, works for dev and for PyInstaller
    base_path = os.path.dirname(sys.executable)
    if not os.path.exists(os.path.join(base_path, "data")):  # Check for data folder only available with exe file
        # use development path
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, resource)

# serachComPorts
def searchComPorts():
    '''
    Search for connected com ports for selecting MCR motor controllers
    ### return
    [list of com ports]
    '''
    ports = serial.tools.list_ports.comports()
    portList = []
    for port, desc, hwid in sorted(ports):
        log.info("Ports: {} [{}]".format(desc, hwid))
        portList.append(port)
    return portList

# get the saved settings file path and name
def getSettingsFileName(appDataFolder:str, settingsFileName:str) -> tuple[str, str, bool]:
    '''
    Verify the existance of PySimpleGUI settings file. 
    Create a file in the AppData/Local folders if it doesn't exist. 
    ### input:  
    - appDataFolder: the name of the AppData folder for persistant storage ('TheiaLensGUI')
    - settingsFileName: the name of the settings file
    ### return:  
    - appDir: the AppData directory
    - settingsFullFileName: the full path to the settings file
    - newFile (bool): set if new settings file created
    '''
    newFile = False
    homeDir = os.path.expanduser("~")
    appDir = os.path.join(homeDir, 'AppData', 'Local', appDataFolder)
    if not os.path.exists(appDir):
        os.mkdir(appDir)
    settingsFullFileName = f'{appDir}\\{settingsFileName}'
    if not os.path.exists(settingsFullFileName):
        log.info(f'New settings file created {settingsFullFileName}')
        newFile = True
    return appDir, settingsFullFileName, newFile