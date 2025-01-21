# Live GUI motor control and Lens IQ engineering unit conversion application
# (c) 2024 Theia Technologies LLC
# contact Mark Peterson at mpeterson@theiatech.com for more information

PySimpleGUI_license = 'ePyqJuMIaWWSNUlqbTnPNUlZVDHqlbw7Z2StIl6oIIklRnpEc83ORey2arWKJb18dhGflzvKbziRIGsYIckgx8ppYD2aVUutcX28VzJLR4CvIq6MMSToczzsNKj9Ip4JMizig300MGSGw4iJTrGolojVZUWs5pzZZZUORkl3cGG7xfvOexWh1glDbanCRrWCZMXrJazYaAWs9yuxIRj4omiwNNSf4PwOICi8wki4Tcm4F4t7ZfUzZtpgcOnnNS0rIxj7o6isTRWBF3ypabyFIssaIqkP5thSbMW3VFMJYTXqNP0FICjVoHiHUKGMVA0uZzXkJJzDbD2Q4fiuLjCdJjDKbm2O1LwVYwWX5g5FIqjUoUifV0G3hHlOahWhEngCV2GQVOjwatG85dviblGm95nQayW1VfzUIkibwKiRQy3gVdzjdaGy9EttZxXXJ7J8RhCUIJ6aINjhUQxCNsz1gbzVI1ifwMiyR7G0F10rZBUklpzica3hVJlkZ4CBIP6tI3j4IZw2MtjAUItBMqDNEbtRMHDSgZiqL5CPJEE3YwXhRJljRmXohmwLavXkJMlXcCyEIH60IAjvIVwSMsjKgmtbMJDQEbtOMcD6QFi5LyCMJIFkbMWPFxpYbVE2FmkwZdHJJdlwcP3CMBiKOLi6JetEcHGEVm0kZBXcJlz0b62O5NAkdTGRhRlSaxWCFy0mZ2WLNmoSLbmEN8vQbTS2IQsQIikJlgQ3QHW7RtkscomnVKzjcDyRI36TIhjBUiwKLnjeEG5BO7CQ4bxKNTz4EiuIMYjrAxxnICna0h=f4750f041c27bde71c9004cdb456dc1898adc4ab4410dd551218bd53f3ecd307ab6df7e1f092b49c19e8ca0b65b8aa8e2aa36295e94b7d931c658e0f2ab69f0c1bfd40f9ceea6a5599afa6ae96af3c9b17e1cea9bcaa5902e362a53202859d6dcdfcbed9c79bfa38020fe52fa48cacffe2f7e42f38f670622f8ba0d61fb743b34dff8ebecf1552d204b41a3be8cb3415358d70213e46745b7a4020f71b635e66aacc3b0c6b70e90c0128da981ba123d5a26700f027b5d3af62647c6b00fea3f8a0c84b78b38bf18302f7ee41659c118d81cf8fe513c5512b52b0bf2ec733bcb29369280e326c61a23f3380bc4557e0ab37424586d05f435c99077a227a1863ac5811443e09184c53a921216021136427f4e9702c4a15a1e1895a24966586c40e6590e82023810e2b7fa8600f91cffefa572aeba702496783bd2b13db4823775889486b6c56793a9bcc3e2f8c520c8a68cdd7c26a9dbd3cc9112e6db4e0e8dccacc70e6694e1f55b14bdcb1acd15b6d714a4cd8cbd08107fc88a998c6c1fcd614b302b92d810fddf81a60ec02f9103f2db67af4856308bae23b5954ba98b7786765d140329090ed0b77e697e81b11ceb74962316e2c8b267f7420b55bb45aabfd234ec582d04e4be9265f2d0ee55ec431b492352952dcd08be82968df04663ec10476577fb5ce6c25c2a3aef25ec54d8207cc34c4749bbe130d86d1ecceabdda4c'
import PySimpleGUI as sg
import logging
import TheiaMCR
import serial.tools.list_ports
import os
import sys
import json
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# lensIQ imports
ENABLE_LENS_IQ_FUNCTIONS = False
if ENABLE_LENS_IQ_FUNCTIONS: import lensIQ_expansion

# revision
revision = "v.2.5.0"

# global variable
MCR = None

# logging setup
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')
# set TheiaMCR sub module log level
MCRLogLevel = logging.DEBUG

def app():
    global MCR
    
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
    readyStatus = 'notInit'
    controllerStatusList = {
        'notInit': ('Not initialized','red'),                   # default
        'init': ('Initializing', 'yellow'),                     # -- in motion
        'ready': ('Ready', 'green'),                            # ready to move     
        'moving': ('Moving','yellow'),                          # -- in motion
        'posUnknown': ('Position unknown','lightgreen'),        # set if steps exceeds min/max steps at any point, reset by initializing
        'error': ('ERROR', 'red')                               # program or data error
    }
    settingsFileName = 'Motor control config.json'
    settingsIconPath = resourcePath('data/cog.png')    # location of the gear icon for settings
    lensDataFileName = 'LensData.json'                  # lens data (names and extents)
    MCRInitialized = False
    absMoveInit = False                                 # set to allow absolute movements (PI home positions known)
    
    TheiaLogoImagePath = resourcePath('data/Theia_logo.png')
    TheiaMenuIcon = resourcePath('data/TL1250P.ico')
    TheiaColorTheme = 'LightGrey1'
    TheiaLightGreenColor = '#00CC66'
    TheiaWhiteColor = '#FFFFFF'
    TheiaGreenColor = '#006633'
    TheiaDarkBlueColor = '#333399'
    TheiaLightBlueColor = '#3366CC'
    IRCSelectedColor = TheiaGreenColor                  # color for selected IRC filter

    # read the saved settings file
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
        settings = sg.UserSettings(filename=settingsFileName, path=appDir, autosave=True)
        return settings
    
    # read lens data file
    def readLensDataFile():
        '''
        Read the lens data file from the AppData/local folder.  
        ### return:  
        [lens data]
        '''
        homeDir = os.path.expanduser("~")
        appDir = os.path.join(homeDir, 'AppData', 'Local', 'TheiaLensGUI')
        lensDataFullFileName = f'{appDir}\\{lensDataFileName}'
        if not os.path.exists(lensDataFullFileName):
            log.warning(f'No data file in {lensDataFullFileName}')
            # Open the data file and save to appDir
            Tk().withdraw() 
            filename = askopenfilename(defaultextension='.json', filetypes=[('JSON File', '.json')], title="Open lens data file")
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

    # enbleLiveFrame
    def enableLiveFrame(enable:bool=True, absoluteInit:bool=False) -> bool:
        '''
        Enable buttons and inputs in the live frame. 
        ### input
        - enable (optional: True): state
        - absoluteInit (optional: False): enable absolute motor movements from home positions
        ### global
        - absMoveInit: set if relativeOnly is False
        ### return
        [enabled value]
        '''
        nonlocal absMoveInit
        absMoveInit = absoluteInit

        # relative movement buttons
        componentList = ['moveTeleBtn', 'moveWideBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', \
            'zoomCurFld', 'focusCurFld', 'irisCurFld', 'zoomStepFld', 'focusStepFld', 'irisStepFld', 'IRCBtn1', 'IRCBtn2']
        for component in componentList:
            window[component].update(disabled = not enable)
        
        # absolute movement buttons
        if absoluteInit:
            componentList = ['moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn']
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
    def selectLens(name:str) -> tuple[int]:
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
            enableLiveFrame(False)
            enableLiveFrameAbs(False)
            if ENABLE_LENS_IQ_FUNCTIONS: 
                IQEP.clearFields()
                IQEP.enableLiveFrame(False)
                IQEP.enableSensorFrame(False)
            setStatus('notInit')
        else:
            return None
        return newLensFamily
        
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
        setStatus('init')
        if lensFam != '':
            # initialize configuration
            _, lensConfig = selectLens(lensFam)
        if not MCRInitialized: 
            MCR = TheiaMCR.MCRControl(MCRCom, debugLog=MCRLogLevel)
            if not MCR.MCRInitialized:
                log.error('** MCR initialization failed')
                MCR = None
                return False
            window['fldFWRev'].update(f'FW: {MCR.MCRBoard.readFWRevision()}')
            window['fldSNBoard'].update(f'SN: {MCR.MCRBoard.readBoardSN()}')
        log.info('Initializing motors')
        MCR.focusInit(lensConfig[2], lensConfig[3], move=homeMotors)
        MCR.zoomInit(lensConfig[0], lensConfig[1], move=homeMotors)
        MCR.irisInit(lensConfig[4], move=homeMotors)
        MCR.IRCInit()
        MCR.IRCState(1)
        window['IRCBtn1'].update(button_color=IRCSelectedColor)
        # set initial motor speeds
        setMotorSpeeds(settings.get('focusSpeed', 1000), settings.get('zoomSpeed', 1000), settings.get('irisSpeed', 100))

        # initialize GUI settings
        setRegardLimits(regardLimits)
        window['cp_limitCheck'].update(regardLimits)
        regardBacklash = setRegardBacklash(True)
        window['cp_backlash'].update(regardBacklash)
        enableLiveFrame(True, absoluteInit=homeMotors)
        if ENABLE_LENS_IQ_FUNCTIONS: IQEP.initMotors(MCR, enableFields=regardLimits)
        setCurrentStepNumber()
        setStatus('ready')
        log.info('Lens initialized')
        return True
    
    # set the controller status indicators
    def setStatus(status):
        '''
        Set the status indicators to the current controller status.  
        ### input:
        - status: the new status (from controllerStatusList)
        '''
        nonlocal readyStatus
        readyStatus = status
        
        window['fldStatus'].update(controllerStatusList[readyStatus][0])
        window['fldStatus'].update(background_color=controllerStatusList[readyStatus][1])
        window.refresh()
        return
    
    ##############################################
    ### GUI layout and handling
    ##############################################
    # setting window 
    def settingsGUI(initPath:str):
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
            [sg.Button('Save settings', key='save'), sg.Button('Cancel', key='discard')]
        ]

        window = sg.Window('Set values', layout, modal=True, finalize=True)
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
        The section for converting from engineering units to motor steps is supported by Lens IQ module functions.  
        ### return: 
        [handle to the window]
        '''
        sg.theme(TheiaColorTheme) 
        sg.set_global_icon(TheiaMenuIcon)
        sg.set_options(button_color=[TheiaWhiteColor, TheiaDarkBlueColor])
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
            [sg.Text('Com port', size=(10,1)), sg.Combo(sorted(comPortList), default_value=comPort, size=(8,1), enable_events=True, key="cp_port"), 
                sg.Button('Refresh', size=(6,1), key='cp_refresh'),
                sg.Text('', size=(1,1)), sg.Checkbox('Regard limits', default=True, key='cp_limitCheck', change_submits=True)],
            ]
        # initialize motor control sub-frame
        initMotorsFrame = [
            [sg.Button('Initialize program\nand home motors', size=(14,2), key='motorInitHomeBtn'),
                sg.Button('Initialize program\nonly', size=(14,2), key='motorInitBtn'),
                sg.Frame('Status', [[sg.Text('', key='fldStatus', size=(12,1), justification='center')]]) ]
            ]
        # lens header including picture and setup functions
        headerFrame = [
            [sg.Column(lensFamFrame)],
            [sg.Column(comPortFrame)],
            [sg.Column(initMotorsFrame, element_justification='center', expand_x=True)]
            ]

        # motor control sub-frames
        defaultSteps = '100' if ENABLE_LENS_IQ_FUNCTIONS else '1000'        # change defaults steps based on IQ functions enabled
        relMoveFrame = [
            [sg.Button('Tele', size=(12,1), key='moveTeleBtn'), sg.Input(defaultSteps, size=(12,1), justification='center', disabled_readonly_background_color='LightGray', key='zoomStepFld'), 
                sg.Button('Wide', size=(12,1), key='moveWideBtn')],
            [sg.Button('Near', size=(12,1), key='moveNearBtn'), sg.Input(defaultSteps, size=(12,1), justification='center', disabled_readonly_background_color='LightGray', key='focusStepFld'), 
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
        IRCFrame = [
            [sg.Text('Internal filter:', size=(12,1)), sg.Button('Filter 1\n(Visible)', size=(11,2), key='IRCBtn1'), sg.Button('Filter 2\n(Visible + IR)', size=(11,2), key='IRCBtn2')]
        ]
        liveControlFrame = []
        liveControlFrame.append([sg.Image(TheiaLogoImagePath), sg.Column(headerFrame)])
        if ENABLE_LENS_IQ_FUNCTIONS:
            lensIQTopFrame, lensIQBottomFrame = IQEP.lensIQGUILayout()
            liveControlFrame.append([sg.Frame('IQ Lens™', lensIQTopFrame, expand_x=True)])
            liveControlFrame.append([sg.Frame('', lensIQBottomFrame, expand_x=True)])
        liveControlFrame.append([sg.Frame('Relative move', relMoveFrame), sg.Frame('Current', curPosFrame), sg.Frame('Absolute move', absMoveFrame)])
        liveControlFrame.append([sg.Column(IRCFrame)])
        liveControlFrame.append([sg.Frame(title='', layout=footerFrame, expand_x=True)])
                    
        # overall layout
        layout = [
            [sg.Frame('Motor control', liveControlFrame, expand_x=True)]
            ] 
        title = 'Theia IQ Lens™ control' if ENABLE_LENS_IQ_FUNCTIONS else 'Theia MCR IQ™ control' 
        window = sg.Window(title, layout, finalize=True)
        return window

    ##################################################
    ### main application routine 
    ##################################################
    if ENABLE_LENS_IQ_FUNCTIONS: IQEP = lensIQ_expansion.IQExpansionPack()
    settings = readSettingsFile()
    comPort = settings.get('comPort', '')
    comPortList = searchComPorts()
    if comPort not in comPortList:
        comPort = ''

    # default lens setup
    lensData = readLensDataFile()
    if lensData == None:
        sg.popup_ok('Lens data file not found', title='Error')
        return
    lensFamiliesList = list(lensData.keys())
    lastLensFamily = settings.get('lastLensFamily', 'TL1250P Nx')
    
    # create the GUI window
    window = mainGUILayout()
    # key bindings
    window['zoomCurFld'].bind('<Return>', 'Update')
    window['focusCurFld'].bind('<Return>', 'Update')
    window['irisCurFld'].bind('<Return>', 'Update')
    setStatus('notInit')
    enableLiveFrame(False)

    # Lens IQ setup variables
    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.setup(window, settings, setStatus)

    while (True):
        sourceWindow, event, values = sg.read_all_windows()
        #log.debug(f"Event: {event}\n{values}")
        if event in (sg.WIN_CLOSED, 'exitBtn'):
            if sourceWindow == window:
                # close application
                break
            else:
                IQEP.closeWindow(sourceWindow)

        elif (event == 'cp_lensFam'):
            newLensFamily = checkNewLensFamily(values['cp_lensFam'])
            if newLensFamily != None: 
                lastLensFamily = newLensFamily
                settings['lastLensFamily'] = lastLensFamily
                window['calFile'].update('')

        elif event == 'cp_port':
            newComPort = values['cp_port']
            if newComPort != comPort:
                comPort = newComPort
                settings['comPort'] = comPort
                # cancel motor initialization status
                setStatus('notInit')
                enableLiveFrame(False)
                MCRInitialized = False

        elif event == 'cp_refresh':
            newComPortList = searchComPorts()
            window['cp_port'].update(values=sorted(newComPortList))
            if comPort not in newComPortList:
                # previously selected comPort no longer available, choose the last one in the new list
                comPort = newComPortList[-1] if len(newComPortList) >= 1 else ''
                if comPort != '':
                    settings['comPort'] = comPort
                # cancel motor initialization status
                setStatus('notInit')
                enableLiveFrame(False)
                MCRInitialized = False
            window['cp_port'].update(comPort)

        elif event == 'cp_limitCheck':
            setRegardLimits(values['cp_limitCheck'])

        elif event == 'cp_backlash':
            regardBacklash = setRegardBacklash(values['cp_backlash'])
    
        elif event == 'motorInitBtn':
            if comPort != '':
                MCRInitialized = initMCR(MCRCom=comPort, homeMotors=False, lensFam=lastLensFamily, MCRInitialized=MCRInitialized, regardLimits=False)
            else:
                log.error("** Com port is blank")
                sg.popup_ok('Com port is blank', title='Error')
        
        elif event == 'motorInitHomeBtn':
            if comPort != '':
                MCRInitialized = initMCR(lensFam=lastLensFamily, MCRCom=comPort, homeMotors=True, MCRInitialized=MCRInitialized, regardLimits=True)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateCalibrationFile()
            else:
                log.error("** Com port is blank")
                sg.popup_ok('Com port is blank', title='Error')

        elif event == 'settingsPopup':
            # open the settings popup window.  The communication path for this program will always be 'USB'.  
            settingsValues = settingsGUI('USB')
            if settingsValues != None:
                if settingsValues['focusSpeed'] != '' or settingsValues['zoomSpeed'] != '' or settingsValues['irisSpeed'] != '':
                    setMotorSpeeds(settingsValues['focusSpeed'], settingsValues['zoomSpeed'], settingsValues['irisSpeed'])
                if settingsValues['comUART'] or settingsValues['comI2C']:
                    # communications path was set to something else and USB is no longer available. 
                    if comPort == '':
                        log.error('** Com port is blank')
                        sg.popup_ok('Com path not changed: Com port is blank', title='Error')
                        continue
                    if not MCRInitialized: 
                        MCR = TheiaMCR.MCRControl(comPort)
                        if not MCR.MCRInitialized:
                            log.error('** Com path not changed: MCR not initialized')
                            sg.popup_ok('Motor control initalization error, communication path not changed', title='Error')
                            MCR = None
                            continue
                        MCRInitialized = True
                    MCR.MCRBoard.setCommunicationPath('UART' if settingsValues['comUART'] else 'I2C')
                    sg.popup_ok(f'New communication path was set to {"UART" if settingsValues["comUART"] else "I2C"}.  USB communication is no longer available and this application will end.', title='New com path')
                    break
        
        elif event == 'IRCBtn1':
            window['IRCBtn1'].update(button_color=IRCSelectedColor)
            window['IRCBtn2'].update(button_color=TheiaDarkBlueColor)
            MCR.IRCState(1)
            
        elif event == 'IRCBtn2':
            window['IRCBtn1'].update(button_color=TheiaDarkBlueColor)
            window['IRCBtn2'].update(button_color=IRCSelectedColor)
            MCR.IRCState(2)

        if ENABLE_LENS_IQ_FUNCTIONS: 
            lensFamily = IQEP.checkEvents(sourceWindow == window, event, values)
            newLensFamily = checkNewLensFamily(lensFamily)
            if newLensFamily != None: 
                lastLensFamily = newLensFamily
                settings['lastLensFamily'] = lastLensFamily
                window['cp_lensFam'].update(lastLensFamily)

        if MCRInitialized and event in {'moveWideBtn', 'moveTeleBtn', 'moveNearBtn', 'moveFarBtn', 'moveOpenBtn', 'moveCloseBtn', 'moveZoomAbsBtn', 'moveFocusAbsBtn', 'moveIrisAbsBtn', 'zoomCurFldUpdate', 'focusCurFldUpdate', 'irisCurFldUpdate'}:
            setStatus('moving')
            if event == 'moveWideBtn':
                # move zoom motor
                MCR.zoom.moveRel(int(values['zoomStepFld']), correctForBL=regardBacklash)
                # update field
                window['zoomCurFld'].update(MCR.zoom.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterZoom()

            elif event == 'moveTeleBtn':
                # move zoom motor
                MCR.zoom.moveRel(-int(values['zoomStepFld']), correctForBL=regardBacklash)
                # update field
                window['zoomCurFld'].update(MCR.zoom.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterZoom()

            elif event == 'moveNearBtn':
                # move focus motor
                MCR.focus.moveRel(-int(values['focusStepFld']), correctForBL=regardBacklash)
                # update field
                window['focusCurFld'].update(MCR.focus.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterFocus(changeOD=False)

            elif event == 'moveFarBtn':
                # move focus motor
                MCR.focus.moveRel(int(values['focusStepFld']), correctForBL=regardBacklash)
                # updated field
                window['focusCurFld'].update(MCR.focus.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterFocus(changeOD=False)

            elif event == 'moveOpenBtn':
                # move iris motor
                MCR.iris.moveRel(-int(values['irisStepFld']), correctForBL=False)
                # update field
                window['irisCurFld'].update(MCR.iris.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterIris()

            elif event == 'moveCloseBtn':
                # move iris motor
                MCR.iris.moveRel(int(values['irisStepFld']), correctForBL=False)
                # updated field
                window['irisCurFld'].update(MCR.iris.currentStep)
                if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterIris()

            elif event in {'moveZoomAbsBtn', 'zoomCurFldUpdate'}:
                if absMoveInit:
                    # move to absolute position
                    MCR.zoom.moveAbs(int(values['zoomCurFld']))
                    # confirm update field
                    window['zoomCurFld'].update(MCR.zoom.currentStep)
                    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterZoom()

            elif event in {'moveFocusAbsBtn', 'focusCurFldUpdate'}:
                if absMoveInit:
                    # move to absolute position
                    MCR.focus.moveAbs(int(values['focusCurFld']))
                    # confirm update field
                    window['focusCurFld'].update(MCR.focus.currentStep)
                    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterFocus(changeOD=False)

            elif event in {'moveIrisAbsBtn', 'irisCurFldUpdate'}:
                if absMoveInit:
                    # move to absolute position
                    MCR.iris.moveAbs(int(values['irisCurFld']))
                    # confirm update field
                    window['irisCurFld'].update(MCR.iris.currentStep)
                    if ENABLE_LENS_IQ_FUNCTIONS: IQEP.updateAfterIris()
            
            ####### check for unknown position
            setStatus('ready')

    window.close()
    return


# call the app function in threading mode to allow user interaction while tests are running
if __name__ == '__main__':
    app()