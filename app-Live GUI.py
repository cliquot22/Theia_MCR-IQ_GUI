# Live GUI motor control
# control the motor and keep track of motor step position
#

import PySimpleGUI as sg
import logging as log
import TheiaMCR
import serial.tools.list_ports
import os

# revision
revision = "v.1.3.0"

# global variable
MCR = None

def app():
    # logging setup
    log.basicConfig(level=log.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')

    # initialization
    lensFamiliesList = ["TW50", "TW60", "TW80", "TW90"]
    settingsFileName = 'Motor control config.json'
    MCRInitialized = False

    # read the saved settings file
    # find the settings file
    def readSettingsFile():
        homeDir = os.path.expanduser("~")
        settingsFullFileName = "{}\\{}".format(homeDir, settingsFileName)
        if not os.path.exists(settingsFullFileName):
            log.info(f'New settings file created {settingsFullFileName}')
            settings = sg.UserSettings(filename=settingsFileName, path=homeDir)
            settings['comPort'] = ''
            settings['lastLensFamily'] = ''
        settings = sg.UserSettings(filename=settingsFileName, path=homeDir)
        return settings

    # enbleLiveFrame
    # enable or disable the buttons and input in the live frame
    # input: enable (bool)
    # return: live input enabled (bool)
    def enableLiveFrame(enable:bool=True) -> bool:
        componentList = ['moveTeleBtn', 'moveWideBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', \
            'moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn', \
            'zoomCurFld', 'focusCurFld', 'irisCurFld', 'zoomStepFld', 'focusStepFld', 'irisStepFld']
        for component in componentList:
            window[component].update(disabled = not enable)
        return not enable
    
    # enableLiveFrameAbs
    # enable or disable the absolute movement buttons
    # input: enable (bool)
    # return: enable
    def enableLiveFrameAbs(enable:bool=True) -> bool:
        componentList = ['moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn']
        for component in componentList:
            window[component].update(disabled = not enable)
        return not enable
    
    # set the regard limits flag in MCR module
    # limit steps to avoid hitting the hard stop
    # this setting is stored in the MCRControl.py variables (not local)
    # input: state
    def setRegardLimits(state:bool=True):
        MCR.focus.setRespectLimits(state)
        MCR.zoom.setRespectLimits(state)
        enableLiveFrameAbs(state)

    # set the backlash flag in MCR move relative commands
    # input: state
    def setRegardBacklash(state:bool=True) -> bool:
        return state
    
    # set current step number
    # read and set the current step for focus, zoom, and/or iris motors
    # input: motor ("focus", "zoom", "iris", None (all)): motor to set
    def setCurrentStepNumber(motor:str='all'):
        if motor in {'focus', 'all'}:
            window['focusCurFld'].update(MCR.focus.currentStep)
        if motor in {'zoom', 'all'}:
            window['zoomCurFld'].update(MCR.zoom.currentStep)
        if motor in {'iris', 'all'}:
            window['irisCurFld'].update(MCR.iris.currentStep)
        return
    
    # serachComPorts
    # search for connected com ports for selecting MCR motor controllers
    # return: list of com ports
    def searchComPorts():
        ports = serial.tools.list_ports.comports()
        portList = []
        for port, desc, hwid in sorted(ports):
            log.info("Ports: {} [{}]".format(desc, hwid))
            portList.append(port)
        return portList
    
    # setup lens parameters
    # input: fam: TW family number (TW60)
    # return: lensConfig = [zoom steps, zoom PI, focus steps, focus PI, iris steps]
    def selectLens(fam:str) -> tuple[int]:
        log.info(f"Select lens family {fam}")
        lensConfig = []
        if "50" in fam:
            lensConfig = [4073, 154, 9353, 8652, 75]
        elif "60" in fam:
            lensConfig = [3256, 3147, 8466, 8031, 75]
        elif "80" in fam:
            lensConfig = [4017, 136, 9269, 8574, 75]
        elif "90" in fam:
            lensConfig = [3227, 3119, 8390, 7959, 75]
        return lensConfig
        
    # initialize motor controller
    # regardlimits are set at the MCRControl.py level, not this local level
    # regardBacklash is set at the local level so moves can vary this setting
    # input: MCRCom comPort for MCR controllerlensConfig parameters if available
    #        lens family prefix string (optional)
    #       homeMotors: true to home motors
    #       MCRInitialize: True for first initialization, false to only re-init motors
    #       regardLimits: regard the limit switches and do not exceed
    # return: initialized state
    def initMCR(MCRCom:str, lensFam:str='', homeMotors:bool=True, MCRInitialized:bool=True, regardLimits:bool=True) -> bool:
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

        # initialize GUI settings
        setRegardLimits(regardLimits)
        window['cp_limitCheck'].update(regardLimits)
        regardBacklash = setRegardBacklash(True)
        window['cp_backlash'].update(regardBacklash)
        enableLiveFrame(True)
        setCurrentStepNumber()
        return True
    
    # mainGUILayout
    # create the GUI window for the main window.  This can be re-created based on selected language
    # There is a live motor control section, measurement section, settings section, and optional monitor section when the test is running 
    # return: handle to the window
    def mainGUILayout():        
        # footer frame
        footerFrame = [
            [sg.Text(revision, size=(12,1), font='Helvetica 8'),
                sg.Text('', size=(20,1), font='Helvetica 8', key='fldFWRev'),
                sg.Text('', size=(20,1), font='Helvetica 8', key='fldSNBoard')]
        ]

        # Live lens motor control section
        # lens family sub-frame
        lensFamFrame = [
            [sg.Text('Lens family', size=(18,1)), sg.Combo(sorted(lensFamiliesList), default_value=lastLensFamily, size=(25,1), enable_events=True, key='cp_lensFam'), 
                sg.Text('', size=(8,1)), sg.Checkbox('Backlash', default=True, key='cp_backlash', change_submits=True)]
            ]
        # comPort selection sub-frame
        comPortFrame = [
            [sg.Text('Com port', size=(18,1)), sg.Combo(sorted(comPortList), default_value=comPort, size=(25,1), enable_events=True, key="cp_port"), 
                sg.Text('', size=(8,1)), sg.Checkbox('Regard limits', default=True, key='cp_limitCheck', change_submits=True)]
            ]
        # initialize motor control sub-frame
        initMotorsFrame = [
            [sg.Button('Initialize motors', size=(12,1), key='motorInitBtn'), 
                sg.Button('Initialize and home motors', size=(20,1), key='motorInitHomeBtn'),
                sg.Button('Quit', size=(12,1), key="exitBtn")]
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
            [sg.Column(lensFamFrame)],
            [sg.Column(comPortFrame)],
            [sg.Frame('Relative move', relMoveFrame), sg.Frame('Current', curPosFrame), sg.Frame('Absolute move', absMoveFrame)],
            [sg.Column(initMotorsFrame, element_justification='center', expand_x=True)],
            [sg.Column(footerFrame)]
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
    lastLensFamily = settings.get('lastLensFamily', 'TW60')
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

# revision history
#
# v.1.0.1 230505 fixed location of settings file
# v.1.0.0 230504 udpated GUI based on Master Control GUI v.3.2.3
# v.0.3.0 221206 updated due to MCRControl.py function changes for focus/zoom movements
# v.0.2.2 221112 fixed crash: modifications to autofocus
# v.0.2.1 221102 lowered trigger for mid focus step to 0.20
# v.0.2.0 221024 added autofocus
#               dependency on commTCPIP (MTF machine)
# v.0.1.4 221006 added limit on/off switch
# v.0.1.3 221004 fixed initialization without movement to allow exceeding limits
# v.0.1.2 221003 added initialization without movement
# v.0.1.1 220901 added lens/com port selections
# v.0.1.0 220830