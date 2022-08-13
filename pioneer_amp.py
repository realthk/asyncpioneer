import asyncio
import async_timeout
import logging
import re
from time import sleep

from .const import (
    TIMEOUT_SECS, CONNECT_RETRY_SECS,
    MAX_VOLUME, MAX_ZONE_VOLUME, 
    SOURCE_ID_MEDIA_SERVER, SOURCE_ID_INTERNET, SOURCE_ID_FAVORITES, SOURCE_ID_TUNER,
    ACCEPTED_SPEAKER_VALUES, ACCEPTED_HDMI_OUT_VALUES, LISTENING_MODES,
    DEFAULT_SOURCES, VALID_ZONE2_SOURCES, VALID_HDZONE_SOURCES
)

_LOGGER = logging.getLogger(__name__)

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP
)

class PioneerAmp():
    def __init__(self, hass, ip, port, serial_bridge,\
                 disabled_sources, last_radio_station, radio_stations, hasZones, inputs):    
        _LOGGER.debug("Init")
        self.port = port
        self.ip = ip
        self.serial_bridge = serial_bridge
        self.hasConnection = False
        self.newDisplay = True
        self.hasNames = False
        self.hasDeviceName = False
        self.data = []
        self.reader = None
        self.writer = None
        self._name = ""
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
        self._device_main   = None
        self._device_zone2  = None
        self._device_hdzone = None
        if disabled_sources:
            self._disabled_source_list = disabled_sources
        self._radio_stations = {}
        self._radio_stations_reversed = {}
        self._hasZones = hasZones
        if inputs:
            self.hasNames = True
            self._source_number_to_name = inputs
            self._source_name_to_number = {v: k for k, v in inputs.items()}
        if radio_stations:
            self._radio_stations = radio_stations
            self._radio_stations_reversed = \
                {value: key for key, value in radio_stations.items()}

        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self.stop_pioneer)


    def stop_pioneer(self, event):
        _LOGGER.info("Shutting down Pioneer")
        self._stop_listen = True


    async def readdata(self):
        _LOGGER.debug("Readdata started")

        while not self._stop_listen:
            if not self.hasConnection:
                try:
                    with async_timeout.timeout(TIMEOUT_SECS):
                        self.reader, self.writer = \
                            await asyncio.open_connection(self.ip, self.port)
                    self.hasConnection = True
                    _LOGGER.info(f"Connected to %s:%d", self.ip, self.port)
                except:
                    _LOGGER.info(f"No connection to %s:%d, retry in {CONNECT_RETRY_SECS}s", \
                        self.ip, self.port)
                    await asyncio.sleep(CONNECT_RETRY_SECS)
                    continue

            try:
                with async_timeout.timeout(TIMEOUT_SECS):
                    data = await self.reader.readuntil(b'\n')
            except:
                self.hasConnection = False
                _LOGGER.info("Lost connection!")
                continue

            if data.decode().strip() is None:
                await asyncio.sleep(1)
                _LOGGER.debug("none read")
                continue

            self.parseData(data.decode())

        _LOGGER.debug("Readdata finished")
        return True


    async def getInputNames(self):
        _LOGGER.debug("Get Names")
        hasNames = True
        for source in DEFAULT_SOURCES:
            if source not in self._source_number_to_name:
                _LOGGER.debug(f"Missing name for '{source}'")
                await self.telnet_command("?RGB" + source)
                await asyncio.sleep(0.15)
                hasNames = False
        self.hasNames = hasNames


    def clearDisplay(self):
        self._artist = ""
        self._album = ""
        self._title = ""
        self._display = ""
        self.__display = ""


    def parseData(self, data):
        msg = ""
        # Fluorescent display content
        if data[:2]=="FL":
            rest = data[2:]
            while len(rest)>=2:
                a = rest[:2]
                if a>"0A" and a!="91":
                    n = int("0x"+a, 16)
                    msg +=chr(n)
                rest = rest[2:]

            if not msg[:5] == "M.VOL":
                if not msg.strip():
                    self.newDisplay = True
                    self._display = self.__display
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
                        else:
                            self.__display = msg

                if self._display.find(self.__display)==-1 and self._display.strip()!=self.__display.strip():
                    self._display = self.__display
                    _LOGGER.debug("Display: "+self._display)
            else:
                msg = data

        # Selected input source
        elif data[:2]=="FN" or data[:3]=="Z2F" or data[:3]=="ZEA":
            if data[:2]=="FN":
                source_number = data[2:4]
                device = self._device_main
            else:
                source_number = data[3:5]
                if data[:3]=="Z2F":
                    device = self._device_zone2
                else:
                    device = self._device_hdzone

            device._title = ""
            if source_number:
                device._selected_source_id = source_number
                device._selected_source_name = \
                    self._source_number_to_name.get(source_number)
                if device._selected_source_id != SOURCE_ID_MEDIA_SERVER \
                     and device._selected_source_id != SOURCE_ID_INTERNET \
                     and device._selected_source_id != SOURCE_ID_FAVORITES \
                     and device._selected_source_id != SOURCE_ID_TUNER:
                    self._artist = ""
                    self._album = ""
                    if device._selected_source_name:
                        device._title = device._selected_source_name
                    else:
                        device._title = ""

                if device._selected_source_name:
                    _LOGGER.debug(f"Current {device._zone} input source: " \
                        + device._selected_source_name + " (" \
                        + source_number + ")")
            else:
                device._selected_source_name = None

        # Radio tuner preset number
        elif data[:2] == "PR":
            self._current_radio_station = data[2:5]
            _LOGGER.debug("Current radio station: " + self._current_radio_station)

        # Radio tuner frequency
        elif data[:2] == "FR":
            if data[2] == "A":
                self._current_radio_frequency = "AM " + str(int(data[3:8])) + "kHz"
            else:
                self._current_radio_frequency = "FM " + str(int(data[3:6])) + "." + data[6:8] + "MHz"
            _LOGGER.debug("Current radio freq: "+self._current_radio_frequency)

        # Model name
        elif data[:3] == "RGD":
            self.hasDeviceName = True
            m = re.search('<([a-zA-Z0-9_\-\/]{5,})\s*\>', data[3:-2])
            name = m.group(1) if m else None
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
        elif data[:3] == "PWR" and self._device_main:
            if data[3] == "1" or data[3] == "2":
                self._device_main._power = False
            else:
                self._device_main._power = True        
        # Zone2 power state
        elif data[:3] == "APR" and self._device_zone2:
            if data[3] == "1" or data[3] == "2":
                self._device_zone2._power = False
            else:
                self._device_zone2._power = True
        # HDZone power state
        elif data[:3] == "ZEP" and self._device_hdzone:
            if data[3] == "1" or data[3] == "2":
                self._device_hdzone._power = False
            else:
                self._device_hdzone._power = True

        # Is muted
        elif data[:3] == "MUT" and self._device_main:
            if data[3] == "1":
                self._device_main._muted = False                
            else:
                self._device_main._muted = True
        elif data[:5] == "Z2MUT" and self._device_zone2:
            if data[5] == "1":
                self._device_zone2._muted = False                
            else:
                self._device_zone2._muted = True
        elif data[:5] == "HZMUT" and self._device_hdzone:
            if data[5] == "1":
                self._device_hdzone._muted = False                
            else:
                self._device_hdzone._muted = True
            
        # Playing state
        elif re.match('GC[HP]', data[:3]):
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
        elif re.match('GE[HP]', data[:3]):
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
        elif data[:3] == "VOL" and self._device_main:
            self._device_main._volume = int(data[3:6]) / MAX_VOLUME
            _LOGGER.debug("Main volume: " + str(round(self._device_main._volume*100))+"%")
        elif data[:2] == "ZV" and self._device_zone2:
            self._device_zone2._volume = int(data[2:4]) / MAX_ZONE_VOLUME
            _LOGGER.debug("Zone2 volume: " + str(round(self._device_zone2._volume*100))+"%")
        elif data[:3] == "HZV" and self._device_hdzone:
            self._device_hdzone._volume = int(data[3:5]) / MAX_ZONE_VOLUME
            _LOGGER.debug("HDZone volume: " + str(round(self._device_hdzone._volume*100))+"%")

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
            _LOGGER.debug("Sound mode: " + LISTENING_MODES[self._current_sound_mode])

        else:
            print (data)

        if self._device_main and self._device_main._async_added:
            self._device_main.async_schedule_update_ha_state()

        if self._device_zone2 and self._device_zone2._async_added:
            self._device_zone2.async_schedule_update_ha_state()

        if self._device_hdzone and self._device_hdzone._async_added:
            self._device_hdzone.async_schedule_update_ha_state()

        return msg


    async def telnet_command(self, command):
        _LOGGER.debug(f"Command: " + command)

        if self.hasConnection:
            if not self.writer:
                _LOGGER.error("No writer available")
                self.hasConnection = False
                return
            try:
                self.writer.write(command.encode("ASCII") + b"\r")
                if self.serial_bridge:
                    await asyncio.sleep(0.1)
            except (ConnectionRefusedError, OSError):
                _LOGGER.error("Pioneer amp refused connection!")
                self.hasConnection = False
                return
            except:
                _LOGGER.error("Lost connection with Pioneer amp!")
                self.hasConnection = False
                self.clearDisplay()
        return


