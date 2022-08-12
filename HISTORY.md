# History
# This is a special branch for INCEPTIO
---
## 2.5.5a / 2022-08-12
- [OpenRTK/RTK330LA] Resolve app crash while erasing the flash.
- [OpenRTK/RTK330LA] Improve firmware upgrade logic.

## 2.5.4a / 2022-06-08
- [OpenRTK/RTK330LA] Fix issues on ST9100 chip firmware upgrade.

## 2.5.2 / 2021-08-13
- [OpenRTK/RTK330L] Add RTCM log that parsed by NTRIP Client.

## 2.5.1 / 2021-08-11
- [OpenRTK/RTK330L] Fix issues.

## 2.5.0 / 2021-07-02
- [DMU] Support firmware upgrade.
- [OpenRTK/RTK330LA] Support ST9100 chip upgrade.
- [Framework] Fix NTRIP client disconnect issue.
- [Framework] Refactor upgrade worker.
- [Framework] Integrate rtk log parser.
- [Framework] Update startup parameters.

## 2.4.0 / 2021-05-07
- [DMU] Resolve firmware version from ID message.
- [DMU] Support record data in developers site.
- [DMU/IMU] Support GF, SF, RF, WF for uart command run tool in developers site.
- [OpenRTK/RTK330LA] Log device info when device is connected.

## 2.3.2 / 2021-04-12
- [DMU] Support INS330BI
- [RTK330LA] Fix the wrong GNSS port logging

## 2.3.1 / 2021-04-02
- [OpenIMU] Update openimu.json for OpenIMU300RI
- [OpenRTK] Update GGA parser
- [OpenRTK] Split log name of RTK330LA from OpenRTK
- [Framework] Optimize the device information match
- [Framework] Support force to bootloader

## 2.3.0 / 2021-02-28
- [OpenIMU] Support packet data statistics.
- [OpenRTK] Support RTK330L.
- [OpenRTK] Save predefined parameters when connected.
- [Framework] Adjust the json file location. Different product would have single application json file.
- [Framework] Support upgrade firmware through aceinna developers site.
- [Framework] Enhance the upgrade center.
- [Framework] Refactor WebServer, consider websocket server is a message tunnel.
- [Framework] Refactor bootstrap, to make it clear for later maintainer.

## 2.2.5 / 2021-05-31 
- [OpenRTK] Support RTK330LA firmware upgrade.
- [OpenRTK] Fix some issues.

## 2.2.4c / 2021-02-18 
- [OpenRTK] Update openrtk parse.
- [OpenRTK] Fix upgrade issue.

## 2.2.4b / 2021-02-07 
- [OpenRTK] Download sdk firmware throught user com port.
- [OpenRTK] Save all parameters in a json file.
- [OpenRTK] Update openrtk.json and openrtk parse for INCEPTIO.

## 2.2.4 / 2020-12-18
- [OpenRTK] Remove console print and add print.log to save these infomation.
- [OpenRTK] Update openrtk parse to make kml files.

## 2.2.3 / 2020-12-01
- [OpenRTK] Update Configuration read size.
- [Framework] Fix cannot parse 'sC', 'uB' command.

## 2.2.2 / 2020-11-26
- [OpenIMU] Add exception handler when log data, although file is closed.
- [OpenIMU] Add uC,uA,gA command response.
- [OpenRTK] Fix upgrade issue through web.

## 2.2.1 / 2020-11-17

- [OpenIMU] Fix the mag align command cannot correctly response.
- [Framework] Update the usage of asyncio.
- [Framework] Fix cannot connect the websocket server on some versions of windows.
- [Framework] Support to start executor as a cli tool with startup parameter `--cli`.
- [Framework] Fix data log will auto start after firmware upgrade without setting auto start.

## 2.2.0 / 2020-11-9

- [OpenRTK] Important update for INS App v23.00, can't suitable for v2.0.0 or v20.00.
- [OpenRTK] Modify user data packets.
- [OpenRTK] Log base rtcm data on debug port.
- [DMU] Add A1,A2 packet response for DUM device.
- [Framework] Add Unit test cases.

## 2.1.7 / 2020-08-26

- [OpenRTK] Print 'NMEA' and #INSPVA.
- [Framework] Improved the ping perform on devices.

## 2.1.6 / 2020-08-19

- [OpenRTK] Modify INS json: suitable for INS_APP v2.0.0.
- [Framework] Improve the output of console.

## 2.1.5 / 2020-08-11

- [Framework] Support download combined GNSS_RTK_SDK and INS_APP Firmware.
- [Framework] Display python driver version.
- [Framework] Remove upgrade file when upgrade firmware.

## 2.1.4 / 2020-07-23

- [OpenRTK] Add 'rD' command to restore OpenRTK330 default configuration.
	User can find 'RESTORE DEFAULTS' button in OpenRTK->SETTINGS.
- [OpenRTK] Add 'gB' command to get configuration according to range of parameterID.
- [OpenRTK] Support update GNSS_RTK_SDK in App Center.
- [Framework] Enhance the message parser from device.

