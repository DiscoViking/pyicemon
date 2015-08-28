import unittest

import messages

class TestPack(unittest.TestCase):

    def test_login(self):
        m = messages.LoginMessage()
        self.assertEqual(m.pack(), b'')

    def test_stats(self):
        m = messages.StatsMessage(1234, b'Name:Me\nMaxJobs:4')
        self.assertEqual(m.pack(),
                         (
                             b'\x00\x00\x04\xd2'
                             b'\x00\x00\x00\x11'
                             b'Name:Me\nMaxJobs:4\x00'
                         )
                         )

    def test_local_job_begin(self):
        m = messages.LocalJobBeginMessage(1001, 2001, 0, b'test_file.c')
        self.assertEqual(m.pack(),
                         (
                             b'\x00\x00\x07\xd1'  # Job ID: 2001
                             b'\x00\x00\x03\xe9'  # Client ID: 1001
                             b'\x00\x00\x00\x00'  # Timestamp.
                             b'\x00\x00\x00\x0b'  # Filename length.
                             b'test_file.c\x00'   # Filename.
                         )
                         )

    def test_local_job_done(self):
        m = messages.LocalJobDoneMessage(2001)
        self.assertEqual(m.pack(), b'\x00\x00\x07\xd1')


if __name__ == '__main__':
    unittest.main()
