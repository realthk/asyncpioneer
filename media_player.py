import asyncio
import logging
import math
import re

import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MEDIA_PLAYER_SCHEMA,
    MediaPlayerDevice)

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
    EVENT_HOMEASSISTANT_STOP
)

import homeassistant.helpers.config_validation as cv
from time import sleep

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

DEFAULT_SOURCES = [SOURCE_ID_BD, SOURCE_ID_DVD, SOURCE_ID_SAT,
    SOURCE_ID_HDMI1, SOURCE_ID_HDMI2, SOURCE_ID_HDMI3, SOURCE_ID_HDMI4,
    SOURCE_ID_HDMI5, SOURCE_ID_HDMI6, SOURCE_ID_INTERNET, SOURCE_ID_MEDIA_SERVER,
    SOURCE_ID_FAVORITES, SOURCE_ID_IPOD, SOURCE_ID_TV, SOURCE_ID_CD,
    SOURCE_ID_TUNER,SOURCE_ID_BT_AUDIO]

_LOGGER = logging.getLogger(__name__)

MAX_VOLUME = 185
DEFAULT_NAME = 'Pioneer AVR'
DEFAULT_PORT = 8102   # Most Pioneer AVRs now use 8102

CONF_DISABLED_SOURCES   = 'disabled_sources'
CONF_RADIO_STATIONS     = 'radio_stations'
CONF_LAST_RADIO_STATION = 'last_radio_station'

DATA_PIONEER = 'pioneer'
ATTR_SPEAKER = 'speaker'
SERVICE_SELECT_SPEAKER = 'pioneer_select_speaker'
ATTR_STATION = 'station'
SERVICE_SELECT_RADIO_STATION = 'pioneer_select_radio_station'
ATTR_DIM_DISPLAY = 'dim_display'
SERVICE_DIM_DISPLAY = 'pioneer_dim_display'

SUPPORT_PIONEER = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
                  SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
                  SUPPORT_SELECT_SOURCE | SUPPORT_PLAY | \
                  SUPPORT_PLAY_MEDIA | \
                  SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_DISABLED_SOURCES): [cv.string],
    vol.Optional(CONF_LAST_RADIO_STATION): cv.string,
    vol.Optional(CONF_RADIO_STATIONS): {cv.string: cv.string},
})

ACCEPTED_SPEAKER_VALUES = ['A', 'B', 'A+B']
pioneer_speaker_schema = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SPEAKER): vol.In(ACCEPTED_SPEAKER_VALUES)
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
]



async def async_setup_platform(hass, config, async_add_entities, \
                               discovery_info=None):
    _LOGGER.debug("setup starting")
    pioneer = PioneerDevice(
        hass,
        config.get(CONF_NAME),
        config.get(CONF_HOST),
        config.get(CONF_PORT),
        config.get(CONF_DISABLED_SOURCES),
        config.get(CONF_LAST_RADIO_STATION),
        config.get(CONF_RADIO_STATIONS)
        )

#    asyncio.ensure_future(pioneer.readdata())
    hass.loop.create_task(pioneer.readdata())

    if DATA_PIONEER not in hass.data:
        hass.data[DATA_PIONEER] = []
    hass.data[DATA_PIONEER].append(pioneer)

    _LOGGER.debug("adding pio entity")
    async_add_entities([pioneer], update_before_add=False)



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

            if service.service == SERVICE_SELECT_RADIO_STATION:
                station = service.data.get(ATTR_STATION)
                device.select_radio_station(station)

            if service.service == SERVICE_DIM_DISPLAY:
                dim_display = service.data.get(ATTR_DIM_DISPLAY)
                device.dim_display(dim_display)

            device.async_schedule_update_ha_state(True)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_SPEAKER, async_service_handler,
        schema=pioneer_speaker_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_RADIO_STATION, async_service_handler,
        schema=pioneer_radio_station_schema)

    hass.services.async_register(
        DOMAIN, SERVICE_DIM_DISPLAY, async_service_handler,
        schema=pioneer_dim_display_schema)


class PioneerDevice(MediaPlayerDevice):

    def __init__(self, hass, name, ip, port, \
                 disabled_sources, last_radio_station, radio_stations):
        _LOGGER.debug("Init")
        self.port = port
        self.ip = ip
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
        self._stop_listen = False
        if disabled_sources:
            self._disabled_source_list = disabled_sources
        self._radio_stations = {}
        self._radio_stations_reversed = {}
        self._async_added = False
        if radio_stations:
            self._radio_stations = radio_stations
            self._radio_stations_reversed = \
                {value: key for key, value in radio_stations.items()}

        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self.stop_pioneer)


    def stop_pioneer(self, event):
        _LOGGER.info("Shutting down Pioneer")
        self._stop_listen = True


    async def async_added_to_hass(self):
        _LOGGER.debug("Async async_added_to_hass")
        self._async_added = True


    async def getInputNames(self):
        _LOGGER.debug("Get Names")
        self.telnet_command("?RGD")
        hasNames = True
        for source in DEFAULT_SOURCES:
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
                    _LOGGER.info("Connected to %s:%d", self.ip, self.port)
                except:
                    _LOGGER.error("No connection to %s:%d, retry in 30s", \
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
        elif data[:2] == "FN":
            source_number = data[2:4]

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
                    _LOGGER.debug("Current input source: " \
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

            _LOGGER.debug("Name: " + name)

        # Input source name
        elif data[:3] == "RGB":
            source_name = data[6:-2].strip()
            source_number = data[3:5]
            self._source_name_to_number[source_name] = source_number
            self._source_number_to_name[source_number] = source_name
            _LOGGER.debug("Input " + source_number + " = '" + source_name + "'")

        # Power state
        elif data[:3] == "PWR":
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
        elif data[:3] == "MUT":
            if data[3] == "1":
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
        elif data[:3] == "VOL":
            self._volume = int(data[3:6]) / MAX_VOLUME
            _LOGGER.debug("Volume: " + str(round(self._volume*100))+"%")

        # Current speaker
        elif data[:3] == "SPK":
            self._current_speaker = int(data[3])
            _LOGGER.debug("Speaker: " + \
                ACCEPTED_SPEAKER_VALUES[self._current_speaker-1])

        else:
            print (data)

        if self._async_added:
            self.async_schedule_update_ha_state()

        return msg


    def telnet_command(self, command):
        _LOGGER.debug("Command: " + command)

        if self.hasConnection:
            if not self.writer:
                _LOGGER.error("No writer available")
                self.hasConnection = False
                return

            try:
                 self.writer.write(command.encode("ASCII") + b"\r")
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
        _LOGGER.debug("Update")
        if not self.hasNames:
            await asyncio.sleep(1)
            await self.getInputNames()

        self.telnet_command("?P")  # Power state?

        if self._power:
            self.telnet_command("?V")  # Volume?
            self.telnet_command("?M")  # Muted?
            self.telnet_command("?F")  # Input source?
            self.telnet_command("?SPK")  # Input source?
            if self._selected_source_id == SOURCE_ID_TUNER:
                self.telnet_command("?PR")  # Tuner preset?
                self.telnet_command("?FR")  # Tuner frequency?
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
                self._selected_source)

    def turn_off(self):
        """Turn off media player."""
        _LOGGER.debug("Turn off ")
        self.clearDisplay()
        self.telnet_command("PF")

    def volume_up(self):
        """Volume up media player."""
        _LOGGER.debug("Volume up ")
        self.telnet_command("VU")

    def volume_down(self):
        """Volume down media player."""
        _LOGGER.debug("Volume down ")
        self.telnet_command("VD")

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        # 60dB max
        _LOGGER.debug("Set volume to "+str(volume) \
            +", so to "+str(round(volume * MAX_VOLUME)).zfill(3)+"VL")
        self.telnet_command(str(round(volume * MAX_VOLUME)).zfill(3) + "VL")

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self.telnet_command("MO" if mute else "MF")

    def turn_on(self):
        """Turn the media player on."""
        _LOGGER.debug("Turn on ")
        self.clearDisplay()
        self.telnet_command("PO")

    def select_source(self, source):
        """Select input source."""
        if source in self._source_name_to_number:
            self.telnet_command(self._source_name_to_number.get(source) + "FN")
            self.clearDisplay()
        else:
            _LOGGER.error("Unknown input '%s'", source)

    def select_speaker(self, speaker):
        """Select output speaker."""
        if speaker in ACCEPTED_SPEAKER_VALUES:
            index = ACCEPTED_SPEAKER_VALUES.index(speaker)
            self.telnet_command(str(index+1)+"SPK")

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
