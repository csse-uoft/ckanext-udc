import logging
import traceback

from ckanext.udc_import_other_portals.worker.socketio_client import SocketClient


log = logging.getLogger(__name__)

def generate_trace(e):
    trace = "".join(traceback.TracebackException.from_exception(e).format())
    return f"Exception: {trace}"


class ImportLogger:
    """Log to file and memory."""
    total = 0
    current = 0
    finished = []

    def __init__(self, base_logger=log, total=0, socket_client: SocketClient = None):
        self.base_logger = base_logger
        self.logs = []
        self.has_error = False
        self.has_warning = False
        self.socket_client = socket_client
        self.total = total

    def exception(self, e):
        trace = generate_trace(e)
        self.logs.append(trace)
        self.base_logger.exception(e)
        self.has_error = True
        if self.socket_client:
            self.socket_client.send_message("exception", trace)
        return e

    def warning(self, s):
        self.logs.append(f"Warning: {s}")
        self.base_logger.warning(s)
        self.has_error = True
        if self.socket_client:
            self.socket_client.send_message("warning", s)

    def error(self, s):
        self.logs.append(f"Error: {s}")
        self.base_logger.error(s)
        self.has_warning = True
        if self.socket_client:
            self.socket_client.send_message("error", s)

    def info(self, s):
        self.logs.append(f"Info: {s}")
        self.base_logger.info(s)
        if self.socket_client:
            self.socket_client.send_message("info", s)
    
    def finished_one(self, type: str, id, name, title, logs='', duplications=None):
        
        if not self.socket_client:
            return
        
        data = {"id": id, "name": name, "title": title}
        
        if duplications:
            data['duplications'] = duplications
        
        if type == 'created':
            self.socket_client.finish_one(type, data)
            self.current += 1
        elif type == 'updated':
            self.socket_client.finish_one(type, data)
            self.current += 1
        elif type == 'deleted':
            self.socket_client.finish_one(type, data)
        elif type == 'errored':
            data["logs"] = logs
            self.socket_client.finish_one(type, data)
            self.current += 1
        else:
            self.error(f"Unknow message type: {type}, uuid={uuid} name={name}")
            
        self.socket_client.update_progress(self.current, self.total)
    
        