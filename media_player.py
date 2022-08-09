import logging
from .pioneer_device import PioneerDevice
from .pioneer_amp    import PioneerAmp
from .const import *

import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA

from homeassistant.components.media_player.const import (
    DOMAIN,
    ATTR_SOUND_MODE,
)

from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_HOST, CONF_NAME, CONF_PORT, CONF_ZONE
)

import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

MEDIA_PLAYER_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.comp_entity_ids,
})

ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE): vol.In(CONF_VALID_ZONES, CONF_INVALID_ZONES_ERR),
        vol.Optional(CONF_NAME): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_SERIAL_BRIDGE, default=False): cv.boolean,
    vol.Optional(CONF_DISABLED_SOURCES): [cv.string],
    vol.Optional(CONF_LAST_RADIO_STATION): cv.string,
    vol.Optional(CONF_RADIO_STATIONS): {cv.string: cv.string},
    vol.Optional(CONF_ZONES): vol.All(cv.ensure_list, [ZONE_SCHEMA]),
    vol.Optional(CONF_INPUTS): {cv.string: cv.string},
})

pioneer_speaker_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SPEAKER): vol.In(ACCEPTED_SPEAKER_VALUES)
})

pioneer_hdmi_out_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_HDMI_OUT): vol.In(ACCEPTED_HDMI_OUT_VALUES)
})

pioneer_select_sound_mode_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SOUND_MODE): cv.string
})

pioneer_speaker_config_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SPEAKER_CONFIG): vol.In(ACCEPTED_SPEAKER_CONFIG_VALUES)
})

pioneer_radio_station_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_STATION): cv.string
})

pioneer_dim_display_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_DIM_DISPLAY): vol.In([0, 1, 2, 3])
})


async def async_setup_platform(hass, config, async_add_entities, \
                               discovery_info=None):
    _LOGGER.debug("setup starting")
    devices = []

    if DATA_PIONEER not in hass.data:
        hass.data[DATA_PIONEER] = []

    hasZones = False
    zones = config.get(CONF_ZONES)
    if zones is not None:
        hasZones = True
        add_zones = {}
        for entry in zones:
            add_zones[entry[CONF_ZONE]] = entry.get(CONF_NAME)
    else:
        add_zones = None

    pioneer = PioneerAmp(
        hass,
        config.get(CONF_HOST),
        config.get(CONF_PORT),
        config.get(CONF_SERIAL_BRIDGE),
        config.get(CONF_DISABLED_SOURCES),
        config.get(CONF_LAST_RADIO_STATION),
        config.get(CONF_RADIO_STATIONS),
        hasZones,
        config.get(CONF_INPUTS)
    )

    mainZone = PioneerDevice(        
        config.get(CONF_NAME),
        "Main",
        pioneer
    )

    hass.data[DATA_PIONEER].append(mainZone)
    devices.append(mainZone)
    pioneer._device_main = mainZone

    if hasZones:
        for zone in add_zones.keys():
            _LOGGER.debug(f"adding new zone '{zone}'")
            pioneer_z = PioneerDevice(
                config.get(CONF_NAME) + "_" + zone,
                zone,
                pioneer
                )
            hass.data[DATA_PIONEER].append(pioneer_z)
            devices.append(pioneer_z)
            if zone == "Zone2":
                pioneer._device_zone2 = pioneer_z
            if zone == "HDZone":
                pioneer._device_hdzone = pioneer_z

    _LOGGER.debug("adding pio devices")
    async_add_entities(devices, update_before_add=False)

    hass.loop.create_task(pioneer.readdata())


    async def async_service_handler(service):
        """Handle for services."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        if entity_ids:
            devices = [device for device in hass.data[DATA_PIONEER]
                       if device.entity_id in entity_ids]
        else:
            devices = hass.data[DATA_PIONEER]

        for device in devices:
            if service.service == SERVICE_SELECT_SPEAKER:
                speaker = service.data.get(ATTR_SPEAKER)
                device.select_speaker(speaker)

            if service.service == SERVICE_SELECT_SPEAKER_CONFIG:
                speaker_config = service.data.get(ATTR_SPEAKER_CONFIG)
                device.select_speaker_config(speaker_config)

            if service.service == SERVICE_SELECT_RADIO_STATION:
                station = service.data.get(ATTR_STATION)
                device.select_radio_station(station)

            if service.service == SERVICE_DIM_DISPLAY:
                dim_display = service.data.get(ATTR_DIM_DISPLAY)
                device.dim_display(dim_display)

            if service.service == SERVICE_SELECT_HDMI_OUT:
                hdmi_out = service.data.get(ATTR_HDMI_OUT)
                device.select_hdmi_out(hdmi_out)

            if service.service == SERVICE_SELECT_SOUND_MODE:
                sound_mode = service.data.get(ATTR_SOUND_MODE)
                device.select_sound_mode(sound_mode)

            device.async_schedule_update_ha_state(True)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_SPEAKER, async_service_handler,
        schema=pioneer_speaker_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_SPEAKER_CONFIG, async_service_handler,
        schema=pioneer_speaker_config_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_RADIO_STATION, async_service_handler,
        schema=pioneer_radio_station_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_DIM_DISPLAY, async_service_handler,
        schema=pioneer_dim_display_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_HDMI_OUT, async_service_handler,
        schema=pioneer_hdmi_out_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_SOUND_MODE, async_service_handler,
        schema=pioneer_select_sound_mode_schema)

