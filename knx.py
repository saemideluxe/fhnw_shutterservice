import knxip
import knxip.ip
import atexit
import sys
import os
import datetime
import queue
import json
import threading
import time
import logging


def _shutdown():
    connection.disconnect()
    print("shutdown")
    log_len = len(log)
    _log_dump(log_len)
    print("write log dump (%d entries)" % log_len)


# addr must be sequence of 3 int
def _logical_addr_to_bin(addr):
    if len(addr) != 3:
        return None
    if not all([type(a) == int for a in addr]):
        return None
    return ((addr[0] & 15) << 11) | ((addr[1] & 7) << 8) | (addr[2] & 255)

def _bin_to_logical_addr(bin_val):
    master_group = (bin_val >> 11) & 15
    subgroup = (bin_val >> 8) & 7
    group = bin_val & 255
    return (master_group, subgroup, group)


def _log_dump(nitems):
    to_dump = log[:nitems]
    with open(logdir + "/" + datetime.datetime.now().strftime("%YY%m%d_%H%M%S.json"), "w") as f:
        f.write(json.dumps(nice_log_format(to_dump)))
    del log[:nitems]


def nice_log_format(logs):
    return {i[0].isoformat(): {"knx-dst-addr": i[1], "data": i[2]} for i in logs}


def queue_command(execution_time, knx_address, data):
    command_queue.put((execution_time, knx_address, data))
    logging.info("added command to knx-queue: knx_address: %s, data: %s" % (knx_address, data))


class KNXCommandWorker(threading.Thread):
    def __init__(self, connection, log, cmd_queue):
        threading.Thread.__init__(self, daemon=True)
        self.connection = connection
        self.connection.notify = self.notify
        self.log = log
        self.command_queue = cmd_queue
        
    def run(self):
        connection.connect()
        while True:
            for i in range(50):
                now = datetime.datetime.now()
                if self.connection.connected:
                    if not self.command_queue.empty() and self.command_queue.queue[0][0] <= now:
                        next_cmd = self.command_queue.get()
                        addr = _logical_addr_to_bin(next_cmd[1])
                        cemi = knxip.ip.CEMIMessage()
                        cemi.init_group_write(addr, next_cmd[2])
                        cemi.ctl2 = 0xf0 # set routing-count to 7 (7 = endless routing)
                        self.connection.send_tunnelling_request(cemi, auto_connect=False)
                        print("sent knx command: %s" % cemi)
                else:
                    # logging.warning("connection lost, try to reconnect")
                    self.connection.data_server.shutdown()
                    self.connection.data_server.server_close()
                    self.connection.data_server = None
                    self.connection.disconnect()
                    time.sleep(1)
                    # self.connection = knxip.ip.KNXIPTunnel(router_ip)
                    # self.connection.connect()
                    # time.sleep(1)
                    os._exit(1)
                time.sleep(0.2)
            self.command_queue.put((now, (4,3,153), [0]))

    def notify(self, addr, data):
        now = datetime.datetime.now()
        self.log.append((now, _bin_to_logical_addr(addr), [int(i) for i in data]))
        if (self.log[-1][0] - self.log[0][0]).total_seconds() / 3600 >= 24:
            to_log = filter(lambda a: (now - a[0]).total_seconds > (12 * 3600), self.log)
            _log_dump(len(to_log))


logdir = "./logs/"
router_ip = "10.20.1.11"
log = []
command_queue = queue.PriorityQueue()
connection = knxip.ip.KNXIPTunnel(router_ip)
knx_command_thread = KNXCommandWorker(connection, log, command_queue)

def init():
    atexit.register(_shutdown)
    knx_command_thread.start()

