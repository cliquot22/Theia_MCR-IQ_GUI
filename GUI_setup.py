# GUI window creation for Theia_lensIQ_GUI
#
# v.1.0.0 250811 initial creation extracted from v.2.5.7 Theia_lensIQ_GUI.py

from PSG_license import PySimpleGUI_License
import PySimpleGUI as sg

import logging
log = logging.getLogger(__name__)
# set lensIQ sub module log level
lensIQLogLevel = logging.INFO

import utilities

class LensIQGUI:
    TheiaLogoImagePath = utilities.resourcePath('data/Theia_logo.png')
    TheiaMenuIcon = utilities.resourcePath('data/TL1250P.ico')
    TheiaColorTheme = 'LightGrey1'
    TheiaLightGreenColor = '#00CC66'
    TheiaWhiteColor = '#FFFFFF'
    TheiaGreenColor = '#006633'
    TheiaDarkBlueColor = '#333399'
    TheiaLightBlueColor = '#3366CC'
    IRCSelectedColor = TheiaGreenColor                  # color for selected IRC filter

    def __init__(self, settingsIconPath:str, IQFunctions):
        '''
        Set up the GUI window.  
        ### input: 
        - settingsIconPath: the path to the settings gear icon
        - IQFunctions: The lensIQ_expansion module or None (if MCR IQ state)
        '''
        self.settingsIconPath = settingsIconPath
        self.TheiaLogoImagePath = LensIQGUI.TheiaLogoImagePath
        self.IQFunctions = IQFunctions
        self.window = self.mainGUILayout()

    # mainGUILayout
    def mainGUILayout(self):
        '''
        Main GUI layout. 
        Create the GUI window for the main window.  
        There is a live motor control section, measurement section, settings section, and optional monitor 
        section when the test is running.  
        The section for converting from engineering units to motor steps is supported by Lens IQ module functions.  
        ### return: 
        [handle to the window]
        '''
        sg.theme(LensIQGUI.TheiaColorTheme) 
        sg.set_global_icon(LensIQGUI.TheiaMenuIcon)
        sg.set_options(button_color=[LensIQGUI.TheiaWhiteColor, LensIQGUI.TheiaDarkBlueColor])
        # footer frame
        footerFrame = [
            [sg.Text(utilities.revision, size=(12,1), font='Helvetica 8'),
                sg.Text('', size=(20,1), font='Helvetica 8', key='fldFWRev'),
                sg.Text('', size=(20,1), font='Helvetica 8', key='fldSNBoard'),
                sg.Push(), 
                sg.Image(filename=self.settingsIconPath, key='settingsPopup', enable_events=True),
                sg.Button('Quit', size=(12,1), key="exitBtn")]
        ]

        # Live lens motor control section
        # lens family sub-frame
        lensFamFrame = [
            [sg.Text('Lens family', size=(10,1)), sg.Combo([], size=(18,10), enable_events=True, key='cp_lensFam')]
            ]
        # comPort selection sub-frame
        comPortFrame = [
            [sg.Text('Com port', size=(10,1)), sg.Combo([], size=(18,10), enable_events=True, key="cp_port"), 
                sg.Button('Refresh', size=(6,1), key='cp_refresh')],
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
        defaultSteps = '100' if self.IQFunctions else '1000'        # change defaults steps based on IQ functions enabled
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
        liveControlFrame.append([sg.Image(self.TheiaLogoImagePath), sg.Column(headerFrame)])
        if self.IQFunctions:
            lensIQTopFrame, lensIQBottomFrame = self.IQFunctions.lensIQGUILayout()
            liveControlFrame.append([sg.Frame('IQ Lens™', lensIQTopFrame, expand_x=True)])
            liveControlFrame.append([sg.Frame('', lensIQBottomFrame, expand_x=True)])
        liveControlFrame.append([sg.Frame('Relative move', relMoveFrame), sg.Frame('Current', curPosFrame), sg.Frame('Absolute move', absMoveFrame)])
        liveControlFrame.append([sg.Column(IRCFrame)])
        liveControlFrame.append([sg.Frame(title='', layout=footerFrame, expand_x=True)])
                    
        # overall layout
        layout = [
            [sg.Frame('Motor control', liveControlFrame, expand_x=True)]
            ] 
        title = 'Theia IQ Lens™ control' if self.IQFunctions else 'Theia MCR IQ™ control' 
        self.window = sg.Window(title, layout, finalize=True)

        # key bindings
        self.window['zoomCurFld'].bind('<Return>', 'Update')
        self.window['focusCurFld'].bind('<Return>', 'Update')
        self.window['irisCurFld'].bind('<Return>', 'Update')
        return self.window

    # setting window 
    def settingsGUI(self, initialProtocol:str, MCR, GUIActions) -> dict | None:
        '''
        Create a window for additional settings.  This function handles the window and returns the values once it is closed.  
        This window includes communication path and motor speeds.  
        Once set by the user, the motor speeds are written to the board and the communication path is updated.  
        If the user cancels, nothing is changed and the return value is 'None'.  
        ### input:
        - initialProtocol: current communication path string ('USB', 'UART', 'I2C')
        - MCR: the handle to the MCR module
        - GUIActions: the handle to the GUI actions module
        ### return: 
        [settings values | None]
        '''
        # check if MCR is initialized
        if not MCR:
            sg.popup_ok('Motor control must be initialized first', title='Error')
            return None

        # motor speeds
        speedsLayout = [
            [sg.Text('', size=(16,1)), sg.Text('Moving', size=(7,1)), sg.Text('Homing', size=(7,1))],
            [sg.Text('Focus motor speed', size=(16,1)), sg.Input('', size=(7,1), key='focusSpeed', disabled=True), sg.Input('', size=(7,1), key='focusHomeSpeed', disabled=True)],
            [sg.Text('Zoom motor speed', size=(16,1)), sg.Input('', size=(7,1), key='zoomSpeed', disabled=True), sg.Input('', size=(7,1), key='zoomHomeSpeed', disabled=True)],
            [sg.Text('Iris motor speed', size=(16,1)), sg.Input('', size=(7,1), key='irisSpeed', disabled=True), sg.Input('', size=(7,1), key='irisHomeSpeed', disabled=True)],
        ]
        # communication path
        comLayout = [
            [sg.Text('Warning: Changing the communication path will reboot the controller board and the original communication path will no longer be active', 
                        size=(30,4), text_color='red')],
            [sg.Button('Change com path', key='changePath')],
            [sg.Radio('USB', group_id='comGroup', default=(initialProtocol == 'USB'), key='comUSB', visible=False), 
                sg.Radio('UART', group_id='comGroup', default=(initialProtocol == 'UART'), key='comUART', visible=False), 
                sg.Radio('I2C', group_id='comGroup', default=(initialProtocol == 'I2C'), key='comI2C', visible=False)]
        ]
        # additional settings
        addLayout = [
            [sg.Checkbox('Backlash', default=True, key='cp_backlash')],
            [sg.Checkbox('Regard limits', default=True, key='cp_limitCheck')],
            [sg.Checkbox('Slow home approach', key='slowHome', default=True)]
        ]
        layout = [
            [sg.Frame('Motor speeds', speedsLayout, expand_x=True)], 
            [sg.Frame('Additional settings', addLayout)],
            [sg.Frame('Communication', comLayout)],
            [sg.Button('Save settings', key='save'), sg.Button('Cancel', key='discard')]
        ]

        window = sg.Window('Set values', layout, modal=True, finalize=True)
        if MCR.MCRInitialized:
            window['focusSpeed'].update(MCR.focus.currentSpeed)
            window['focusSpeed'].update(disabled=False)
            window['focusHomeSpeed'].update(MCR.focus.homingSpeed)
            window['focusHomeSpeed'].update(disabled=False)
            window['zoomSpeed'].update(MCR.zoom.currentSpeed)
            window['zoomSpeed'].update(disabled=False)
            window['zoomHomeSpeed'].update(MCR.zoom.homingSpeed)
            window['zoomHomeSpeed'].update(disabled=False)
            window['irisSpeed'].update(MCR.iris.currentSpeed)
            window['irisSpeed'].update(disabled=False)
            window['irisHomeSpeed'].update(MCR.iris.homingSpeed)
            window['irisHomeSpeed'].update(disabled=False)
            window['slowHome'].update(MCR.focus.slowHomeApproach)
            window['cp_backlash'].update(GUIActions.regardBacklash)
            window['cp_limitCheck'].update(GUIActions.regardLimits)

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