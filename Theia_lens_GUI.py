# Live GUI motor control
# (c) 2023 Theia Technologies LLC
# contact Mark Peterson at mpeterson@theiatech.com for more information

import PySimpleGUI as sg
import logging as log
import TheiaMCR
import serial.tools.list_ports
import os
import sys

# revision
revision = "v.1.4.0"

# global variable
MCR = None

def app():
    # logging setup
    log.basicConfig(level=log.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')
    
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

    # initialization
    lensFamiliesList = [
        'TL1250P N#',
        'TL1250P R#',
        'TL936P R#',
        'TL410P R#'
    ]
    settingsFileName = 'Motor control config.json'
    settingsIconPath = resourcePath('data/cog.png')    # location of the gear icon for settings
    MCRInitialized = False
    
    TheiaLogoImagePath = resourcePath('data/Theia_logo.png')
    TheiaMenuIcon = resourcePath('data/TL1250P.ico')
    TheiaColorTheme = 'DefaultNoMoreNagging' #'LightBlue2'
    TheiaLightGreenColor = '#00CC66'
    TheiaGreenColor = '#006633'
    TheiaDarkBlueColor = '#333399'
    TheiaLightBlueColor = '#3366CC'

    # read the saved settings file
    # find the settings file
    def readSettingsFile():
        '''
        Read the PySimpleGUI settings file. 
        Create a file in the AppData/Local folders if it doesn't exist. 
        '''
        homeDir = os.path.expanduser("~")
        appDir = os.path.join(homeDir, 'AppData', 'Local', 'TheiaLensGUI')
        if not os.path.exists(appDir):
            os.mkdir(appDir)
        settingsFullFileName = f'{appDir}\\{settingsFileName}'
        if not os.path.exists(settingsFullFileName):
            log.info(f'New settings file created {settingsFullFileName}')
            settings = sg.UserSettings(filename=settingsFileName, path=appDir)
            settings['comPort'] = ''
            settings['lastLensFamily'] = ''
        settings = sg.UserSettings(filename=settingsFileName, path=appDir)
        return settings

    # enbleLiveFrame
    def enableLiveFrame(enable:bool=True) -> bool:
        '''
        Enable buttons and inputs in the live frame. 
        ### input
        - enable (bool): state
        ### return
        [enabled value]
        '''
        componentList = ['moveTeleBtn', 'moveWideBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', \
            'moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn', \
            'zoomCurFld', 'focusCurFld', 'irisCurFld', 'zoomStepFld', 'focusStepFld', 'irisStepFld']
        for component in componentList:
            window[component].update(disabled = not enable)
        return not enable
    
    # enableLiveFrameAbs
    def enableLiveFrameAbs(enable:bool=True) -> bool:
        '''
        Enable buttons and inputs for absolute movements. 
        ### input
        - enable (bool): state
        ### return
        [enabled value]
        '''
        componentList = ['moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn']
        for component in componentList:
            window[component].update(disabled = not enable)
        return not enable
    
    # set the regard limits flag in MCR module
    def setRegardLimits(state:bool=True):
        '''
        Set the regard limits flag in MCR module. 
        Limit steps to avoid going past the hard stop.  
        This setting is stored in the MCRControl.py variables (not local)
        ### input: 
        - state: the regard setting
        '''
        MCR.focus.setRespectLimits(state)
        MCR.zoom.setRespectLimits(state)
        enableLiveFrameAbs(state)

    # set the backlash flag in MCR move relative commands
    def setRegardBacklash(state:bool=True) -> bool:
        '''
        Set the backalsh flag in the MCR move relative command.   
        *This function is not active*
        ### input
        - state: the regard setting (not used)
        '''
        return state
    
    # set current step number
    def setCurrentStepNumber(motor:str='all'):
        '''
        Set the current step number. 
        Read and set the current step for focus, zoom, and/or iris motors from the MCR variables. 
        ### input
        - motor (optional: 'all'): ['focus' | 'zoom' | 'iris' | 'all']
        '''
        if motor in {'focus', 'all'}:
            window['focusCurFld'].update(MCR.focus.currentStep)
        if motor in {'zoom', 'all'}:
            window['zoomCurFld'].update(MCR.zoom.currentStep)
        if motor in {'iris', 'all'}:
            window['irisCurFld'].update(MCR.iris.currentStep)
        return
    
    # set motor speeds
    def setMotorSpeeds(focusSpeed:int=1000, zoomSpeed:int=1000, irisSpeed:int=100):
        '''
        Set the motor speeds.  Speeds are saved in the local settings file (not stored in control board EEPROM)
        ### input: 
        - focusSpeed (optional: 1000): focus motor pps speed
        - zoomSpeed (optional: 1000): zoom motor pps speed
        - irisSpeed (optional: 100): iris motor pps speed
        '''
        if (MCR.focus.setMotorSpeed(focusSpeed) == 'OK'): 
            settings['focusSpeed'] = focusSpeed
        else:
            log.warning(f'Focus motor speed {focusSpeed} is out of range, not changed')

        if (MCR.zoom.setMotorSpeed(focusSpeed) == 'OK'): 
            settings['zoomSpeed'] = zoomSpeed
        else:
            log.warning(f'Zoom motor speed {focusSpeed} is out of range, not changed')

        if (MCR.iris.setMotorSpeed(focusSpeed) == 'OK'): 
            settings['irisSpeed'] = irisSpeed
        else:
            log.warning(f'Iris motor speed {focusSpeed} is out of range, not changed')
        return
    
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
    
    # setup lens parameters
    def selectLens(fam:str) -> tuple[int]:
        '''
        Set up lens parameters focus steps, focus PI step, zoom steps, zoom PI step, iris steps. 
        ### input
        - fam: lens family (see lensFamiliesList variable for names. )
        ### return
        lensConfig = [zoom steps, zoom PI, focus steps, focus PI, iris steps]
        '''
        log.info(f"Select {fam}")
        lensConfig = []
        if "410P R" in fam:
            lensConfig = [4073, 154, 9353, 8652, 75]
        elif "1250P R" in fam:
            lensConfig = [3256, 3147, 8466, 8031, 75]
        elif "410P N" in fam:
            lensConfig = [4017, 136, 9269, 8574, 75]
        elif "1250P N" in fam:
            lensConfig = [3227, 3119, 8390, 7959, 75]
        elif "936" in fam:
            lensConfig = [2994, 2958, 5180, 5128, 75]
        return lensConfig
        
    # initialize motor controller
    def initMCR(MCRCom:str, lensFam:str='', homeMotors:bool=True, MCRInitialized:bool=True, regardLimits:bool=True) -> bool:
        '''
        Initialize the motor controller. 
        Regardlimits are set at the MCRControl.py level, not this local level
        RegardBacklash is set at the local level so moves can vary this setting
        ### input: 
        - MCRCom: comPort for MCR controllerlensConfig parameters if available
        - lensFam (optional: ''): lens family string (see variable lensFamiliesList for names)
        - homeMotors (optional: True): true to move motors to home positions
        - MCRInitialize (optional: True): True for first initialization, false to only re-init motors
        - regardLimits (optional: True): regard the limit switches and do not exceed
        ### return: 
        [initialized state]
        '''
        nonlocal regardBacklash
        global MCR
        if lensFam != '':
            # initialize configuration
            lensConfig = selectLens(lensFam)
        if not MCRInitialized: 
            MCR = TheiaMCR.MCRControl(MCRCom)
            if not MCR.MCRInitialized:
                return False
            window['fldFWRev'].update(f'FW: {MCR.MCRBoard.readFWRevision()}')
            window['fldSNBoard'].update(f'SN: {MCR.MCRBoard.readBoardSN()}')
        log.debug('  initializing motors')
        MCR.focusInit(lensConfig[2], lensConfig[3], move=homeMotors)
        MCR.zoomInit(lensConfig[0], lensConfig[1], move=homeMotors)
        MCR.irisInit(lensConfig[4], move=homeMotors)
        # set initial motor speeds
        setMotorSpeeds(settings.get('focusSpeed', 1000), settings.get('zoomSpeed', 1000), settings.get('irisSpeed', 100))

        # initialize GUI settings
        setRegardLimits(regardLimits)
        window['cp_limitCheck'].update(regardLimits)
        regardBacklash = setRegardBacklash(True)
        window['cp_backlash'].update(regardBacklash)
        enableLiveFrame(True)
        setCurrentStepNumber()
        return True
    
    # setting window layout
    def settingsGUILayout(initPath:str):
        '''
        Create a window for additional settings.  This window includes communication path and motor speeds.  
        Once set by the user, the motor speeds are written to the board and the communication path is updated.  
        If the user cancels, nothing is changed and the return value is 'None'.  
        ### input:
        - initPath: current communication path string ('USB', 'UART', 'I2C')
        ### return: 
        [new communication path string | None]
        '''
        # motor speeds
        speedsLayout = [
            [sg.Text('Focus motor speed', expand_x=True), sg.Input('', size=(15,1), key='focusSpeed', disabled=True)],
            [sg.Text('Zoom motor speed', expand_x=True), sg.Input('', size=(15,1), key='zoomSpeed', disabled=True)],
            [sg.Text('Iris motor speed', expand_x=True), sg.Input('', size=(15,1), key='irisSpeed', disabled=True)],
        ]
        # communication path
        comLayout = [
            [sg.Text('Warning: Changing the communication path will reboot the controller board and the original communication path will no longer be active', 
                     size=(30,4), text_color='red')],
            [sg.Button('Change com path', key='changePath')],
            [sg.Radio('USB', group_id='comGroup', default=(initPath == 'USB'), key='comUSB', visible=False), 
             sg.Radio('UART', group_id='comGroup', default=(initPath == 'UART'), key='comUART', visible=False), 
             sg.Radio('I2C', group_id='comGroup', default=(initPath == 'I2C'), key='comI2C', visible=False)]
        ]
        layout = [
            [sg.Frame('Motor speeds', speedsLayout, expand_x=True)],
            [sg.Frame('Communication', comLayout)],
            [sg.Button('Save settings', key='save'), sg.Button('Discard settings', key='discard')]
        ]
        window = sg.Window('Set values', layout, finalize=True)
        if MCRInitialized:
            window['focusSpeed'].update(MCR.focus.currentSpeed)
            window['focusSpeed'].update(disabled=False)
            window['zoomSpeed'].update(MCR.zoom.currentSpeed)
            window['zoomSpeed'].update(disabled=False)
            window['irisSpeed'].update(MCR.iris.currentSpeed)
            window['irisSpeed'].update(disabled=False)

        while True:
            event, values = window.read()
            if event in {sg.WIN_CLOSED, 'save', 'discard'}:
                break
            elif event == 'changePath':
                window['changePath'].update(visible=False)
                window['comUSB'].update(visible=True)
                window['comUART'].update(visible=True)
                window['comI2C'].update(visible=True)
        window.close()
        if event == 'save': return values
        return None
    
    # mainGUILayout
    def mainGUILayout():
        '''
        Main GUI layout. 
        Create the GUI window for the main window.  
        There is a live motor control section, measurement section, settings section, and optional monitor 
        section when the test is running.  
        ### return: 
        [handle to the window]
        '''
        sg.theme(TheiaColorTheme) 
        sg.set_global_icon(TheiaMenuIcon)
        sg.set_options(button_color=[TheiaLightGreenColor, TheiaDarkBlueColor])
        # footer frame
        footerFrame = [
            [sg.Text(revision, size=(12,1), font='Helvetica 8'),
                sg.Text('', size=(20,1), font='Helvetica 8', key='fldFWRev'),
                sg.Text('', size=(20,1), font='Helvetica 8', key='fldSNBoard'),
                sg.Push(), 
                sg.Image(filename=settingsIconPath, key='settingsPopup', enable_events=True),
                sg.Button('Quit', size=(12,1), key="exitBtn")]
        ]

        # Live lens motor control section
        # lens family sub-frame
        lensFamFrame = [
            [sg.Text('Lens family', size=(10,1)), sg.Combo(sorted(lensFamiliesList), default_value=lastLensFamily, size=(15,1), enable_events=True, key='cp_lensFam'), 
                sg.Text('', size=(3,1)), sg.Checkbox('Backlash', default=True, key='cp_backlash', change_submits=True)]
            ]
        # comPort selection sub-frame
        comPortFrame = [
            [sg.Text('Com port', size=(10,1)), sg.Combo(sorted(comPortList), default_value=comPort, size=(15,1), enable_events=True, key="cp_port"), 
                sg.Text('', size=(3,1)), sg.Checkbox('Regard limits', default=True, key='cp_limitCheck', change_submits=True)]
            ]
        # initialize motor control sub-frame
        initMotorsFrame = [
            [sg.Button('Initialize and home motors', size=(20,1), key='motorInitHomeBtn'),
                sg.Button('Initialize motors', size=(12,1), key='motorInitBtn')]
            ]
        # lens header including picture and setup functions
        headerFrame = [
            [sg.Column(lensFamFrame)],
            [sg.Column(comPortFrame)],
            [sg.Column(initMotorsFrame, element_justification='center', expand_x=True)]
            ]

        # motor control sub-frames
        relMoveFrame = [
            [sg.Button('Tele', size=(12,1), key='moveTeleBtn'), sg.Input('1000', size=(12,1), justification='center', disabled_readonly_background_color='LightGray', key='zoomStepFld'), 
                sg.Button('Wide', size=(12,1), key='moveWideBtn')],
            [sg.Button('Near', size=(12,1), key='moveNearBtn'), sg.Input('1000', size=(12,1), justification='center', disabled_readonly_background_color='LightGray', key='focusStepFld'), 
                sg.Button('Far', size=(12,1), key='moveFarBtn')],
            [sg.Button('Open', size=(12,1), key='moveOpenBtn'), sg.Input('10', size=(12,1), justification='center', disabled_readonly_background_color='LightGray', key='irisStepFld'), 
                sg.Button('Close', size=(12,1), key='moveCloseBtn')],
            ]
        curPosFrame = [
            [sg.Input('0', size=(12,1), pad=(6,6), justification='center', disabled_readonly_background_color='LightGray', key='zoomCurFld')],
            [sg.Input('0', size=(12,1), pad=(6,6), justification='center', disabled_readonly_background_color='LightGray', key='focusCurFld')],
            [sg.Input('0', size=(12,1), pad=(6,6), justification='center', disabled_readonly_background_color='LightGray', key='irisCurFld')],
            ]
        absMoveFrame = [
            [sg.Button('Zoom', size=(12,1), key='moveZoomAbsBtn', disabled=True)],
            [sg.Button('Focus', size=(12,1), key='moveFocusAbsBtn', disabled=True)],
            [sg.Button('Iris', size=(12,1), key='moveIrisAbsBtn', disabled=True)],
            ]
        liveControlFrame = [
            [sg.Image(TheiaLogoImagePath), sg.Column(headerFrame)],
            [sg.Frame('Relative move', relMoveFrame), sg.Frame('Current', curPosFrame), sg.Frame('Absolute move', absMoveFrame)],
            [sg.Frame(title='', layout=footerFrame, expand_x=True)]
            ]
                    
        # overall layout
        layout = [
            [sg.Frame('Motor control', liveControlFrame, expand_x=True)]
            ] 
        window = sg.Window('Theia lens motor control', layout, finalize=True)
        return window


    #***************** main application routine ***********************
    settings = readSettingsFile()
    comPort = settings.get('comPort', '')
    comPortList = searchComPorts()
    if comPort not in comPortList:
        comPort = ''

    # default lens setup
    lastLensFamily = settings.get('lastLensFamily', 'TL1250P N#')
    selectLens(lastLensFamily)

    window = mainGUILayout()

    while (True):
        event, values = window.read()
        #log.debug(f"Event: {event}")
        # exit calibration app
        if event in (sg.WIN_CLOSED, 'exitBtn'):
            break

        elif event == 'cp_lensFam':
            lastLensFamily = values['cp_lensFam']
            selectLens(lastLensFamily)
            settings['lastLensFamily'] = lastLensFamily

        elif event == 'cp_port':
            comPort = values['cp_port']
            settings['comPort'] = comPort

        elif event == 'cp_limitCheck':
            setRegardLimits(values['cp_limitCheck'])

        elif event == 'cp_backlash':
            regardBacklash = setRegardBacklash(values['cp_backlash'])
    
        elif event == 'motorInitBtn':
            if comPort != '':
                MCRInitialized = initMCR(MCRCom=comPort, homeMotors=False, lensFam=lastLensFamily, MCRInitialized=MCRInitialized, regardLimits=False)
            else:
                log.error("Com port is blank")
                sg.popup_ok('Com port is blank', title='Error')
        
        elif event == 'motorInitHomeBtn':
            if comPort != '':
                MCRInitialized = initMCR(lensFam=lastLensFamily, MCRCom=comPort, homeMotors=True, MCRInitialized=MCRInitialized, regardLimits=True)
            else:
                log.error("Com port is blank")
                sg.popup_ok('Com port is blank', title='Error')

        elif event == 'settingsPopup':
            # open the settings popup window.  The communication path for this program will always be 'USB'.  
            newComPath = settingsGUILayout('USB')
            if newComPath != None:
                if newComPath['focusSpeed'] != '' or newComPath['zoomSpeed'] != '' or newComPath['irisSpeed'] != '':
                    setMotorSpeeds(newComPath['focusSpeed'], newComPath['zoomSpeed'], newComPath['irisSpeed'])
                if newComPath['comUART'] or newComPath['comI2C']:
                    # communications path was set to something else and USB is no longer available. 
                    sg.popup_ok(f'New communication path was set to {"UART" if newComPath["comUART"] else "I2C"}.  USB communication is no longer available and this application will end.', title='New com path')
                    break

        if MCRInitialized:
            if event == 'moveWideBtn':
                # move zoom motor
                MCR.zoom.moveRel(int(values['zoomStepFld']), correctForBL=regardBacklash)
                # update field
                window['zoomCurFld'].update(MCR.zoom.currentStep)

            elif event == 'moveTeleBtn':
                # move zoom motor
                MCR.zoom.moveRel(-int(values['zoomStepFld']), correctForBL=regardBacklash)
                # update field
                window['zoomCurFld'].update(MCR.zoom.currentStep)

            elif event == 'moveNearBtn':
                # move focus motor
                MCR.focus.moveRel(-int(values['focusStepFld']), correctForBL=regardBacklash)
                # update field
                window['focusCurFld'].update(MCR.focus.currentStep)

            elif event == 'moveFarBtn':
                # move focus motor
                MCR.focus.moveRel(int(values['focusStepFld']), correctForBL=regardBacklash)
                # updated field
                window['focusCurFld'].update(MCR.focus.currentStep)

            elif event == 'moveOpenBtn':
                # move iris motor
                MCR.iris.moveRel(-int(values['irisStepFld']))
                # update field
                window['irisCurFld'].update(MCR.iris.currentStep)

            elif event == 'moveCloseBtn':
                # move iris motor
                MCR.iris.moveRel(int(values['irisStepFld']))
                # updated field
                window['irisCurFld'].update(MCR.iris.currentStep)

            elif event == 'moveZoomAbsBtn':
                # move to absolute position
                MCR.zoom.moveAbs(int(values['zoomCurFld']))
                # confirm update field
                window['zoomCurFld'].update(MCR.zoom.currentStep)

            elif event == 'moveFocusAbsBtn':
                # move to absolute position
                MCR.focus.moveAbs(int(values['focusCurFld']))
                # confirm update field
                window['focusCurFld'].update(MCR.focus.currentStep)

            elif event == 'moveIrisAbsBtn':
                # move to absolute position
                MCR.iris.moveAbs(int(values['irisCurFld']))
                # confirm update field
                window['irisCurFld'].update(MCR.iris.currentStep)

    window.close()
    return


# call the app function in threading mode to allow user interaction while tests are running
if __name__ == '__main__':
    app()