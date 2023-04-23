from datetime import datetime
from builtins import open
import yaml

#
# Standard
#

# the name of the script
SCRIPT_NAME='sceneController'
# the variable name prefix of state variables
STATE_VAR_PREFIX=f'pyscript.{SCRIPT_NAME}_'

# logs the message to the Logbook
def logMsg(message):
    logbook.log(name=SCRIPT_NAME, message=message)

# status
logMsg(message='loading...')

# returns the state variable name with the prefix
def var_name(name):
    return f'{STATE_VAR_PREFIX}{name}'

#
# Custom
#

# returns either the brightness integer or
#  None, if not supported and when the state is off
def getBrightness(entityName):
    try:
        brightness=int(state.get(f'{entityName}.brightness'))
    except:
        brightness=None
    return brightness


# uses the list of scenes provided to find the sceneFriendlyName
# and to compare its state, against the scenes
def isSceneActive(scenes, sceneFriendlyName):
    isActive=True
    for sceneName, sceneConfig in scenes.items():
        if sceneFriendlyName==sceneName:
            for entityId, entityConfig in sceneConfig['entities'].items():
                # first and foremost, check the on/off state
                # there's no need to proceed and check other
                # features, if that's incorrect...
                if state.get(entityId)!=entityConfig['state']:
                    # on/off state
                    isActive=False
                if isActive and 'brightness' in entityConfig and getBrightness(entityId) != entityConfig['brightness']:
                    # brightness mismatch
                    isActive=False
                    
                # check the color (if supported)
    return isActive

def controllerLedsTriggerFactory(controllerName, controllerConfig):
    # makes sure the LEDs of the scene controller
    # are turned on/off appropriately
    @state_trigger(controllerConfig['triggerEntities'])
    @time_trigger('once(now)')
    def controllerLeds():
        # change unique ID to be per controller ID
        task.unique(f'sceneController_leds__{controllerName}', kill_me=True)
        for button in controllerConfig['buttons']:
            # find if the scene is currently on/off
            if isSceneActive(scenes=controllerConfig['scenes'], sceneFriendlyName=button['sceneFriendlyName']):
                # turn the LED on
                service.call(
                    'zwave_js',
                    'set_config_parameter',
                    parameter=button['ledParameter'],
                    value='2',
                    entity_id=controllerConfig['entityId']
                )
            else:
                # turn the LED off 
                service.call(
                    'zwave_js',
                    'set_config_parameter',
                    parameter=button['ledParameter'],
                    value='3',
                    entity_id=controllerConfig['entityId']
                )
    return controllerLeds

# keep a list of the controller led trigger closures
controllerLedsTriggers=[]

# when the scenes change and reload
# we also need to reload their config file
# in order to reflect their changes
@event_trigger('scene_reloaded')
def loadScenesConfig():
    logMsg(message='loading config...')

    # new triggers
    controllerLedsTriggers.clear()

    # load all the scenes configurations
    # because it is the only way to get the state of each entity, in each scene
    # otherwise, we only get the list of entities of a scene...
    with open('/config/scenes.yaml', 'r') as file:
        scenesConfig = yaml.safe_load(file)

    # iterate each controller... 
    for controllerName, controllerConfig in pyscript.app_config['controllers'].items():
        # grab the scene config, of each scene, using its name
        for sceneName in controllerConfig['scenes']:
            controllerConfig['scenes'][sceneName]=[sceneConfigItem for sceneConfigItem in scenesConfig if sceneConfigItem['name'] == sceneName][0]

        # grab the unique trigger entities from all the scenes we have
        # as well as any supported attributes they may have
        controllerConfig['triggerEntities']=[]
        for sceneName, sceneConfig in controllerConfig['scenes'].items():
            # add the triggerEntities for this scene
            for entityName, entityConfig in sceneConfig['entities'].items():
                # in case this entity has brightness, which we support
                # add it as a trigger
                if 'brightness' in entityConfig and f'{entityName}.brightness' not in controllerConfig['triggerEntities']:
                    controllerConfig['triggerEntities'].append(f'{entityName}.brightness')
                # for simple state, add the entity
                if entityName not in controllerConfig['triggerEntities']:
                    controllerConfig['triggerEntities'].append(entityName)

        # add the closure to the list
        controllerLedsTriggers.append(controllerLedsTriggerFactory(controllerName=controllerName, controllerConfig=controllerConfig))

    logMsg(message='config loaded!')

# perform the initial scene config load
loadScenesConfig()

def controllerButtonsTriggerFactory(controllerName, controllerConfig):
    # handles the scene controller button clicks,
    # for the zwave node_id provided
    # to turn on the proper scene
    @event_trigger('zwave_js_value_notification', f"domain == 'zwave_js' and node_id == {(controllerConfig['nodeId'])}")
    def controllerButtons(**kwargs):
        task.unique(f'sceneController_buttons__{controllerName}', kill_me=True)
        for button in controllerConfig['buttons']:
            if button['label']==kwargs['label']:
                # find if the scene is currently on/off
                if isSceneActive(scenes=controllerConfig['scenes'], sceneFriendlyName=button['sceneFriendlyName']):
                    # turn the scene off
                    service.call(
                        'scene',
                        'turn_on',
                        entity_id=controllerConfig['offScene']
                    )
                else:
                    # turn the scene on
                    service.call(
                        'scene',
                        'turn_on',
                        entity_id=f"scene.{button['scene']}"
                    )
    return controllerButtons

# build the triggers for each controller
controllerButtonsTriggers=[]
for controllerName, controllerConfig in pyscript.app_config['controllers'].items():
    controllerButtonsTriggers.append(controllerButtonsTriggerFactory(controllerName=controllerName, controllerConfig=controllerConfig))

# status
logMsg(message='loaded!')