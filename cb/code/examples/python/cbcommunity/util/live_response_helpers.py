#!/usr/bin/env python
#
#The MIT License (MIT)
#
# Copyright (c) 2015 Bit9 + Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------
# Class for wrapping around Live Response connectivity and actions.
#
# TODO -- more actions wrapped, more error handling, potentially more post-processing
# of returned results?
#
# last updated 2015-05-17 by Ben Johnson bjohnson@bit9.com
#

import threading
import time


class LiveResponseHelper(threading.Thread):
    """
    Threaded class that should do a keep-alive and handle the establishing of
    the live response session.
    """
    def __init__(self, ext_cbapi, sensor_id):
        self.cb = ext_cbapi
        self.sensor_id = sensor_id
        self.session_id = None
        self.keep_alive_time = 60
        self.go = True
#        self.lock = threading.RLock()
        self.ready_event = threading.Event()
        self.ready_event.clear()
        threading.Thread.__init__(self)

    ###########################################################################

    def __create_session(self):
        target_session = self.cb.live_response_session_create(self.sensor_id)
        self.session_id = target_session.get('id')
        while target_session.get('status') == "pending":
            time.sleep(5.0)
            target_session = self.cb.live_response_session_status(self.session_id)
            if not self.go:
                break

    def __post_and_wait(self, command, command_object=None):
        resp = self.cb.live_response_session_command_post(self.session_id, command, command_object)
        command_id = resp.get('id')
        return self.cb.live_response_session_command_get(self.session_id, command_id, wait=True)

    ###########################################################################

    def run(self):
        # THIS THREAD IS FOR KEEP-ALIVE
        self.__create_session()
        self.ready_event.set()

        while self.go:
            self.cb.live_response_session_keep_alive(self.session_id)
            for i in xrange(self.keep_alive_time):
                time.sleep(1.0)
                if not self.go:
                    break

    def stop(self, wait=True):
        self.go = False
        if wait:
            self.join()

    ###########################################################################

    def process_list(self):
        # with self.lock: # overkill but shouldn't be a big performance hit
        self.ready_event.wait()
        return self.__post_and_wait("process list").get('processes', [])

    def kill(self, pid):
#        with self.lock: # overkill but shouldn't be a big performance hit
        self.ready_event.wait()
        return self.__post_and_wait("kill", pid)

    def get_file(self, filepath):
        self.ready_event.wait()
        ret = self.__post_and_wait("get file", filepath)
        fileid = ret["file_id"]
        return self.cb.live_response_session_command_get_file(self.session_id, fileid)


