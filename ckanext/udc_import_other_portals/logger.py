import logging
import traceback


log = logging.getLogger(__name__)


class ImportLogger:
    """Log to file and memory."""

    def __init__(self, base_logger=log):
        self.base_logger = base_logger
        self.logs = []
        self.has_error = False
        self.has_warning = False

    def exception(self, e):
        trace = "".join(traceback.TracebackException.from_exception(e).format())
        self.logs.append(f"Exception: {trace}")
        self.base_logger.exception(e)
        self.has_error = True
        return e

    def warning(self, s):
        self.logs.append(f"Warning: {s}")
        self.base_logger.warning(s)
        self.has_error = True

    def error(self, s):
        self.logs.append(f"Error: {s}")
        self.base_logger.error(s)
        self.has_warning = True

    def info(self, s):
        self.logs.append(f"Info: {s}")
        self.base_logger.info(s)
