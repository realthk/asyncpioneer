# Async Pioneer AV amp

My VSX-924 AV amp works with the original Home Assistant Pioneer driver for a few hours, a day or two at max only. After that it freezes, and only a power off/on cycle makes it useable again.
This is because that driver creates a new telnet connection to the amp for every update, it queries the required info, and then closes the connection. The telnet software in the amp firmware probably has memory leak, that might be the reason for this freeze after a few thousands of telnet connections.

No firmware updates available for this amp anymore, so I re-wrote the driver in an async workflow: it creates a single connection and listens to the replies from the amp in an endless loop.
The idea is probably right, because my amp hardly freezes now. As a bonus, it was also possible to capture the display-content of the amp.

I recommend the [Mini Media Player](https://github.com/kalkih/mini-media-player) from kalkih as a nice UI for the amp.


![Preview Image](https://user-images.githubusercontent.com/5654575/53702516-1f760700-3e08-11e9-900b-435edf7fbfa7.png)

## Install

1. Download and copy [media_player.py](https://github.com/realthk/asyncpioneer/blob/master/media_player.py) into `config/custom_components/asyncpioneer` directory.

2. Add a reference to this inside your `configuration.yaml`:

  ```yaml
media_player:
  - platform: asyncpioneer
    host: 192.168.8.121
    port: 8102
    last_radio_station: "D06"
    radio_stations:
       "Bartok"          : "B02"
       "Novi Sad"        : "B03"
       "Petofi"          : "B04"
       "Panda"           : "B05"
       "Szabadkai Rádió" : "C02"
       "Pannon Szabadka" : "C03"
       "Prvi Radio"      : "D05"
       "Hit FM Szabadka" : "D06"
    disabled_sources:
      - "HDMI 4"
      - "HDMI 5"
      - "HDMI 6/MHL"
      - "iPod/USB"
      - "THome"
  ```

## Options
**last_radio_station**:
If not set, "next track" button in radio tuner mode will simply send "next station" command to the amp, which is not convenient, if you only have a few stations stored in the amp's memory.
If this is set to eg. "B03", then sending a "next track" command when listening to "B03" will result in a "select A01 station" command. Likewise, a "previous track" on "A01" results in "select B03 station".

**radio_stations**:
You can name the stored stations here, because not every radio use RDS. Dictionary format.

**disabled_sources**:
A simple list to disable unwanted input sources, to make the source selector list shorter.

## Services
**pioneer_select_speaker**:
Select output speaker "A", "B" or "A+B"
Eg.
  ```yaml
  - service: media_player.pioneer_select_speaker
    data:
      entity_id: media_player.pioneer_avr
      speaker: "A+B"
  ```
  
**pioneer_select_radio_station**:
Select stored radio station by its name.
Eg.
  ```yaml
  - service: media_player.pioneer_select_radio_station
    data:
      entity_id: media_player.pioneer_avr
      station: "My favorite radio"
  ```
  
## State attributes
**current_radio_station**:
The currently selected radio station code, like "B07"

**current_speaker**:
The currently selected output speaker: "A", "B" or "A+B"

  