# Live GUI motor control and Lens IQ engineering unit conversion application
# (c) 2025 Theia Technologies LLC
# contact Mark Peterson at mpeterson@theiatech.com for more information

from PSG_license import PySimpleGUI_License 
import PySimpleGUI as sg
import logging
import TheiaMCR
import sys
import utilities
import GUI_setup
import read_settings_files as settingsFiles
import GUI_actions

# lensIQ imports
ENABLE_LENS_IQ_FUNCTIONS = False
if ENABLE_LENS_IQ_FUNCTIONS: import lensIQ_expansion

# global variable
MCR = None
mainGUI = None

# logging setup
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')
# set TheiaMCR sub module log level
MCRDebugLogLevel = False

settingsFileName = 'Motor control config.json'
settingsIconPath = utilities.resourcePath('data/cog.png')    # location of the gear icon for settings
lensDataFileName = 'limits.json'                   # lens data (names and extents)
dataSetQRCode = utilities.resourcePath('data/QR-Dropbox-lensIQ-dataset.png')    # QR code for the lens data file


# create the main window GUI layout
def createMainGUI():
    '''
    Call the GUI creation function in GUI_setup.py.  
    Fill in the values of some fields.  
    '''
    global mainGUI
    mainGUI = GUI_setup.LensIQGUI(settingsIconPath=settingsIconPath, IQFunctions=IQEP if ENABLE_LENS_IQ_FUNCTIONS else None)

    # field updates
    mainGUI.window['cp_lensFam'].update(value = lastLensFamily, values = lensFamiliesList, size=(18,10))
    mainGUI.window['cp_port'].update(value = comPort, values = sorted(comPortList), size=(18,10))

    actions = GUI_actions.GUIActions(mainGUI) 
    actions.setStatus('notInit')
    actions.enableLiveFrame(False)
    return actions
    
# setup lens parameters
def selectLens(name:str) -> tuple[str, list]:
    '''
    Set up lens parameters focus steps, focus PI step, zoom steps, zoom PI step, iris steps. 
    Based on lens model number, return the configuration and serial number prefix ('TW90').  
    ### input
    - name: lens family name (see lensFamiliesList variable for names. )
    ### return
    [
        prefix = ['TW50' | 'TW60' | 'TW80' | 'TW90' | 'TW46'],
        lensConfig = [zoom steps, zoom PI, focus steps, focus PI, iris steps]
    '''
    log.info(f"Select {name}")
    prefix = lensData[name]['fam']
    lensConfig = [lensData[name]['zoomSteps'], lensData[name]['zoomPI'], lensData[name]['focusSteps'], lensData[name]['focusPI'], lensData[name]['irisSteps']]
    return prefix, lensConfig

# check for a new lens family
def checkNewLensFamily(newLensFamily:str) -> str:
    '''
    Check if the selected lens family is different from the last lens family.
    ### input: 
    - newLensFamily: the new lens family name
    ### return: 
    [None | new lens family name]
    '''
    if newLensFamily == None:
        return None
    
    if newLensFamily != lastLensFamily:
        actions.enableLiveFrame(False)
        actions.enableLiveFrameAbs(False)
        if ENABLE_LENS_IQ_FUNCTIONS: 
            IQEP.clearFields()
            IQEP.enableLiveFrame(False)
            IQEP.enableSensorFrame(False)
        actions.setStatus('notInit')
    else:
        return None
    return newLensFamily
    
# initialize motor controller
def initMCR(MCRCom:str, lensFam:str='', homeMotors:bool=True, regardLimits:bool=True) -> bool:
    '''
    Initialize the motor controller. 
    Regardlimits are set at the MCRControl.py level, not this local level
    RegardBacklash is set at the local level so moves can vary this setting
    ### input: 
    - MCRCom: comPort for MCR controllerlensConfig parameters if available
    - lensFam (optional: ''): lens family string (see variable lensFamiliesList for names)
    - homeMotors (optional: True): true to move motors to home positions
    - regardLimits (optional: True): regard the limit switches and do not exceed
    ### return: 
    [initialized state]
    '''
    global MCR
    actions.setStatus('init')
    if lensFam != '':
        # initialize configuration
        _, lensConfig = selectLens(lensFam)
    if not MCR:
        MCR = TheiaMCR.MCRControl(MCRCom, moduleDebugLevel=MCRDebugLogLevel)
        if not MCR.MCRInitialized:
            log.error('** MCR initialization failed')
            MCR = None
            actions.setStatus('error')
            return False
        mainGUI.window['fldFWRev'].update(f'FW: {MCR.MCRBoard.readFWRevision()}')
        mainGUI.window['fldSNBoard'].update(f'SN: {MCR.MCRBoard.readBoardSN()}')
    log.info('Initializing motors')
    MCR.focusInit(lensConfig[2], lensConfig[3], move=homeMotors)
    MCR.zoomInit(lensConfig[0], lensConfig[1], move=homeMotors)
    MCR.irisInit(lensConfig[4], move=homeMotors)
    MCR.IRCInit()
    MCR.IRC.state(1)
    mainGUI.window['IRCBtn1'].update(button_color=mainGUI.IRCSelectedColor)
    # set initial motor speeds
    setMotorSpeeds(settings.get('focusSpeed', 1000), settings.get('zoomSpeed', 1000), settings.get('irisSpeed', 100))
    setHomeSpeeds(settings.get('focusHomingSpeed', 1000), settings.get('zoomHomingSpeed', 1000), settings.get('irisHomingSpeed', 100))
    MCR.focus.slowHomeApproach = slowHomeApproach
    MCR.zoom.slowHomeApproach = slowHomeApproach

    # initialize GUI settings
    actions.setRegardLimits(regardLimits)
    MCR.focus.setRespectLimits(regardLimits)
    MCR.zoom.setRespectLimits(regardLimits)
    actions.setRegardBacklash(True)
    actions.enableLiveFrame(True, absoluteInit=homeMotors)

    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.initMotors(MCR, enableFields=actions.regardLimits)

    # set current motor steps (PI positions)
    mainGUI.window['focusCurFld'].update(MCR.focus.currentStep)
    mainGUI.window['zoomCurFld'].update(MCR.zoom.currentStep)
    mainGUI.window['irisCurFld'].update(MCR.iris.currentStep)

    actions.setStatus('ready')
    log.info('Lens initialized')
    return True

# set motor speeds
def setMotorSpeeds(focusSpeed:int=1000, zoomSpeed:int=1000, irisSpeed:int=100):
    '''
    Set the motor speeds.  Speeds are saved in the local settings file (not stored in control board EEPROM)
    ### input: 
    - focusSpeed (optional: 1000): focus motor pps speed
    - zoomSpeed (optional: 1000): zoom motor pps speed
    - irisSpeed (optional: 100): iris motor pps speed
    '''
    if (MCR.focus.setMotorSpeed(int(focusSpeed)) == 0): 
        settings['focusSpeed'] = int(focusSpeed)
    else:
        log.warning(f'Focus motor speed {focusSpeed} is out of range, not changed')

    if (MCR.zoom.setMotorSpeed(int(zoomSpeed)) == 0): 
        settings['zoomSpeed'] = int(zoomSpeed)
    else:
        log.warning(f'Zoom motor speed {zoomSpeed} is out of range, not changed')

    if (MCR.iris.setMotorSpeed(int(irisSpeed)) == 0): 
        settings['irisSpeed'] = int(irisSpeed)
    else:
        log.warning(f'Iris motor speed {irisSpeed} is out of range, not changed')
    return

# set motor homing speeds
def setHomeSpeeds(focusSpeed:int=1000, zoomSpeed:int=1000, irisSpeed:int=100):
    '''
    Set the motor homing speeds.  Speeds are saved in the local settings file (not stored in control board EEPROM)
    ### input: 
    - focusSpeed (optional: 1000): focus motor pps speed
    - zoomSpeed (optional: 1000): zoom motor pps speed
    - irisSpeed (optional: 100): iris motor pps speed
    '''
    if (MCR.focus.setHomingSpeed(int(focusSpeed)) == 0): 
        settings['focusHomingSpeed'] = int(focusSpeed)
    else:
        log.warning(f'Focus motor speed {focusSpeed} is out of range, not changed')

    if (MCR.zoom.setHomingSpeed(int(zoomSpeed)) == 0): 
        settings['zoomHomingSpeed'] = int(zoomSpeed)
    else:
        log.warning(f'Zoom motor speed {zoomSpeed} is out of range, not changed')

    if (MCR.iris.setHomingSpeed(int(irisSpeed)) == 0): 
        settings['irisHomingSpeed'] = int(irisSpeed)
    else:
        log.warning(f'Iris motor speed {irisSpeed} is out of range, not changed')
    return

# handle settings values
def handleSettingsValues(values:dict):
    '''
    Respond to the values in the settings window. 
    '''
    if values['focusSpeed'] != '' or values['zoomSpeed'] != '' or values['irisSpeed'] != '':
        setMotorSpeeds(values['focusSpeed'], values['zoomSpeed'], values['irisSpeed'])

    if values['focusHomeSpeed'] != '' or values['zoomHomeSpeed'] != '' or values['irisHomeSpeed'] != '':
        setHomeSpeeds(values['focusHomeSpeed'], values['zoomHomeSpeed'], values['irisHomeSpeed'])

    if values['slowHome'] != None:
        slowHomeApproach = values['slowHome']
        MCR.focus.slowHomeApproach = slowHomeApproach
        MCR.zoom.slowHomeApproach = slowHomeApproach
        settings['slowHome'] = slowHomeApproach

    if values['cp_limitCheck'] != None:
        state = values['cp_limitCheck']
        actions.setRegardLimits(state)
        if MCR:
            MCR.focus.setRespectLimits(state)
            MCR.zoom.setRespectLimits(state)

    if values['cp_backlash'] != None:
        actions.setRegardBacklash(values['cp_backlash'])

##################################################
### main application routine 
##################################################
if ENABLE_LENS_IQ_FUNCTIONS: IQEP = lensIQ_expansion.IQExpansionPack()
settings = settingsFiles.readSettingsFile(settingsFileName)
comPort = settings.get('comPort', '')
comPortList = utilities.searchComPorts()
if comPort not in comPortList:
    comPort = ''

# save default files
settings['dataSetQRCode'] = dataSetQRCode

# default lens setup
lensData = settingsFiles.readLensLimitsFile(lensDataFileName)
if lensData == None:
    sg.popup_ok(f'Lens data file not found: {lensDataFileName}', title='Error')
    sys.exit(1)
lensFamiliesList = list(lensData.keys())
lastLensFamily = settings.get('lastLensFamily', 'TL1250P Nx')
slowHomeApproach = settings.get('slowHome', True)

# create the GUI window
actions = createMainGUI()

# Lens IQ setup variables
if ENABLE_LENS_IQ_FUNCTIONS: IQEP.setup(mainGUI.window, settings, actions.setStatus)

while (True):
    sourceWindow, event, values = sg.read_all_windows()
    #log.debug(f"Event: {event}\n{values}")
    if event in (sg.WIN_CLOSED, 'exitBtn'):
        if sourceWindow == mainGUI.window:
            # close application
            break
        else:
            IQEP.closeWindow(sourceWindow)

    elif (event == 'cp_lensFam'):
        newLensFamily = checkNewLensFamily(values['cp_lensFam'])
        if newLensFamily != None: 
            lastLensFamily = newLensFamily
            settings['lastLensFamily'] = lastLensFamily
            if ENABLE_LENS_IQ_FUNCTIONS: mainGUI.window['calFile'].update('')

    elif event == 'cp_port':
        newComPort = values['cp_port']
        if newComPort != comPort:
            comPort = newComPort
            settings['comPort'] = comPort
            # cancel motor initialization status
            actions.setStatus('notInit')
            actions.enableLiveFrame(False)

    elif event == 'cp_refresh':
        newComPortList = utilities.searchComPorts()
        if comPort not in newComPortList:
            # previously selected comPort no longer available, choose the last one in the new list
            comPort = newComPortList[-1] if len(newComPortList) >= 1 else ''
            if comPort != '':
                settings['comPort'] = comPort
            # cancel motor initialization status
            actions.setStatus('notInit')
            actions.enableLiveFrame(False)
        mainGUI.window['cp_port'].update(value=comPort, values=sorted(newComPortList), size=(18,10))

    elif event == 'motorInitBtn':
        if comPort != '':
            initMCR(MCRCom=comPort, homeMotors=False, lensFam=lastLensFamily, regardLimits=False)
        else:
            log.error("** Com port is blank")
            sg.popup_ok('Com port is blank', title='Error')
    
    elif event == 'motorInitHomeBtn':
        if comPort != '':
            success = initMCR(lensFam=lastLensFamily, MCRCom=comPort, homeMotors=True, regardLimits=True)
            if success and MCR.MCRInitialized and ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateCalibrationFile()
        else:
            log.error("** Com port is blank")
            sg.popup_ok('Com port is blank', title='Error')

    elif event == 'settingsPopup':
        # open the settings popup window.  The communication path for this program will always be 'USB'.  
        settingsValues = mainGUI.settingsGUI('USB', MCR, actions)
        if settingsValues != None:
            handleSettingsValues(settingsValues)

            if settingsValues['comUART'] or settingsValues['comI2C']:
                # communications path was set to something else and USB is no longer available. 
                if comPort == '':
                    log.error('** Com port is blank')
                    sg.popup_ok('Com path not changed: Com port is blank', title='Error')
                    continue
                if not MCR:
                    MCR = TheiaMCR.MCRControl(comPort)
                    if not MCR.MCRInitialized:
                        log.error('** Com path not changed: MCR not initialized')
                        sg.popup_ok('Motor control initalization error, communication path not changed', title='Error')
                        MCR = None
                        continue
                MCR.MCRBoard.setCommunicationPath('UART' if settingsValues['comUART'] else 'I2C')
                sg.popup_ok(f'New communication path was set to {"UART" if settingsValues["comUART"] else "I2C"}.  USB communication is no longer available and this application will end.', title='New com path')
                break
    
    elif event == 'IRCBtn1':
        mainGUI.window['IRCBtn1'].update(button_color=mainGUI.IRCSelectedColor)
        mainGUI.window['IRCBtn2'].update(button_color=mainGUI.TheiaDarkBlueColor)
        MCR.IRC.state(1)
        
    elif event == 'IRCBtn2':
        mainGUI.window['IRCBtn1'].update(button_color=mainGUI.TheiaDarkBlueColor)
        mainGUI.window['IRCBtn2'].update(button_color=mainGUI.IRCSelectedColor)
        MCR.IRC.state(2)

    if ENABLE_LENS_IQ_FUNCTIONS: 
        lensFamily = IQEP.checkEvents(sourceWindow == mainGUI.window, event, values)
        newLensFamily = checkNewLensFamily(lensFamily)
        if newLensFamily != None: 
            lastLensFamily = newLensFamily
            settings['lastLensFamily'] = lastLensFamily
            mainGUI.window['cp_lensFam'].update(lastLensFamily)

    if MCR:
        if MCR.MCRInitialized and event in {'moveWideBtn', 'moveTeleBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', 'moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn', 'zoomCurFldUpdate', 'focusCurFldUpdate', 'irisCurFldUpdate'}:
            actions.setStatus('moving')
            if event == 'moveWideBtn':
                # move zoom motor
                MCR.zoom.moveRel(int(values['zoomStepFld']), correctForBL=actions.regardBacklash)
                # update field
                mainGUI.window['zoomCurFld'].update(MCR.zoom.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterZoom()

            elif event == 'moveTeleBtn':
                # move zoom motor
                MCR.zoom.moveRel(-int(values['zoomStepFld']), correctForBL=actions.regardBacklash)
                # update field
                mainGUI.window['zoomCurFld'].update(MCR.zoom.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterZoom()

            elif event == 'moveNearBtn':
                # move focus motor
                MCR.focus.moveRel(-int(values['focusStepFld']), correctForBL=actions.regardBacklash)
                # update field
                mainGUI.window['focusCurFld'].update(MCR.focus.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterFocus(changeOD=False)

            elif event == 'moveFarBtn':
                # move focus motor
                MCR.focus.moveRel(int(values['focusStepFld']), correctForBL=actions.regardBacklash)
                # updated field
                mainGUI.window['focusCurFld'].update(MCR.focus.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterFocus(changeOD=False)

            elif event == 'moveOpenBtn':
                # move iris motor
                MCR.iris.moveRel(-int(values['irisStepFld']), correctForBL=False)
                # update field
                mainGUI.window['irisCurFld'].update(MCR.iris.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterIris()

            elif event == 'moveCloseBtn':
                # move iris motor
                MCR.iris.moveRel(int(values['irisStepFld']), correctForBL=False)
                # updated field
                mainGUI.window['irisCurFld'].update(MCR.iris.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterIris()

            elif event in {'moveZoomAbsBtn', 'zoomCurFldUpdate'}:
                if actions.absMoveInitialized:
                    # move to absolute position
                    MCR.zoom.moveAbs(int(values['zoomCurFld']))
                    # confirm update field
                    mainGUI.window['zoomCurFld'].update(MCR.zoom.currentStep)
                    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterZoom()

            elif event in {'moveFocusAbsBtn', 'focusCurFldUpdate'}:
                if actions.absMoveInitialized:
                    # move to absolute position
                    MCR.focus.moveAbs(int(values['focusCurFld']))
                    # confirm update field
                    mainGUI.window['focusCurFld'].update(MCR.focus.currentStep)
                    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterFocus(changeOD=False)

            elif event in {'moveIrisAbsBtn', 'irisCurFldUpdate'}:
                if actions.absMoveInitialized:
                    # move to absolute position
                    MCR.iris.moveAbs(int(values['irisCurFld']))
                    # confirm update field
                    mainGUI.window['irisCurFld'].update(MCR.iris.currentStep)
                    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterIris()
        
        ####### check for unknown position
        actions.setStatus('ready')

mainGUI.window.close()
