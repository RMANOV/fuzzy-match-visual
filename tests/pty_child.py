"""Owned child: establish controlling tty before executing unchanged demo."""
import fcntl
import json
import os
import runpy
import select
import sys
import termios

demo = os.path.realpath(sys.argv[1])
ack_fd = int(sys.argv[2])
try:
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    os.tcsetpgrp(0, os.getpgrp())
    identity = {'pid': os.getpid(), 'sid': os.getsid(0), 'pgid': os.getpgrp(),
                'foreground': os.tcgetpgrp(0), 'tty_fds': [os.isatty(i) for i in (0, 1, 2)]}
    assert identity['pid'] == identity['sid'] == identity['pgid'] == identity['foreground']
    assert all(identity['tty_fds'])
    print('PTY_IDENTITY=' + json.dumps(identity), flush=True)
    if not select.select([ack_fd], [], [], 15)[0]:
        raise RuntimeError('Owned parent acknowledgement deadline exceeded')
    if os.read(ack_fd, 1) != b'G':
        raise RuntimeError('Missing exact owned parent acknowledgement')
finally:
    os.close(ack_fd)
runpy.run_path(demo, run_name='__main__')
