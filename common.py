import sys
import time
import logging
from typing import TextIO

log_level: int = logging.INFO
"""logging level"""

log_colorize: bool = True
"""use terminal colors for logs (only applies to stdout/stderr)"""

log_to_stdout: bool = True
"""write log entries to stdout"""

log_stderr_threshold: int = logging.FATAL
"""
write log entries at this level or higher to stderr (even if log_to_stdout is
False).
"""

log_always_include_thread_id: bool = False
"""always include the thread ID in log entries, even when it has a name."""

log_file: TextIO | None = None
"""optional log file"""

keyboard_interrupt: KeyboardInterrupt | None = None
"""
will be set if any thread in GoofyServer or GoofyClient catches a
KeyboardInterrupt.
"""


# ANSI color codes
COL_RESET = "\033[0m"
COL_BLACK = "\033[30m"
COL_RED = "\033[31m"
COL_GREEN = "\033[32m"
COL_YELLOW = "\033[33m"
COL_BLUE = "\033[34m"
COL_MAGENTA = "\033[35m"
COL_CYAN = "\033[36m"
COL_WHITE = "\033[37m"
COL_BRIGHT_BLACK = "\033[90m"
COL_BRIGHT_RED = "\033[91m"
COL_BRIGHT_GREEN = "\033[92m"
COL_BRIGHT_YELLOW = "\033[93m"
COL_BRIGHT_BLUE = "\033[94m"
COL_BRIGHT_MAGENTA = "\033[95m"
COL_BRIGHT_CYAN = "\033[96m"
COL_BRIGHT_WHITE = "\033[97m"


class LogFormatter(logging.Formatter):
    # force UTC timestamps
    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> tuple[str, str]:
        """
        returns a tuple containing the message and its terminal version which is
        potentionally colorized.
        """

        # thread ID and name
        if record.threadName and log_always_include_thread_id:
            record.threadName = f"{record.thread} {record.threadName}"
        elif not record.threadName:
            record.threadName = f"{record.thread}"

        if record.levelname == "CRITICAL":
            record.levelname = "FATAL"

        message = super().format(record)

        if log_colorize:
            if record.levelno >= logging.FATAL:
                color = COL_BRIGHT_RED
            elif record.levelno >= logging.ERROR:
                color = COL_RED
            elif record.levelno >= logging.WARNING:
                color = COL_YELLOW
            elif record.levelno < logging.INFO:
                color = COL_CYAN
            else:
                color = COL_RESET
            colorized = f"{color}{message}{COL_RESET}"
            return message, colorized
        else:
            return message, message


class LogHandler(logging.Handler):
    formatter: LogFormatter

    def __init__(self, formatter: LogFormatter):
        logging.Handler.__init__(self)

        if not isinstance(formatter, LogFormatter):
            raise ValueError(
                f"LogHandler's formatter must be a LogFormatter, not "
                f"{type(formatter)}."
            )
        self.formatter = formatter

    def flush(self):
        with self.lock:
            sys.stderr.flush()
            if log_to_stdout:
                sys.stdout.flush()
            if log_file is not None:
                log_file.flush()

    def emit(self, record):
        try:
            msg, msg_for_terminal = self.formatter.format(record)

            if record.levelno >= log_stderr_threshold:
                sys.stderr.write(msg_for_terminal)
            elif log_to_stdout:
                sys.stdout.write(msg_for_terminal)

            if log_file is not None:
                log_file.write(msg)

            with self.lock:
                sys.stderr.flush()
                if log_to_stdout:
                    sys.stdout.flush()
                if log_file is not None:
                    log_file.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


log_formatter = LogFormatter(
    "\n{levelname[0]} | {asctime} | {threadName} | {name}\n{message}\n",
    datefmt="%Y-%m-%d %H:%M:%S UTC",
    style="{"
)
log_handler = LogHandler(log_formatter)


def make_logger(name: str, level: int | None = None) -> logging.Logger:
    if level is None:
        level = log_level
    l = logging.Logger(name, level)
    l.addHandler(log_handler)
    return l


root_log = make_logger("root")


def format_exception(e: Exception) -> str:
    if (
        isinstance(e, int)
        or isinstance(e, str)
        or isinstance(e, bool)
        or isinstance(e, tuple)
        or isinstance(e, list)
        or isinstance(e, dict)
    ):
        return str(e)
    s = str(e)
    if s and type(e) is Exception:
        return s
    elif s:
        return f"{e.__class__.__name__}: {s}"
    else:
        return e.__class__.__name__


def unique(l: list):
    return list(dict.fromkeys(l))
