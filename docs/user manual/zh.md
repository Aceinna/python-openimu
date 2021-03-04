# 使用手册

## 目录
- [使用步骤](#使用步骤)
- [工作模式](#工作模式)
- [连接方式](#连接方式)

## 使用步骤

### 1. 运行driver
```bash
$ ./ans-devices
```

#### 运行参数
在启动driver工具的时候，可以设置一些启动参数值，

参数列表:

| 参数 | 类型 | 默认值 | 说明 |
| - | :-: | :-: | - |
| --cli | Boolean | False | 启动命令行模式 |
| -p, --port | Number | '8000' | 设置websocket server的监听端口 |
| --device-type | String | 'auto' | 指定连接设备类型，有效值是 `IMU`, `RTK`, `DMU` 之一 |
| -b, --baudrate | String | None | 指定串口波特率，有效值是 `38400`, `57600`, `115200`, `230400`, `460800` 之一 |
| -c, --com-port | String | 'auto' | 指定串口名称 |
| --console-log | Boolean | False | 输出日志到控制台的开关 |
| --debug | Boolean | False | 输出debug级别日志到控制台的开关 |
| --with-data-log | Boolean | False | 自动记录设备输出数据 (OpenIMU only) |
| -s, --set-user-para | Boolean | False | 使用用户设置参数的开关 (OpenRTK only) |
| -n, --ntrip-client | Boolean | False | 开启Ntrip Client的开关 (OpenRTK only) |
| -l, --protocol | String | 'uart' | 指定设备的连接方式。 有效值是 `uart`, `lan` 之一 |

### 2. 连接设备
将设备与电脑连接，等待一段时间，driver工具将会自动设备。也可以指定一些启动参数，可以更快地识别到设备。

### 3. 数据可视化
打开Aceinna开发者网站，不同的设备对应不同的可视化页面。
- OpenIMU https://developers.aceinna.com/devices/record-next
- OpenRTK https://developers.aceinna.com/devices/rtk

## 工作模式
### 默认模式
通常，driver以默认模式工作。它将建立一个websocket服务器，然后通过websocket协议交换消息。同时配合[Aceinna开发者网站](https://developers.aceinna.com“Aceinna开发者网站”），用户可以对设备进行数据监控、参数配置和固件管理。

### 命令行模式
你可以指定启动参数 `--cli` 以切换到命令行模式。命令行模式帮助您直接与设备交互。它还提供启动websocket服务器的命令，以便可以使用默认模式的全部功能。

命令行模式支持使用一些命令，下面是命令列表说明，

#### 帮助
显示帮助菜单。它将显示所有受支持命令的描述列表。
```bash
$ help
```

#### 获取设备信息
显示连接设备的信息。
```bash
$ connect
```

#### 获取参数 (仅OpenIMU)
检索指定参数的当前值。
```bash
$ get param_name
```

#### 设置参数 (仅OpenIMU)
更新指定参数的值。关闭设备电源后将恢复该值。
```bash
$ set param_name param_value
```

#### 保存配置
将配置保存到EEPROM中。该值将被永久保存。
```bash
$ save
```

#### 记录数据 (OpenIMU Only)
在路径 `/path` 中记录设备输出数据。OpenRTK不支持这个命令，因为OpenRTK设备在连接时会自动记录数据。
```bash
$ record
```

#### 更新固件
从指定路径升级固件。固件文件应与设备匹配。这是一个高风险的操作。
```bash
$ upgrade path/to/bin
```

#### 启动服务器
建立一个websocket服务器。
```bash
$ server_start
```

#### 关闭服务器
停止websocket服务器。如果websocket服务器正在运行，当你想使用其他命令时，必须先停止它。
```bash
$ stop
```

#### 退出
退出命令行模式
```bash
$ exit
```

## 连接方式
Aceinna设备可以通过UART或LAN与PC连接。支持的协议取决于设备类型。
| 设备类型 | 支持的协议 | 说明 |
| - | - | - |
| DMU | `uart` | |
| OpenIMU | `uart` | |
| OpenRTK | `uart`, `lan` | 启动时设置参数 `-l lan` 以支持网口方式连接设备 |
| RTK330L | `uart` |  |
