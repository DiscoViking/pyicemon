import unittest

import messages
from monitor import Monitor


class DummyConnection(object):
    next_msg = None
    sent_msg = None

    def __init__(self):
        pass

    def send_message(self, msg):
        self.sent_msg = msg

    def get_message(self):
        return self.next_msg


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


class TestMonitor(unittest.TestCase):

    def test_negative_jobs(self):
        """Test that a CS can't go into negative active jobs."""
        m = Monitor(DummyConnection())

        # Receive JobBeign messages before CS Stats.
        m.handleGetCS(messages.GetCSMessage("file.c", 1, 1, 201))
        m.handleJobBegin(messages.JobBeginMessage(1, 0, 101))

        # Activate the CS.
        stats = messages.StatsMessage(101, b'')
        stats.data["Name"] = "cs1"
        stats.data["IP"] = "1.1.1.1"
        stats.data["MaxJobs"] = "4"
        m.handleStats(stats)

        # Receive a JobDone twice for the same job.
        m.handleJobDone(messages.JobDoneMessage(1, 0,
                                                0, 0, 0, 0,     # We don't care
                                                0, 0, 0, 0, 0)) # about these.
        m.handleJobDone(messages.JobDoneMessage(1, 0,
                                                0, 0, 0, 0,     # We don't care
                                                0, 0, 0, 0, 0)) # about these.
        self.assertEqual(m.cs[101].active_jobs, 0)


if __name__ == '__main__':
    unittest.main()
