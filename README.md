# pyscript scene controller

A home assistant pyscript for scene controllers.

It allows you to configure easily, a z-wave (for now) scene controller and map its buttons, to different home assistant scenes. When clicking any of the mapped buttons, if the scene is not active, it activates it and turns off the button's LED. If the scene is already active, it activates a specific scene, that resets all the scenes (e.g. turn off all the lights or whatever state you prefer).

It automatically keeps the LEDs of the scene controller's buttons in sync with all the mapped scenes. Meaning, if a scene gets activated/deactivated by action(s) outside of the scene controller, it will immediatelly pickup the change and toggle the LEDs appropriately.

## setup

1. install pyscript (if not already installed)
1. if any of the mentioned directories do not exist, you need to create them
1. copy the contents of this repository into `config/pyscript/apps/sceneController`
1. create the pyscript config file (if not already created) `config/pyscript/config.yaml`
1. insert the config under `apps` -> `sceneController`

## example config

```yaml
apps:
  sceneController:
    controllers:
      # the name of your controller
      # it can be anything
      downstairsController:
        # the z-wave scene controller, node_id
        # that triggers the scene changes
        nodeId: 78
        # the entities (lights, switches, etc.)
        # that are involved in the scenes and should
        # cause the trigger of scene controller LEDs to change
        triggerEntities:
        # the names of the scenes, case-sensitive
        # not their ids or entity ids
        # @see config/scenes.yaml (name prop)
        scenes:
          "Downstairs - all lights":
          "Downstairs - cooking lights":
          "Downstairs - dining lights":
          "Downstairs - lounge lights":
        # the entity ID to trigger (e.g. scene)
        # when wanting to turn off everything,
        # related to this controller
        offScene: scene.downstairs_all_lights_off
        # map each button on the scene controller to:
        # - its z-wave event label (to know when it got pressed)
        # - its z-wave config parameter, that toggles its LED (to be able to toggle its LED)
        # - a scene (to activate when pressing the button)
        buttons:
          - one:
            # the identifier used in events of type:
            # zwave_js_value_notification
            # to know which event/button, does what
            label: "Scene 001"
            # the zwave parameter for the LED of the scene button
            ledParameter: 2
            # the name part of the entity id, of the scene to apply
            # TODO: translate the sceneFriendlyName to this, to avoid redundant config
            scene: downstairs_cooking_lights
            # the name, as-is in the config/scenes.yaml (name prop)
            sceneFriendlyName: "Downstairs - cooking lights"
          - two:
            label: "Scene 002"
            ledParameter: 3
            scene: downstairs_dining_lights
            sceneFriendlyName: "Downstairs - dining lights"
          - three:
            label: "Scene 003"
            ledParameter: 4
            scene: downstairs_lounge_lights
            sceneFriendlyName: "Downstairs - lounge lights"
          - four:
            label: "Scene 004"
            ledParameter: 5
            scene': downstairs_all_lights
            sceneFriendlyName: "Downstairs - all lights"
```
