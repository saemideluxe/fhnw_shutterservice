import knxip
import knxip.ip
import atexit
import sys
import datetime
import queue
import json
import threading
import time


def _shutdown():
    knw_command_thread.stop.set()
    knw_command_thread.join()
    print("shutdown")
    _log_dump(len(log))
    print("write log dump (%d entries)" % len(log))



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
    with open(logdir + "/" + datetime.datetime.now().strftime("%YY%m%d_%H%M%s.json"), "w") as f:
        f.write(json.dumps(nice_log_format(to_dump)))
    del log[:nitems]


def nice_log_format(logs):
    return {i[0].isoformat(): {"knx-dst-addr": i[1], "data": i[2]} for i in logs}


def queue_command(execution_time, knx_address, data):
    command_queue.put((execution_time, knx_address, data))


class KNXCommandWorker(threading.Thread):
    def __init__(self, router_ip, log, cmd_queue):
        threading.Thread.__init__(self)
        self.stop = threading.Event()
        self.connection = knxip.ip.KNXIPTunnel(router_ip)
        self.connection.notify = self.notify
        self.log = log
        self.command_queue = cmd_queue
        self.connected = self.connection.connect()
        
    def run():
        while not self.stop.is_set():
            now = datetime.datetime.now()
            if not self.command_queue.empty() and self.command_queue.queue[0][0] <= now:
                next_cmd = self.command_queue.get()
                self.connection.group_write(_logical_addr_to_bin(next_cmd[1]), next_cmd[2])
            time.sleep(0.2)
        self.connection.disconnect()

    def notify(addr, data):
        now = datetime.datetime.now()
        self.log.append((now, _bin_to_logical_addr(addr), [int(i) for i in data]))
        if (self.log[-1][0] - self.log[0][0]).total_seconds() / 3600 >= 24:
            to_log = filter(lambda a: (now - a[0]).total_seconds > (12 * 3600), self.log)
            _log_dump(len(to_log))


logdir = "./logs/"
log = []
command_queue = queue.PriorityQueue()
router_ip = "10.20.1.11"
knx_command_thread = KNXCommandWorker(router_ip, log, command_queue)
atexit.register(_shutdown)

knx_command_thread.start()

time.sleep(2)

if not knx_command_thread.connected:
    print("could not connect to knx router at %s" % router_ip)
    sys.exit(1) 
