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

# pull the app config
config=pyscript.app_config['controllers']

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
    for scene in scenes.items():
        if sceneFriendlyName==scene[0]:
            for entityTuple in scene[1]['entities'].items():
                entityId=entityTuple[0]
                entity=scene[1]['entities'][entityId]
                # first and foremost, check the on/off state
                # there's no need to proceed and check other
                # features, if that's incorrect...
                if state.get(entityId)!=entity['state']:
                    # on/off state
                    isActive=False
                if isActive and 'brightness' in entity and getBrightness(entityId) != entity['brightness']:
                    # brightness mismatch
                    isActive=False
                    
                # check the color (if supported)
    return isActive

# when the scenes change and reload
# we also need to reload their config file
# in order to reflect their changes
# TODO: re-register all the triggers based on their entities
@event_trigger('scene_reloaded')
def loadConfig():
    logMsg(message='loading config...')

    # load all the scenes configurations
    # because it is the only way to get the state of each entity, in each scene
    # otherwise, we only get the list of entities of a scene...
    with open('/config/scenes.yaml', 'r') as file:
        scenesConfig = yaml.safe_load(file)

    # TODO: iterate each controller... 
    # grab the scene config, of each scene, using its name
    for sceneName in config['downstairsController']['scenes']:
        config['downstairsController']['scenes'][sceneName]=[sceneConfigItem for sceneConfigItem in scenesConfig if sceneConfigItem['name'] == sceneName][0]

    # TODO: iterate each controller...  
    # grab the unique trigger entities from all the scenes we have
    # as well as any supported attributes they may have
    config['downstairsController']['triggerEntities']=[]
    for scene in config['downstairsController']['scenes'].items():
        # add the triggerEntities for this scene
        for entity in scene[1]['entities'].items():
            # in case this entity has brightness, which we support
            # add it as a trigger
            if 'brightness' in entity[1] and f'{entity[0]}.brightness' not in config['downstairsController']['triggerEntities']:
                config['downstairsController']['triggerEntities'].append(f'{entity[0]}.brightness')
            # for simple state, add the entity
            if entity[0] not in config['downstairsController']['triggerEntities']:
                config['downstairsController']['triggerEntities'].append(entity[0])
    
    # TODO: iterate for each controller
    # makes sure the LEDs of the scene controller
    # are turned on/off appropriately
    @state_trigger(config['downstairsController']['triggerEntities'])
    @time_trigger('once(now)')
    def controllerLeds():
        # TODO: consider simultaneous scene changes in different room.
        # change unique ID to be per controller ID
        task.unique('sceneController_leds', kill_me=True)
        for button in config['downstairsController']['buttons']:
            # find if the scene is currently on/off
            if isSceneActive(scenes=config['downstairsController']['scenes'], sceneFriendlyName=button['sceneFriendlyName']):
                # turn the LED on
                service.call(
                    'zwave_js',
                    'set_config_parameter',
                    parameter=button['ledParameter'],
                    value='2',
                    entity_id='switch.kitchen_scene_controller'
                )
            else:
                # turn the LED off 
                service.call(
                    'zwave_js',
                    'set_config_parameter',
                    parameter=button['ledParameter'],
                    value='3',
                    entity_id='switch.kitchen_scene_controller'
                )

    logMsg(message='config loaded!')
    return controllerLeds

# keep the closure trigger(s)
triggers=loadConfig()

# TODO: iterate for each controller
# handles the scene controller button clicks,
# for the zwave node_id provided
# to turn on the proper scene
@event_trigger('zwave_js_value_notification', f"domain == 'zwave_js' and node_id == {(config['downstairsController']['nodeId'])}")
def controllerButtons(**kwargs):
    task.unique('sceneController_buttons', kill_me=True)
    for button in config['downstairsController']['buttons']:
        if button['label']==kwargs['label']:
            # find if the scene is currently on/off
            if isSceneActive(scenes=config['downstairsController']['scenes'], sceneFriendlyName=button['sceneFriendlyName']):
                # turn the scene off
                service.call(
                    'scene',
                    'turn_on',
                    entity_id=config['downstairsController']['offScene']
                )
            else:
                # turn the scene on
                service.call(
                    'scene',
                    'turn_on',
                    entity_id=f"scene.{button['scene']}"
                )

# status
logMsg(message='loaded!')