"""Linux PTY regression tests; no radio hardware or elevated privileges needed."""
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux tty EOF semantics')
class UARTDisconnectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.binary = str(Path(cls.directory.name) / 'uart-test')
        subprocess.run([
            'g++', '-std=c++11', '-O2', '-I', str(ROOT),
            str(ROOT / 'tests/uart_disconnect.cpp'),
            *[str(ROOT / name) for name in ('UARTController.cpp', 'ModemPort.cpp', 'SerialPort.cpp')],
            '-o', cls.binary,
        ], check=True)

    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.process = None
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if self.process:
            if self.process.poll() is None:
                self.process.kill()
            self.process.communicate()
        for fd in (self.master, self.slave):
            if fd is not None:
                os.close(fd)

    def start(self, length=1):
        self.process = subprocess.Popen(
            [self.binary, os.ttyname(self.slave), str(length)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertTrue(select.select([self.process.stdout], [], [], 3)[0])
        self.assertEqual(self.process.stdout.readline().strip(), 'ready')
        os.close(self.slave)
        self.slave = None

    def disconnect(self):
        os.close(self.master)
        self.master = None
        try:
            self.process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('UART read did not return after tty disconnect')
        self.assertEqual(self.process.returncode, 4)

    def test_disconnect_before_data_returns_error(self):
        self.start()
        self.disconnect()

    def test_disconnect_during_partial_read_returns_error(self):
        self.start(3)
        os.write(self.master, b'\xe0')
        time.sleep(0.1)
        self.disconnect()

    def test_idle_port_is_not_disconnected(self):
        self.start()
        time.sleep(0.1)
        self.assertIsNone(self.process.poll())
        os.write(self.master, b'\xe0')
        out, err = self.process.communicate(timeout=2)
        self.assertEqual(self.process.returncode, 0, err)
        self.assertEqual(out.strip(), 'e0')

    def test_fragmented_frame_still_reads_completely(self):
        self.start(3)
        os.write(self.master, b'\xe0')
        time.sleep(0.1)
        os.write(self.master, b'\x03\x01')
        out, err = self.process.communicate(timeout=2)
        self.assertEqual(self.process.returncode, 0, err)
        self.assertEqual(out.strip(), 'e00301')


if __name__ == '__main__':
    unittest.main()
