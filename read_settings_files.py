# Read files specific to Theia_lensIQ_GUI.py
#
# v.1.0.0 250811 extracted from Theia_lensIQ_GUI v.2.5.7 

from PSG_license import PySimpleGUI_License
import PySimpleGUI as sg
import utilities
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import json
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def readSettingsFile(settingsFileName:str) -> dict:
    '''
    Read the settings file data
    ### input: 
    - settingsFileName: the short name of the settings file
    ### return: 
    [settings values]
    '''
    appDir, settingsFileName, newFile = utilities.getSettingsFileName(appDataFolder='TheiaLensGUI', settingsFileName=settingsFileName)
    if newFile:
        settings = sg.UserSettings(filename=settingsFileName, path=appDir)
        settings['comPort'] = ''
        settings['lastLensFamily'] = ''
    settings = sg.UserSettings(filename=settingsFileName, path=appDir, autosave=True)
    return settings

# read lens data file
def readLensLimitsFile(lensDataFileName:str) -> dict:
    '''
    Read the lens data file from the AppData/local folder.  
    ### return:  
    [lens data]
    '''
    lensData = None
    homeDir = os.path.expanduser("~")
    appDir = os.path.join(homeDir, 'AppData', 'Local', 'TheiaLensGUI', 'data')
    lensDataFullFileName = f'{appDir}\\{lensDataFileName}'
    if not os.path.exists(lensDataFullFileName):
        log.warning(f'No data file in {lensDataFullFileName}.  Find the "limits.json" file that contains lens limit values. ')
        # Open the data file and save to appDir
        Tk().withdraw() 
        filename = askopenfilename(defaultextension='.json', filetypes=[('JSON File', '.json')], title="Open limits.json file")
        if filename:
            with open(filename, 'r') as f:
                lensData = json.load(f)
            with open(lensDataFullFileName, 'w') as f:
                json.dump(lensData, f)
        else: 
            return None
    else:
        lensData = json.load(open(lensDataFullFileName))
    return lensData