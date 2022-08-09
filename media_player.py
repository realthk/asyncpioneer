import asyncio
import logging
import re
from .pioneer_amp import PioneerAmp
from .const import *

from homeassistant.components.media_player import MediaPlayerEntity

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
    ATTR_MEDIA_EPISODE,
    ATTR_MEDIA_PLAYLIST,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    ATTR_MEDIA_SEASON,
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
    STATE_OFF, STATE_ON,
)

import homeassistant.helpers.config_validation as cv
from time import sleep

_LOGGER = logging.getLogger(__name__)


SUPPORT_PIONEER = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
                  SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
                  SUPPORT_SELECT_SOURCE | SUPPORT_PLAY | \
                  SUPPORT_PLAY_MEDIA | \
                  SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK

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

class PioneerDevice(MediaPlayerEntity):
    def __init__(self, name, zone, amp: PioneerAmp):
        self._name = name
        self._amp = amp
        self._zone = zone
        self._zone_index = CONF_VALID_ZONES.index(zone)
        self._volume = None
        self._selected_source_name = None
        self._selected_source_id = None
        self._muted = False
        self._power = False
        self._title = ""
        self._async_added = False

    async def async_added_to_hass(self):
        _LOGGER.debug(f"{self._zone} Async async_added_to_hass")
        self._async_added = True

    async def async_update(self):
        """Get the latest details from the device."""
        if not self._amp.hasConnection:
            return False

        _LOGGER.debug(f"{self._zone} Update")

        if not self._amp.hasDeviceName:
            self._amp.telnet_command("?RGD")

        if not self._amp.hasNames and self._zone=="Main":
            await asyncio.sleep(1)
            await self._amp.getInputNames()

        # Power state?
        commands = ["?P", "?AP", "?ZEP"]
        self._amp.telnet_command(commands[self._zone_index])

        if self._power:
            # Volume?
            commands = ["?V", "?ZV", "?HZV"]
            self._amp.telnet_command(commands[self._zone_index])

            # Muted?
            commands = ["?M", "?Z2M", "?HZM"]
            self._amp.telnet_command(commands[self._zone_index])

            # Input source?
            commands = ["?F", "?ZS", "?ZEA"]
            self._amp.telnet_command(commands[self._zone_index])

            if self._zone == "Main":
                # Speaker?
                self._amp.telnet_command("?SPK")

            if self._selected_source_id == SOURCE_ID_TUNER:
                self._amp.telnet_command("?PR")  # Tuner preset?
                self._amp.telnet_command("?FR")  # Tuner frequency?
            else:
                self._amp.telnet_command("?HO")  # HDMI out?

            self._amp.telnet_command("?S")       # Sound mode?

        return True

    @property
    def name(self):
        """Return the name of the device."""
        if self._amp._name > "":            
            if self._amp._hasZones:
                return self._amp._name + (" " + self._zone)        
            return self._amp._name
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
        if self._amp._title>"":
            return self._amp._title
        return self._amp._display

    @property
    def media_artist(self):
        """Artist of current playing media."""
        return self._amp._artist

    @property
    def media_album_name(self):
        """Album of current playing media."""
        return self._amp._album

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def current_radio_station(self):
        """Return the current radio_station number."""
        return self._amp._current_radio_station

    @property
    def current_speaker(self):
        """Return the current speaker."""
        if self._current_speaker:
            return ACCEPTED_SPEAKER_VALUES[self._current_speaker-1]
        return ""

    @property
    def current_hdmi_out(self):
        """Return the current HDMI out."""
        if self._amp._current_hdmi_out:
            return ACCEPTED_HDMI_OUT_VALUES[self._amp._current_hdmi_out]
        return ""

    @property
    def current_sound_mode(self):
        """Return the current HDMI out."""
        if self._amp._current_sound_mode:
            return LISTENING_MODES[self._amp._current_sound_mode]
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
            self._amp.telnet_command(command)
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
            self._amp.telnet_command(command)
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
            self._amp.telnet_command(command)
            self._amp.clearDisplay()
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
            self._amp.telnet_command(command)
            self._amp.clearDisplay()
        else:
            _LOGGER.error("No 'next track' command for source %s", \
                self._selected_source_name)

    def turn_off(self):
        """Turn off media player."""
        _LOGGER.debug(f"{self._zone} Turn off ")
        self._amp.clearDisplay()
        commands = ["PF", "APF", "ZEF"]
        self._amp.telnet_command(commands[self._zone_index])

    def volume_up(self):
        """Volume up media player."""
        _LOGGER.debug("Volume up ")
        commands = ["VU", "ZU", "HZU"]
        self._amp.telnet_command(commands[self._zone_index])

    def volume_down(self):
        """Volume down media player."""
        _LOGGER.debug("Volume down ")
        commands = ["VD", "ZD", "HZD"]
        self._amp.telnet_command(commands[self._zone_index])

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        # 60dB max
        if self._zone == "Main":
            _LOGGER.debug("Set volume to "+str(volume) \
                +", so to "+str(round(volume * MAX_VOLUME)).zfill(3)+"VL")
            self._amp.telnet_command(str(round(volume * MAX_VOLUME)).zfill(3) + "VL")
        elif self._zone == "Zone2":
            _LOGGER.debug("Set Zone2 volume to "+str(volume) \
                +", so to ZV"+str(round(volume * MAX_ZONE_VOLUME)).zfill(2))
            self._amp.telnet_command(str(round(volume * MAX_ZONE_VOLUME)).zfill(2) + "ZV")
        elif self._zone == "HDZone":
            _LOGGER.debug("Set HDZone volume to "+str(volume) \
                +", so to "+str(round(volume * MAX_ZONE_VOLUME)).zfill(2)+"HZV")
            self._amp.telnet_command(str(round(volume * MAX_ZONE_VOLUME)).zfill(2) + "HZV")

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        if self._zone == "Main":
            self._amp.telnet_command("MO" if mute else "MF")
        elif self._zone == "Zone2":
            self._amp.telnet_command("Z2MO" if mute else "Z2MF")
        elif self._zone == "HDZone":
            self._amp.telnet_command("HZMO" if mute else "HZMF")

    def turn_on(self):
        """Turn the media player on."""
        _LOGGER.debug(f"{self._zone} Turn on ")
        self._amp.clearDisplay()
        commands = ["PO", "APO", "ZEO"]
        self._amp.telnet_command(commands[self._zone_index])

    def select_source(self, source):
        """Select input source."""
        if source in self._source_name_to_number:
            commands = ["FN", "ZS", "ZEA"]
            self._amp.telnet_command(self._source_name_to_number.get(source) + commands[self._zone_index])
            self.clearDisplay()
        else:
            _LOGGER.error("Unknown input '%s'", source)

    def select_speaker(self, speaker):
        """Select output speaker."""
        if speaker in ACCEPTED_SPEAKER_VALUES:
            index = ACCEPTED_SPEAKER_VALUES.index(speaker)
            self._amp.telnet_command(str(index+1)+"SPK")

    def select_speaker_config(self, speaker_config):
        """Select speaker config mode."""
        _LOGGER.debug(f"Speaker config '{speaker_config}'")
        if speaker_config in ACCEPTED_SPEAKER_CONFIG_VALUES:
            index = ACCEPTED_SPEAKER_CONFIG_VALUES.index(speaker_config)
            self._amp.telnet_command("0"+str(index)+"SSF")

    def select_radio_station(self, station):
        """Set radio tuner to the frequency of a named station in config."""
        if not len(self._radio_stations) \
            or not station in self._radio_stations.keys():
            _LOGGER.error("Unknown radio station '%s'", station)
        else:
            num = self._radio_stations.get(station)
            if num > "":
                self._amp.telnet_command(num + "PR")
                self._amp.clearDisplay()
                _LOGGER.debug("Set radio preset to '%s' for station '%s'", \
                    num, station)

    def select_hdmi_out(self, hdmi_out):
        """Select hdmi output."""
        _LOGGER.debug("HDMI command received '%s'", hdmi_out)
        if hdmi_out in ACCEPTED_HDMI_OUT_VALUES:
            index = ACCEPTED_HDMI_OUT_VALUES.index(hdmi_out)
            _LOGGER.debug("HDMI command will be '%d'", index)
            self._amp.telnet_command(str(index)+"HO")

    def select_sound_mode(self, sound_mode):
        """Select sound mode"""
        _LOGGER.debug("Sound mode command received '%s'", sound_mode)
        foundMode = False
        for code, name in LISTENING_MODES.items():
            if name == sound_mode:
                foundMode = True
                _LOGGER.debug("Sound mode command will be '%s'", code)
                self._amp.telnet_command(code+"SR")
        if not foundMode:
            _LOGGER.debug("Cannot find code for sound mode '%s'", sound_mode)

    def dim_display(self, dim_display):
        """Dims the display"""
        self._amp.telnet_command(str(dim_display)+"SAA")

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
