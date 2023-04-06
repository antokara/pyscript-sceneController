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
config={
    'downstairsController': {}
}
def loadConfig():
    # load all the scenes configurations
    # because it is the only way to get the state of each entity, in each scene
    # otherwise, we only get the list of entities of a scene...
    # TODO: reload somehow on change and update everything. make it a function
    # that gets called at init and on change with trigger from scenes Create/Update/Delete
    with open('/config/scenes.yaml', 'r') as file:
        scenes = yaml.safe_load(file)

    config['downstairsController'] = {
        # the z-wave scene controller, node_id
        # that triggers the scene changes
        'nodeId': 78,
        # the entities (lights, switches, etc.)
        # that are involved in the scenes and should
        # cause the trigger of scene controller LEDs to change
        'triggerEntities':[],
        # the configuration of the filtered scenes
        'scenes': [scene for scene in scenes if scene['name'] in [
            # the names of the scenes, case-sensitive
            # not their ids or entity ids
            'Downstairs - all lights',
            'Downstairs - cooking lights',
            'Downstairs - dining lights',
            'Downstairs - lounge lights',
        ]],
        'offScene': 'scene.downstairs_all_lights_off',
        # which buttons on the controller,
        # should trigger a scene activation
        'buttons':[
            {
                # the identifier used in events of type:
                # zwave_js_value_notification
                # to know which event/button, does what
                'label': 'Scene 001',
                # the zwave parameter for the LED of the scene button
                'ledParameter': '2',
                # the name part of the entity id, of the scene to apply
                'scene': 'downstairs_cooking_lights',
                'sceneFriendlyName': 'Downstairs - cooking lights',
            },
            {
                'label': 'Scene 002',
                'ledParameter': '3',
                'scene': 'downstairs_dining_lights',
                'sceneFriendlyName': 'Downstairs - dining lights',
            },
            {
                'label': 'Scene 003',
                'ledParameter': '4',
                'scene': 'downstairs_lounge_lights',
                'sceneFriendlyName': 'Downstairs - lounge lights',
            },
            {
                'label': 'Scene 004',
                'ledParameter': '5',
                'scene': 'downstairs_all_lights',
                'sceneFriendlyName': 'Downstairs - all lights',
            }
        ]
    }


    # TODO: iterate each controller...
    # grab the unique trigger entities from all the scenes we have
    # as well as any supported attributes they may have
    config['downstairsController']['triggerEntities']=[]
    for scene in config['downstairsController']['scenes']:
        for entity in scene['entities'].items():
            # in case this entity has brightness, which we support
            # add it as a trigger
            if 'brightness' in entity[1] and f'{entity[0]}.brightness' not in config['downstairsController']['triggerEntities']:
                config['downstairsController']['triggerEntities'].append(f'{entity[0]}.brightness')
            # for simple state, add the entity
            if entity[0] not in config['downstairsController']['triggerEntities']:
                config['downstairsController']['triggerEntities'].append(entity[0])
                

loadConfig()

a=config['downstairsController']['triggerEntities']
logMsg(message=f'triggerEntities:  {a}')

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
    for scene in scenes:
        if sceneFriendlyName==scene['name']:
            for entityTuple in scene['entities'].items():
                entityId=entityTuple[0]
                entity=scene['entities'][entityId]
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

# triggerEntities = [*map(config['downstairsController']['scenes'].get, lst)]
# triggerEntities = [*map(lambda scene: scene['entities'], config['downstairsController']['scenes'])]
# [*map(lambda scene: scene['entities'], config['downstairsController']['scenes'])]

# triggerEntities = [*map(lambda scene: 
#     [*map(lambda entity: entity, scene['entities'])]
#     , config['downstairsController']['scenes'])]

# scene.downstairs_all_lights
# scene.downstairs_cooking_lights
# scene.downstairs_dining_lights
# scene.downstairs_lounge_lights
# scene.downstairs_all_lights_off

# zwave config call
# serviceCall={
#     'domain': 'zwave_js',
#     'name': 'set_config_parameter',
#     'kwargs': {
#         'parameter': '2',
#         'value': '2',
#         'entity_id': 'switch.kitchen_scene_controller'
#     }
# }
# service.call(
#     serviceCall['domain'],
#     serviceCall['name'],
#     **serviceCall['kwargs']
# )

# scene call
# serviceCall={
#     'domain': 'scene',
#     'name': 'turn_on',
#     'kwargs': {
#         'entity_id': 'scene.downstairs_all_lights_off'
#     }
# }
# service.call(
#     serviceCall['domain'],
#     serviceCall['name'],
#     **serviceCall['kwargs']
# )

# TODO: iterate for each controller
# makes sure the LEDs of the scene controller
# are turned on/off appropriately
@state_trigger(config['downstairsController']['triggerEntities'])
@time_trigger('once(now)')
def controllerLeds():
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