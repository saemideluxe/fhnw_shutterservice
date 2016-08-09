import datetime
import knx

_now = datetime.datetime.now
_cmd_timeout = datetime.timedelta(microseconds=999 * 1000)

_CMD_UP = [0]
_CMD_DOWN = [1]

# to move shutter long, set LSB of address to 0
def _knx_addr_long_move(addr):
    return addr[0:2] + (addr[2] & 254,)


# to move shutter short, set LSB of address to 1
def _knx_addr_short_move(addr):
    return addr[0:2] + (addr[2] | 1,)


def up(shutter_adr, time=None):
    knx.queue_command(_now(), _knx_addr_long_move(shutter_adr), _CMD_UP)
    if time:
        knx.queue_command(_now() + datetime.timedelta(seconds=time), _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    return "up ok", False


def down(shutter_adr, time=None):
    knx.queue_command(_now(), _knx_addr_long_move(shutter_adr), _CMD_DOWN)
    if time:
        knx.queue_command(_now() + datetime.timedelta(seconds=time), _knx_addr_short_move(shutter_adr), _CMD_UP)
    return "down ok", False


def stepup(shutter_adr):
    knx.queue_command(_now(), _knx_addr_short_move(shutter_adr), _CMD_UP)
    return "stepup ok", False


def stepdown(shutter_adr):
    knx.queue_command(_now(), _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    return "stepdown ok", False


def stop(shutter_adr):
    knx.queue_command(_now(), _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    knx.queue_command(_now(), _knx_addr_short_move(shutter_adr), _CMD_UP)
    return "stop ok", False


def angle(shutter_adr, angle=None):
    if angle not in [0, 1, 2, 3]:
        return "bad angle, use one of [0, 1, 2, 3]", True
    knx.queue_command(_now() + _cmd_timeout * 0, _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    knx.queue_command(_now() + _cmd_timeout * 1, _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    knx.queue_command(_now() + _cmd_timeout * 2, _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    knx.queue_command(_now() + _cmd_timeout * 3, _knx_addr_short_move(shutter_adr), _CMD_DOWN)
    for i in range(angle):
        knx.queue_command(_now() + _cmd_timeout * (4 + i), _knx_addr_short_move(shutter_adr), _CMD_UP)

    return "angle %s ok" % angle, False


# format : "commandName : {commandFunction, paramterName}
# only one parameter per command is currently supported
shutter_commands = {
    "up": (up, "time", int),
    "down": (down, "time", int),
    "stepup": (stepup, None, None),
    "stepdown": (stepdown, None, None),
    "stop": (stop, None, None),
    "angle": (angle, "angle", int),
}
