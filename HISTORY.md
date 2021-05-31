# History
# This is a special branch for INCEPTIO
---

## 2.2.5 / 2021-02-18 
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

