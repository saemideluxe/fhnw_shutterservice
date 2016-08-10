import flask
import flask_cors
import threading
import time
import logging
import sys

# our imports
import config
import commands
import knx


app = flask.Flask(__name__)
flask_cors.CORS(app)


@app.route("/")
def root():
    return flask.jsonify(knx="%sknx/" % flask.request.url_root)


@app.route("/knx/")
def knx_root():
    rooms = {"%s" % i: "%sknx/%s/" % (flask.request.url_root, i) for i in config.supported_rooms}
    return flask.jsonify(**rooms)


@app.route("/knx/<room>/")
def rooms(room):
    if room not in config.supported_rooms:
        return "Room '%s' is not supported" % room, 404

    shutters = {"%s" % i: "%sknx/%s/%s/" % (flask.request.url_root, room, i) for i in config.supported_rooms[room]}
    return flask.jsonify(**shutters)


@app.route("/knx/<room>/<shutter>/")
def shutter(room, shutter):
    if room not in config.supported_rooms:
        return "Room '%s' is not supported" % room, 404
    if shutter not in config.supported_rooms[room]:
        return "Shutter '%s' in room '%s' is not supported" % (shutter, room), 404

    shutter_cmds = {}
    for i in commands.shutter_commands:
        link = "%sknx/%s/%s/%s" % (flask.request.url_root, room, shutter, i)
        shutter_cmds[i] = {"call": link}
        param_name = commands.shutter_commands[i][1]
        param_type = commands.shutter_commands[i][2]
        if param_name:
            shutter_cmds[i]["param_name"] = param_name
            shutter_cmds[i]["param_type"] = param_type.__name__
    return flask.jsonify(**shutter_cmds)


@app.route("/knx/<room>/<shutter>/<command>")
def command(room, shutter, command):
    if room not in config.supported_rooms:
        return "Room '%s' is not supported" % room, 404
    if shutter not in config.supported_rooms[room]:
        return "Shutter '%s' in room '%s' is not supported" % (shutter, room), 404
    if command not in commands.shutter_commands:
        return "Command '%s' not supported" % command, 404

    func, param_name, param_type = commands.shutter_commands[command]
    arg = flask.request.args.get(param_name, None)
    shutter_adr = config.supported_rooms[room][shutter]
    if arg:
        try:
            arg = param_type(arg)
        except:
            return "argument '%s' is not allowed for this route" % arg, 400
        result = func(shutter_adr, arg)
    else:
        result = func(shutter_adr)

    arg_descr = {param_name: arg} if param_name else {}

    return flask.jsonify(room=room, shutter=shutter, command=command, knx_adr=shutter_adr, message=result[0], has_error=result[1], **arg_descr)


@app.route("/knx/log")
def log():
    _all = flask.request.args.get("all", "0")
    if _all == "1":
        return flask.jsonify(**knx.nice_log_format(knx.log))
    else:
        n = flask.request.args.get("n", "20")
        n = int(n) if n.isdigit() else 20
        return flask.jsonify(**knx.nice_log_format(knx.log[-n:]))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.NOTSET)
    knx.init()
    if not knx.connection.connected:
        print("could not connect to knx router, exit program")
        sys.exit(1)
    else:
        print("connected to knx router")
        app.run(host="0.0.0.0", port=50001, use_reloader=False, threaded=True)

