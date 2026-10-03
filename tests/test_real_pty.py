"""Real POSIX PTY boundary coverage; parent never imports the demo."""
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import termios
import time
import unittest

DEMO = Path(__file__).resolve().parents[1] / 'demo.py'
BOOTSTRAP = Path(__file__).with_name('pty_child.py')
SOURCE_HASH = '3dce17d83b0a29c5b9a9ffcff4dc7091607e4e914ab8b45aa474a72f52d0e0f6'
ENV = {'PATH': '/usr/bin:/bin', 'TERM': 'xterm-256color', 'LANG': 'C.UTF-8'}
SELECTED_QUIT = b'\x1b[38;2;100;255;200m\xe2\x96\xb8 \x1b[1m[Q] Quit'
SELECTED_SPEED = b'\x1b[38;2;100;255;200m\xe2\x96\xb8 \x1b[1m[S] Speed Control'


class Session:
    def __init__(self, cols=80):
        self.master = self.slave = self.child = self.original = None
        self.ack_read = self.ack_write = None
        self.output = bytearray()
        self.deadline = time.monotonic() + 15
        try:
            self.master, self.slave = pty.openpty()
            fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, cols, 0, 0))
            self.original = termios.tcgetattr(self.slave)
            self.ack_read, self.ack_write = os.pipe()
            command = [sys.executable, '-I', '-B', str(BOOTSTRAP), str(DEMO), str(self.ack_read)]
            self.child = subprocess.Popen(command, stdin=self.slave, stdout=self.slave,
                stderr=self.slave, cwd=str(DEMO.parent), env=ENV,
                close_fds=True, pass_fds=(self.ack_read,), start_new_session=True)
            os.close(self.ack_read)
            self.ack_read = None
            self.expect(b'PTY_IDENTITY=')
            self.expect(b'\n')
            line = bytes(self.output).split(b'PTY_IDENTITY=', 1)[1].split(b'\n', 1)[0]
            identity = json.loads(line)
            assert identity['pid'] == self.child.pid
            assert identity['sid'] == identity['pgid'] == identity['foreground'] == self.child.pid
            assert identity['tty_fds'] == [True, True, True]
            assert os.getsid(self.child.pid) == self.child.pid
            assert os.getpgid(self.child.pid) == self.child.pid
            # Child cannot run or exit through product rejection before this ACK.
            assert self.child.poll() is None
            if time.monotonic() >= self.deadline:
                raise AssertionError('Identity handshake exceeded child budget')
            if os.write(self.ack_write, b'G') != 1:
                raise AssertionError('Owned acknowledgement write incomplete')
            os.close(self.ack_write)
            self.ack_write = None
        except BaseException:
            self.close()
            raise

    def read(self):
        if time.monotonic() >= self.deadline:
            raise AssertionError('Owned child exceeded 15-second progress budget')
        if select.select([self.master], [], [], .05)[0]:
            try:
                data = os.read(self.master, 8192)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                data = b''
            self.output.extend(data)
            if len(self.output) > 262144:
                raise AssertionError('Owned child output exceeded 256 KiB')

    def expect(self, token, start=0):
        while token not in self.output[start:]:
            if self.child.poll() is not None:
                self.read()
                if token not in self.output[start:]:
                    raise AssertionError('Child exited before expected interaction')
                break
            self.read()

    def key(self, value):
        raw_mask = termios.ICANON | termios.ISIG | termios.ECHO
        while termios.tcgetattr(self.slave)[3] & raw_mask:
            if self.child.poll() is not None:
                raise AssertionError('Child exited before raw-byte input')
            self.read()
        os.write(self.master, value)

    def finish(self):
        while self.child.poll() is None:
            self.read()
        while select.select([self.master], [], [], 0)[0]:
            before = len(self.output)
            self.read()
            if len(self.output) == before:
                break
        return self.child.returncode

    def close(self):
        try:
            if self.child is not None and self.child.poll() is None:
                self.child.terminate()
                try:
                    self.child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.child.kill()
                    self.child.wait(timeout=2)
            if self.child is not None:
                self.child.wait(timeout=2)
        finally:
            try:
                if (self.slave is not None and self.original is not None
                        and (self.child is None or self.child.returncode is not None)):
                    termios.tcsetattr(self.slave, termios.TCSANOW, self.original)
            finally:
                try:
                    if self.slave is not None:
                        descriptor, self.slave = self.slave, None
                        os.close(descriptor)
                finally:
                    try:
                        if self.master is not None:
                            descriptor, self.master = self.master, None
                            os.close(descriptor)
                    finally:
                        try:
                            if self.ack_read is not None:
                                descriptor, self.ack_read = self.ack_read, None
                                os.close(descriptor)
                        finally:
                            if self.ack_write is not None:
                                descriptor, self.ack_write = self.ack_write, None
                                os.close(descriptor)


class RealTerminal(unittest.TestCase):
    def setUp(self):
        self.assertEqual(hashlib.sha256(DEMO.read_bytes()).hexdigest(), SOURCE_HASH)

    def session(self, **options):
        item = Session(**options)
        self.addCleanup(item.close)
        return item

    def assert_clean_exit(self, item):
        self.assertEqual(item.finish(), 0)
        self.assertIn(b'\x1b[?1049h\x1b[?25l', item.output)
        self.assertTrue(item.output.endswith(b'\x1b[?25h\x1b[?1049l'))
        # Observe product restoration BEFORE cleanup's independent restoration.
        self.assertEqual(termios.tcgetattr(item.slave), item.original)

    def test_splash_menu_q_restores_terminal(self):
        item = self.session()
        item.expect(b'Press any key to start')
        item.key(b'x')
        item.expect(b'q: quit')
        item.key(b'q')
        self.assert_clean_exit(item)

    def test_up_wrap_and_enter_opens_speed_before_quit(self):
        item = self.session()
        item.expect(b'Press any key to start')
        item.key(b'x')
        item.expect(b'q: quit')
        offset = len(item.output)
        item.key(b'\x1b[A')
        item.expect(b'q: quit', offset)
        self.assertIn(SELECTED_QUIT, item.output[offset:])
        offset = len(item.output)
        item.key(b'\x1b[A')
        item.expect(b'q: quit', offset)
        self.assertIn(SELECTED_SPEED, item.output[offset:])
        offset = len(item.output)
        item.key(b'\r')
        item.expect(b'Animation Speed', offset)
        item.expect(b'Esc: back', offset)
        offset = len(item.output)
        item.key(b'q')
        item.expect(b'q: quit', offset)
        offset = len(item.output)
        item.key(b'\x1b[B')
        item.expect(b'q: quit', offset)
        self.assertIn(SELECTED_QUIT, item.output[offset:])
        item.key(b'\r')
        self.assert_clean_exit(item)

    def test_raw_ctrl_c_byte_decodes_interrupt_and_restores(self):
        for stage in ('splash', 'menu'):
            with self.subTest(stage=stage):
                item = self.session()
                item.expect(b'Press any key to start')
                if stage == 'menu':
                    item.key(b'x')
                    item.expect(b'q: quit')
                # ISIG is disabled: this is application byte decoding, not SIGINT.
                item.key(b'\x03')
                self.assert_clean_exit(item)

    def test_narrow_terminal_rejects_without_hiding_cursor(self):
        item = self.session(cols=59)
        self.assertEqual(item.finish(), 1)
        self.assertIn(b'Terminal too narrow', item.output)
        self.assertNotIn(b'\x1b[?1049h', item.output)
        self.assertNotIn(b'\x1b[?25l', item.output)
        self.assertEqual(termios.tcgetattr(item.slave), item.original)


if __name__ == '__main__':
    unittest.main()
