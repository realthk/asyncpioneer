import asyncio
import logging
import math
import re

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerEntity)

from homeassistant.components.media_player.const import (
    SUPPORT_PAUSE, SUPPORT_PLAY, SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET,
    MEDIA_TYPE_MUSIC, SUPPORT_PLAY_MEDIA, DOMAIN,
    SUPPORT_NEXT_TRACK, SUPPORT_PREVIOUS_TRACK,
    ATTR_APP_ID,
    ATTR_APP_NAME,
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_ALBUM_ARTIST,
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CHANNEL,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_ENQUEUE,
    ATTR_MEDIA_EPISODE,
    ATTR_MEDIA_PLAYLIST,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    ATTR_MEDIA_SEASON,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_SERIES_TITLE,
    ATTR_MEDIA_SHUFFLE,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_TRACK,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    ATTR_SOUND_MODE,
    ATTR_SOUND_MODE_LIST
)

from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_HOST, CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON,
    EVENT_HOMEASSISTANT_STOP,
    CONF_ZONE
)

import homeassistant.helpers.config_validation as cv
from time import sleep

CONF_INVALID_ZONES_ERR = "Invalid Zone (expected Zone2 or HDZone)"
CONF_VALID_ZONES = ["Main", "Zone2", "HDZone"]
CONF_ZONES = "zones"

SOURCE_ID_PHONO         = "00"
SOURCE_ID_CD            = "01"
SOURCE_ID_TUNER         = "02"
SOURCE_ID_DVD           = "04"
SOURCE_ID_TV            = "05"
SOURCE_ID_SAT           = "06"
SOURCE_ID_MULTI_CH      = "12"
SOURCE_ID_USB_DAC       = "13"
SOURCE_ID_BR            = "15"
SOURCE_ID_IPOD          = "17"
SOURCE_ID_HDMI1         = "19"
SOURCE_ID_HDMI2         = "20"
SOURCE_ID_HDMI3         = "21"
SOURCE_ID_HDMI4         = "22"
SOURCE_ID_HDMI5         = "23"
SOURCE_ID_HDMI6         = "24"
SOURCE_ID_BD            = "25"
SOURCE_ID_BT_AUDIO      = "33"
SOURCE_ID_HDMI7         = "34"
SOURCE_ID_INTERNET      = "38"
SOURCE_ID_PANDORA       = "41"
SOURCE_ID_MEDIA_SERVER  = "44"
SOURCE_ID_FAVORITES     = "45"

VALID_ZONE2_SOURCES =  ["04", "06", "15", "26", "38", "40", "41", "44", "45", "17", "13", "05", "01", "02", "33"]
VALID_HDZONE_SOURCES = ["04", "06", "15", "19", "20", "21", "22", "23", "24", "25", "34", "26", "38", "41", "41", "44", "45", "17", "13"]

LISTENING_MODES = {
	"0001": "STEREO",
	"0010": "STANDARD",
	"0009": "STEREO",
	"0011": "2ch",
	"0013": "PRO LOGIC2 MOVIE",
	"0018": "PRO LOGIC2x MOVIE",
	"0014": "PRO LOGIC2 MUSIC",
	"0019": "PRO LOGIC2x MUSIC",
	"0015": "PRO LOGIC2 GAME",
	"0020": "PRO LOGIC2x GAME",
	"0031": "PRO LOGIC2z HEIGHT",
	"0032": "WIDE SURROUND MOVIE",
	"0033": "WIDE SURROUND MUSIC",
	"0012": "PRO LOGIC",
	"0016": "Neo:6 CINEMA",
	"0017": "Neo:6 MUSIC",
	"0037": "Neo:X CINEMA",
	"0038": "Neo:X MUSIC",
	"0039": "Neo:X GAME",
	"0040": "Dolby Surround",
	"0021": "Multi ch",
	"0022": "DOLBY EX",
	"0023": "PRO LOGIC2x MOVIE",
	"0024": "PRO LOGIC2x MUSIC",
	"0034": "PRO LOGIC2z HEIGHT",
	"0035": "WIDE SURROUND MOVIE",
	"0036": "WIDE SURROUND MUSIC",
	"0025": "DTS-ES Neo",
	"0026": "DTS-ES matrix",
	"0027": "DTS-ES discrete",
	"0030": "DTS-ES 8ch discrete",
	"0043": "Neo:X CINEMA ",
	"0044": "Neo:X MUSIC",
	"0045": "Neo:X GAME",
	"0050": "Dolby Surround",
	"0100": "ADVANCED SURROUND",
	"0101": "ACTION",
	"0103": "DRAMA",
	"0118": "ADVANCED GAME",
	"0117": "SPORTS",
	"0107": "CLASSICAL",
	"0110": "ROCK/POP",
	"0112": "EXTENDED STEREO",
	"0003": "Front Stage Surround Advance",
	"0200": "ECO MODE",
	"0212": "ECO MODE 1",
	"0213": "ECO MODE 2",
	"0153": "RETRIEVER AIR",
	"0113": "PHONES SURROUND",
	"0005": "AUTO SURR/STREAM DIRECT",
	"0006": "AUTO SURROUND",
	"0151": "Auto Level Control",
	"0007": "DIRECT",
	"0008": "PURE DIRECT",
	"0152": "OPTIMUM SURROUND"
}


DEFAULT_SOURCES = [SOURCE_ID_BD, SOURCE_ID_DVD, SOURCE_ID_SAT,
    SOURCE_ID_HDMI1, SOURCE_ID_HDMI2, SOURCE_ID_HDMI3, SOURCE_ID_HDMI4,
    SOURCE_ID_HDMI5, SOURCE_ID_HDMI6, SOURCE_ID_INTERNET, SOURCE_ID_MEDIA_SERVER,
    SOURCE_ID_FAVORITES, SOURCE_ID_IPOD, SOURCE_ID_TV, SOURCE_ID_CD,
    SOURCE_ID_TUNER,SOURCE_ID_BT_AUDIO]

_LOGGER = logging.getLogger(__name__)

MAX_VOLUME = 185
MAX_ZONE_VOLUME = 81

DEFAULT_NAME = 'Pioneer AVR'
DEFAULT_PORT = 8102   # Most Pioneer AVRs now use 8102

CONF_SERIAL_BRIDGE      = 'serial_bridge'
CONF_DISABLED_SOURCES   = 'disabled_sources'
CONF_RADIO_STATIONS     = 'radio_stations'
CONF_LAST_RADIO_STATION = 'last_radio_station'

DATA_PIONEER = 'asyncpioneer'
ATTR_SPEAKER = 'speaker'
ATTR_SPEAKER_CONFIG = 'speaker_config'
SERVICE_SELECT_SPEAKER = 'pioneer_select_speaker'
SERVICE_SELECT_SPEAKER_CONFIG = 'pioneer_select_speaker_config'
ATTR_STATION = 'station'
SERVICE_SELECT_RADIO_STATION = 'pioneer_select_radio_station'
ATTR_DIM_DISPLAY = 'dim_display'
SERVICE_DIM_DISPLAY = 'pioneer_dim_display'
ATTR_HDMI_OUT = 'hdmi_out'
SERVICE_SELECT_HDMI_OUT = 'pioneer_select_hdmi_out'
SERVICE_SELECT_SOUND_MODE = 'select_sound_mode'

SUPPORT_PIONEER = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
                  SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
                  SUPPORT_SELECT_SOURCE | SUPPORT_PLAY | \
                  SUPPORT_PLAY_MEDIA | \
                  SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK

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
})

ACCEPTED_SPEAKER_VALUES = ['A', 'B', 'A+B']
pioneer_speaker_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SPEAKER): vol.In(ACCEPTED_SPEAKER_VALUES)
})

ACCEPTED_HDMI_OUT_VALUES = ['1+2 ON', '1 ON', '2 ON', '1/2 OFF']
pioneer_hdmi_out_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_HDMI_OUT): vol.In(ACCEPTED_HDMI_OUT_VALUES)
})

pioneer_select_sound_mode_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SOUND_MODE): cv.string
})

ACCEPTED_SPEAKER_CONFIG_VALUES = ['Height', 'Wide', 'SPK B', 'Bi Amp', 'Zone 2', 'HDZone']
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

ATTR_CURRENT_RADIO_STATION = 'current_radio_station'
ATTR_CURRENT_SPEAKER = 'current_speaker'
ATTR_CURRENT_SPEAKER_CONFIG = 'current_speaker_config'
ATTR_CURRENT_HDMI_OUT = 'current_hdmi_out'
ATTR_CURRENT_SOUND_MODE = 'current_sound_mode'

ATTR_TO_PROPERTY = [
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ALBUM_ARTIST,
    ATTR_MEDIA_TRACK,
    ATTR_MEDIA_SERIES_TITLE,
    ATTR_MEDIA_SEASON,
    ATTR_MEDIA_EPISODE,
    ATTR_MEDIA_CHANNEL,
    ATTR_MEDIA_PLAYLIST,
    ATTR_APP_ID,
    ATTR_APP_NAME,
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_SOUND_MODE,
    ATTR_SOUND_MODE_LIST,
    ATTR_MEDIA_SHUFFLE,
    ATTR_CURRENT_RADIO_STATION,
    ATTR_CURRENT_SPEAKER,
    ATTR_CURRENT_HDMI_OUT,
    ATTR_CURRENT_SOUND_MODE,
]


async def async_setup_platform(hass, config, async_add_entities, \
                               discovery_info=None):
    _LOGGER.debug("setup starting")
    devices = []

#    if hass.data.get(DATA_PIONEER) is None:
#        hass.data[DATA_PIONEER] = {}

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

    pioneer = PioneerDevice(
        hass,
        config.get(CONF_NAME),
        config.get(CONF_HOST),
        config.get(CONF_PORT),
        config.get(CONF_SERIAL_BRIDGE),
        config.get(CONF_DISABLED_SOURCES),
        config.get(CONF_LAST_RADIO_STATION),
        config.get(CONF_RADIO_STATIONS),
        "Main",
        hasZones
        )

    hass.loop.create_task(pioneer.readdata())

    hass.data[DATA_PIONEER].append(pioneer)
    devices.append(pioneer)

    if hasZones:
        for zone in add_zones.keys():
            _LOGGER.debug(f"adding new zone '{zone}'")
            pioneer_z = PioneerDevice(
                hass,
                config.get(CONF_NAME) + "_" + zone,
                config.get(CONF_HOST),
                config.get(CONF_PORT),
                config.get(CONF_SERIAL_BRIDGE),
                config.get(CONF_DISABLED_SOURCES),
                config.get(CONF_LAST_RADIO_STATION),
                config.get(CONF_RADIO_STATIONS),
                zone,
                hasZones
                )
            hass.loop.create_task(pioneer_z.readdata())
            hass.data[DATA_PIONEER].append(pioneer_z)
            devices.append(pioneer_z)

    _LOGGER.debug("adding pio devices")
    async_add_entities(devices, update_before_add=False)



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


class PioneerDevice(MediaPlayerEntity):

    def __init__(self, hass, name, ip, port, serial_bridge,\
                 disabled_sources, last_radio_station, radio_stations, zone, hasZones):
        _LOGGER.debug("Init")
        self.port = port
        self.ip = ip
        self.serial_bridge = serial_bridge
        self.hasConnection = False
        self.newDisplay = True
        self.hasComplete = False
        self.hasNames = False
        self._name = name
        self.data = []
        self.reader = None
        self.writer = None
        self._display = ""
        self.__display = ""
        self._title = ""
        self._artist = ""
        self._album = ""
        self._genre = ""
        self._bitrate = ""
        self._format = ""
        self._time = ""
        self._media_state = ""
        self._media_source = ""
        self._volume = None
        self._selected_source_name = None
        self._selected_source_id = None
        self._muted = False
        self._power = False
        self._zone2power = False
        self._source_name_to_number = {}
        self._source_number_to_name = {}
        self._disabled_source_list = {}
        self._current_radio_station = ""
        self._current_radio_frequency = ""
        self._last_radio_station = last_radio_station
        self._current_speaker = ""
        self._current_hdmi_out = ""
        self._stop_listen = False
        self._current_sound_mode = ""
        if disabled_sources:
            self._disabled_source_list = disabled_sources
        self._radio_stations = {}
        self._radio_stations_reversed = {}
        self._async_added = False
        self._hasZones = hasZones
        self._zone = zone
        self._zone_index = CONF_VALID_ZONES.index(zone)
        if radio_stations:
            self._radio_stations = radio_stations
            self._radio_stations_reversed = \
                {value: key for key, value in radio_stations.items()}

        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self.stop_pioneer)


    def stop_pioneer(self, event):
        _LOGGER.info("Shutting down Pioneer")
        self._stop_listen = True


    async def async_added_to_hass(self):
        _LOGGER.debug(f"{self._zone} Async async_added_to_hass")
        self._async_added = True


    async def getInputNames(self):
        _LOGGER.debug(f"{self._zone} Get Names")
        self.telnet_command("?RGD")
        hasNames = True
        for source in DEFAULT_SOURCES:
            if self._zone == "Zone2":
                if source not in VALID_ZONE2_SOURCES:
                    continue
            elif self._zone == "HDZone":
                if source not in VALID_HDZONE_SOURCES:
                    continue

            if source not in self._source_number_to_name:
                self.telnet_command("?RGB" + source)
                sleep(0.15)
                hasNames = False
        self.hasNames = hasNames


    async def readdata(self):
        _LOGGER.debug("Readdata")

        while not self._stop_listen:
            if not self.hasConnection:
                try:
                    self.reader, self.writer = \
                        await asyncio.open_connection(self.ip, self.port)
                    self.hasConnection = True
                    _LOGGER.info(f"{self._zone} Connected to %s:%d", self.ip, self.port)
                except:
                    _LOGGER.error(f"{self._zone} No connection to %s:%d, retry in 30s", \
                        self.ip, self.port)
                    await asyncio.sleep(30)
                    continue

            try:
                data = await self.reader.readuntil(b'\n')
            except:
                self.hasConnection = False
                _LOGGER.error("Lost connection!")
                continue

            if data.decode().strip() is None:
                await asyncio.sleep(1)
                _LOGGER.debug("none read")
                continue
            self.parseData(data.decode())

        _LOGGER.debug("Finished Readdata")
        return True

    def clearDisplay(self):
        self._artist = ""
        self._album = ""
        self._title = ""
        self.hasComplete = False
        self._display = ""
        self.__display = ""


    def updateRadioDisplay(self):
        if self._current_radio_station > "":
            self._artist = self._current_radio_station
        if self._current_radio_frequency > "":
            self._artist += " " + self._current_radio_frequency
        if self.current_radio_station in self._radio_stations_reversed.keys():
            self._artist += " (" + \
                self._radio_stations_reversed.get(self.current_radio_station) \
                + ")"


    def parseData(self, data):
        msg = ""

        # Fluorescent display content
        if data[:2]=="FL":
            rest = data[2:]
            while len(rest)>=2:
                a = rest[:2]
                if a>"0A":
                    n = int("0x"+a, 16)
                    msg +=chr(n)
                rest = rest[2:]

            if not msg[:5] == "M.VOL":
                if not msg.strip():
                    self.newDisplay = True
                    self._display = self.__display
                    self.hasComplete = True
                else:
                    if self.newDisplay:
                        self.newDisplay = False
                        self.__display = msg
                    else:
                        n = len(msg)-1
                        x = 1
                        pos = -1
                        while n>1:
                            pos = self.__display.find(msg[:n])
                            if pos>-1:
                                break
                            n-=1
                            x+=1

                        if pos>-1:
                            self.__display += msg[-x:]

                if not self.hasComplete:
                    self._display = self.__display
                _LOGGER.debug("Display: "+self._display)

            else:
                msg = data

        # Selected input source
        elif (data[:2] == "FN" and self._zone == "Main") \
          or (data[:3] == "Z2F" and self._zone == "Zone2") \
          or (data[:3] == "ZEA" and self._zone == "HDZone"):
            if self._zone == "Main":
                source_number = data[2:4]
            else: 
                source_number = data[3:5]

            if source_number:
                self._selected_source_id = source_number
                self._selected_source_name = \
                    self._source_number_to_name.get(source_number)
                if self._selected_source_id != SOURCE_ID_MEDIA_SERVER \
                     and self._selected_source_id != SOURCE_ID_INTERNET \
                     and self._selected_source_id != SOURCE_ID_FAVORITES \
                     and self._selected_source_id != SOURCE_ID_TUNER:
                    self._artist = ""
                    self._album = ""
                    if self._selected_source_name:
                        self._title = self._selected_source_name
                    else:
                        self._title = ""

                if self._selected_source_name:
                    _LOGGER.debug(f"Current {self._zone} input source: " \
                        + self._selected_source_name + " (" \
                        + source_number + ")")
            else:
                self._selected_source_name = None
            self.hasComplete = False

        # Radio tuner preset number
        elif data[:2] == "PR":
            self._current_radio_station = data[2:5]
            self._artist = self._current_radio_station
            self.updateRadioDisplay()
            _LOGGER.debug("Current radio station: " + \
                self._current_radio_station)

        # Radio tuner frequency
        elif data[:2] == "FR":
            if data[2] == "A":
                self._current_radio_frequency = "AM " + \
                    str(int(data[3:8])) + "kHz"
            else:
                self._current_radio_frequency = "FM " + \
                    str(int(data[3:6])) + "." + data[6:8] + "MHz"

            self._artist = self._current_radio_frequency
            self.updateRadioDisplay()
            _LOGGER.debug("Current radio freq: "+self._current_radio_frequency)


        # Model name
        elif data[:3] == "RGD":
            m = re.search('<([a-zA-Z0-9_\-\/]{5,})\>', data[3:-2])
            name = m.group(1)
            if name and name>"":
                self._name = "Pioneer " + name
            if self._hasZones:
                self._name += (" " + self._zone)

            _LOGGER.debug("Name: " + name)

        # Input source name
        elif data[:3] == "RGB":
            source_name = data[6:-2].strip()
            source_number = data[3:5]
            self._source_name_to_number[source_name] = source_number
            self._source_number_to_name[source_number] = source_name
            _LOGGER.debug("Input " + source_number + " = '" + source_name + "'")

        # Power state
        elif (data[:3] == "PWR" and self._zone == "Main") or (data[:3] == "APR" and self._zone == "Zone2") \
          or (data[:3] == "ZEP" and self._zone == "HDZone"):
            if data[3] == "1":
                self._power = False
            else:
                self._power = True

        # Zone power state
        elif data[:3] == "APR":
            if data[3] == "1":
                self._zone2power = False
            else:
                self._zone2power = True

        # Is muted
        elif data[:3] == "MUT" and self._zone == "Main":
            if data[3] == "1":
                self._muted = False
            else:
                self._muted = True
        elif (data[:5] == "Z2MUT" and self._zone == "Zone2") or (data[:5] == "HZMUT" and self._zone == "HDZone"):
            if data[5] == "1":
                self._muted = False
            else:
                self._muted = True

        # Playing state
        elif data[:3] == "GCH":
            mode = data[3:5]
            if mode == "02":
                self._media_state = "Playing"
            elif mode == "03":
                self._media_state = "Paused"
            elif mode == "06":
                self._media_state = "Stopped"
            elif mode == "07":
                self._media_state = "Waiting"
            elif mode == "01":
                self._media_state = ""
            else:
                self._media_state = "Unknown ("+data[3:5]+")"

        # Metadata
        elif data[:3] == "GEH":
            type = data[6:8]
            if type == "00":      # No data yet
                pass
            elif type == "20":      # Track title
                self._title = data[9:-3]
                self.newDisplay = True
                _LOGGER.debug("Title: " + self._title)
            elif type == "21":    # Artist
                self._artist = data[9:-3]
                _LOGGER.debug("Artist: " + self._artist)
            elif type == "22":  # Album
                self._album = data[9:-3]
                _LOGGER.debug("Album: " + self._album)
            elif type == "23":  # Time ("7:12")
                self._time = data[9:-3]
                _LOGGER.debug("Time: " + self._time)
            elif type == "24":    # Genre ("Ambient")
                self._genre = data[9:-3]
                _LOGGER.debug("Genre: " + self._genre)
            elif type == "26":    # Format ("mp3")
                self._format = data[9:-3]
                _LOGGER.debug("Format: " + self._format)
            elif type == "29":    # Bitrate ("128kbps")
                self._bitrate = data[9:-3]
                _LOGGER.debug("Bitrate: " + self._bitrate)

        # Volume level
        elif data[:3] == "VOL" and self._zone == "Main":
            self._volume = int(data[3:6]) / MAX_VOLUME
            _LOGGER.debug("Volume: " + str(round(self._volume*100))+"%")
        elif (data[:2] == "ZV" and self._zone == "Zone2"):
            self._volume = int(data[2:4]) / MAX_ZONE_VOLUME
            _LOGGER.debug("Volume: " + str(round(self._volume*100))+"%")
        elif (data[:3] == "HZV" and self._zone == "HDZone"):
            self._volume = int(data[3:5]) / MAX_ZONE_VOLUME
            _LOGGER.debug("Volume: " + str(round(self._volume*100))+"%")

        # Current speaker
        elif data[:3] == "SPK":
            self._current_speaker = int(data[3])
            _LOGGER.debug("Speaker: " + \
                ACCEPTED_SPEAKER_VALUES[self._current_speaker-1])

        elif data[:2] == "HO":
            self._current_hdmi_out = int(data[2])
            _LOGGER.debug("HDMI out: " + \
                ACCEPTED_HDMI_OUT_VALUES[self._current_hdmi_out])

        # Sound mode
        elif data[:2] == "SR":                
            self._current_sound_mode = data[2:6]
            _LOGGER.debug("Sound mode: " + \
                LISTENING_MODES[self._current_sound_mode])            

        else:
            print (data)

        if self._async_added:
            self.async_schedule_update_ha_state()

        return msg


    def telnet_command(self, command):
        _LOGGER.debug(f"{self._zone} Command: " + command)

        if self.hasConnection:
            if not self.writer:
                _LOGGER.error("No writer available")
                self.hasConnection = False
                return

            try:
                 self.writer.write(command.encode("ASCII") + b"\r")
                 if self.serial_bridge:
                    sleep(0.1)
            except (ConnectionRefusedError, OSError):
                _LOGGER.error("Pioneer %s refused connection!", self._name)
                self.hasConnection = False
                return
            except:
                _LOGGER.error("Pioneer %s lost connection!", self._name)
                self.hasConnection = False
        return

    async def async_update(self):
        """Get the latest details from the device."""
        _LOGGER.debug(f"{self._zone} Update")
        if not self.hasNames:
            await asyncio.sleep(1)
            await self.getInputNames()

        # Power state?
        commands = ["?P", "?AP", "?ZEP"]
        self.telnet_command(commands[self._zone_index])  

        if self._power:
            # Volume?
            commands = ["?V", "?ZV", "?HZV"] 
            self.telnet_command(commands[self._zone_index])  

            # Muted?
            commands = ["?M", "?Z2M", "?HZM"] 
            self.telnet_command(commands[self._zone_index])  

            # Input source?
            commands = ["?F", "?ZS", "?ZEA"] 
            self.telnet_command(commands[self._zone_index])  

            if self._zone == "Main":
                # Speaker?
                self.telnet_command("?SPK") 

            if self._selected_source_id == SOURCE_ID_TUNER:
                self.telnet_command("?PR")  # Tuner preset?
                self.telnet_command("?FR")  # Tuner frequency?
            else:
                self.telnet_command("?HO")  # HDMI out?

            self.telnet_command("?S")       # Sound mode?

        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        if self._power:
            return STATE_ON
        return STATE_OFF

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_PIONEER

    @property
    def source(self):
        """Return the current input source."""
        return self._selected_source_name

    @property
    def source_list(self):
        """List of available input sources."""
        if len(self._disabled_source_list) and len(self._source_name_to_number):
            enabled_sources = {}
            for name, number in self._source_name_to_number.items():
                if self._zone == "Zone2" and number not in VALID_ZONE2_SOURCES:
                    continue
                if self._zone == "HDZone" and number not in VALID_HDZONE_SOURCES:
                    continue
                if name not in self._disabled_source_list:
                    enabled_sources[name] = number
            return list(enabled_sources.keys())

        return list(self._source_name_to_number.keys())

    @property
    def media_title(self):
        """Title of current playing media."""
        if self._title>"":
            return self._title
        return self._display

    @property
    def media_artist(self):
        """Artist of current playing media."""
        return self._artist

    @property
    def media_album_name(self):
        """Album of current playing media."""
        return self._album

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def current_radio_station(self):
        """Return the current radio_station number."""
        return self._current_radio_station

    @property
    def current_speaker(self):
        """Return the current speaker."""
        if self._current_speaker:
            return ACCEPTED_SPEAKER_VALUES[self._current_speaker-1]
        return ""

    @property
    def current_hdmi_out(self):
        """Return the current HDMI out."""
        if self._current_hdmi_out:
            return ACCEPTED_HDMI_OUT_VALUES[self._current_hdmi_out]
        return ""

    @property
    def current_sound_mode(self):
        """Return the current HDMI out."""
        if self._current_sound_mode:
            return LISTENING_MODES[self._current_sound_mode]
        return ""        


    def media_play(self):
        """Start or resume playback on current source."""
        command = ""
        if self._selected_source_id == SOURCE_ID_TUNER:
            pass
        elif self._selected_source_id == SOURCE_ID_IPOD:
            command = "00IP"
        elif self._selected_source_id == SOURCE_ID_BT_AUDIO:
            command = "10BT"
        elif self._selected_source_id == SOURCE_ID_MEDIA_SERVER \
          or self._selected_source_id == SOURCE_ID_INTERNET \
          or self._selected_source_id == SOURCE_ID_FAVORITES:
            command = "10NW"

        if command>"":
            self.telnet_command(command)
            self.clearDisplay()
        else:
            _LOGGER.error("No play command for source %s",self._selected_source)

    def media_pause(self):
        """Pause playback on current source."""
        command = ""
        if self._selected_source_id == SOURCE_ID_TUNER:
            pass
        elif self._selected_source_id == SOURCE_ID_IPOD:
            command = "01IP"
        elif self._selected_source_id == SOURCE_ID_BT_AUDIO:
            command = "11BT"
        elif self._selected_source_id == SOURCE_ID_MEDIA_SERVER \
          or self._selected_source_id == SOURCE_ID_INTERNET \
          or self._selected_source_id == SOURCE_ID_FAVORITES:
            command = "11NW"

        if command>"":
            self.telnet_command(command)
        else:
            _LOGGER.error("No pause command for source %s", \
                self._selected_source)

    def media_previous_track(self):
        """Skip to previous track on current source."""
        command = ""
        if self._selected_source_id == SOURCE_ID_TUNER:
            if self._current_radio_station=="A01" and self._last_radio_station:
                command = self._last_radio_station + "PR"
            else:
                command = "TPD"
        elif self._selected_source_id == SOURCE_ID_IPOD:
            command = "03IP"
        elif self._selected_source_id == SOURCE_ID_BT_AUDIO:
            command = "13BT"
        elif self._selected_source_id == SOURCE_ID_MEDIA_SERVER \
          or self._selected_source_id == SOURCE_ID_INTERNET \
          or self._selected_source_id == SOURCE_ID_FAVORITES:
            command = "12NW"

        if command>"":
            self.telnet_command(command)
            self.clearDisplay()
        else:
            _LOGGER.error("No 'previous track' command for source %s", \
                self._selected_source)

    def media_next_track(self):
        """Skip to next track on current source."""
        command = ""
        if self._selected_source_id == SOURCE_ID_TUNER:
            if self._current_radio_station \
               and self._current_radio_station == self._last_radio_station:
                command = "A01PR"
            else:
                command = "TPI"
        elif self._selected_source_id == SOURCE_ID_IPOD:
            command = "04IP"
        elif self._selected_source_id == SOURCE_ID_BT_AUDIO:
            command = "14BT"
        elif self._selected_source_id == SOURCE_ID_MEDIA_SERVER \
          or self._selected_source_id == SOURCE_ID_INTERNET \
          or self._selected_source_id == SOURCE_ID_FAVORITES:
            command = "13NW"

        if command>"":
            self.telnet_command(command)
            self.clearDisplay()
        else:
            _LOGGER.error("No 'next track' command for source %s", \
                self._selected_source_name)

    def turn_off(self):
        """Turn off media player."""
        _LOGGER.debug(f"{self._zone} Turn off ")
        self.clearDisplay()
        commands = ["PF", "APF", "ZEF"]
        self.telnet_command(commands[self._zone_index])

    def volume_up(self):
        """Volume up media player."""
        _LOGGER.debug("Volume up ")
        commands = ["VU", "ZU", "HZU"]
        self.telnet_command(commands[self._zone_index])

    def volume_down(self):
        """Volume down media player."""
        _LOGGER.debug("Volume down ")
        commands = ["VD", "ZD", "HZD"]
        self.telnet_command(commands[self._zone_index])

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        # 60dB max
        if self._zone == "Main":
            _LOGGER.debug("Set volume to "+str(volume) \
                +", so to "+str(round(volume * MAX_VOLUME)).zfill(3)+"VL")
            self.telnet_command(str(round(volume * MAX_VOLUME)).zfill(3) + "VL")
        elif self._zone == "Zone2":
            _LOGGER.debug("Set Zone2 volume to "+str(volume) \
                +", so to ZV"+str(round(volume * MAX_ZONE_VOLUME)).zfill(2))
            self.telnet_command(str(round(volume * MAX_ZONE_VOLUME)).zfill(2) + "ZV")
        elif self._zone == "HDZone":
            _LOGGER.debug("Set HDZone volume to "+str(volume) \
                +", so to "+str(round(volume * MAX_ZONE_VOLUME)).zfill(2)+"HZV")
            self.telnet_command(str(round(volume * MAX_ZONE_VOLUME)).zfill(2) + "HZV")

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        if self._zone == "Main":
            self.telnet_command("MO" if mute else "MF")
        elif self._zone == "Zone2":
            self.telnet_command("Z2MO" if mute else "Z2MF")
        elif self._zone == "HDZone":
            self.telnet_command("HZMO" if mute else "HZMF")

    def turn_on(self):
        """Turn the media player on."""
        _LOGGER.debug(f"{self._zone} Turn on ")
        self.clearDisplay()
        commands = ["PO", "APO", "ZEO"]
        self.telnet_command(commands[self._zone_index])

    def select_source(self, source):
        """Select input source."""
        if source in self._source_name_to_number:
            commands = ["FN", "ZS", "ZEA"]
            self.telnet_command(self._source_name_to_number.get(source) + commands[self._zone_index])
            self.clearDisplay()
        else:
            _LOGGER.error("Unknown input '%s'", source)

    def select_speaker(self, speaker):
        """Select output speaker."""
        if speaker in ACCEPTED_SPEAKER_VALUES:
            index = ACCEPTED_SPEAKER_VALUES.index(speaker)
            self.telnet_command(str(index+1)+"SPK")
            
    def select_speaker_config(self, speaker_config):
        """Select speaker config mode."""
        _LOGGER.debug(f"Speaker config '{speaker_config}'")
        if speaker_config in ACCEPTED_SPEAKER_CONFIG_VALUES:
            index = ACCEPTED_SPEAKER_CONFIG_VALUES.index(speaker_config)
            self.telnet_command("0"+str(index)+"SSF")

    def select_radio_station(self, station):
        """Set radio tuner to the frequency of a named station in config."""
        if not len(self._radio_stations) \
            or not station in self._radio_stations.keys():
            _LOGGER.error("Unknown radio station '%s'", station)
        else:
            num = self._radio_stations.get(station)
            if num > "":
                self.telnet_command(num + "PR")
                self.clearDisplay()
                _LOGGER.debug("Set radio preset to '%s' for station '%s'", \
                    num, station)

    def select_hdmi_out(self, hdmi_out):
        """Select hdmi output."""
        _LOGGER.debug("HDMI command received '%s'", hdmi_out)
        if hdmi_out in ACCEPTED_HDMI_OUT_VALUES:
            index = ACCEPTED_HDMI_OUT_VALUES.index(hdmi_out)
            _LOGGER.debug("HDMI command will be '%d'", index)
            self.telnet_command(str(index)+"HO")

    def select_sound_mode(self, sound_mode):
        """Select sound mode"""
        _LOGGER.debug("Sound mode command received '%s'", sound_mode)
        foundMode = False
        for code, name in LISTENING_MODES.items():
            if name == sound_mode:
                foundMode = True
                _LOGGER.debug("Sound mode command will be '%s'", code)
                self.telnet_command(code+"SR")
        if not foundMode:        
            _LOGGER.debug("Cannot find code for sound mode '%s'", sound_mode)

    def dim_display(self, dim_display):
        """Dims the display"""
        self.telnet_command(str(dim_display)+"SAA")

    @property
    def state_attributes(self):
        """Return the state attributes."""
        if self.state == STATE_OFF:
            return None

        state_attr = {
            attr: getattr(self, attr) for attr
            in ATTR_TO_PROPERTY if getattr(self, attr) is not None
        }

        return state_attr
