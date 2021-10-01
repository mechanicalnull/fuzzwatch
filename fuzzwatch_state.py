#   fuzzwatch_state.py - The shared state between the fuzzer and Fuzzwatch UI
#   -------------------------------------
#   Copyright 2021 @mechanicalnull
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from typing import List, Tuple, Optional
from multiprocessing import Array, Value, Lock, Process, Event

MUTATION_WINDOW_SIZE = 0x80
ROW_SIZE = 0x10
ZERO_STRING = b'\x00' * 256
BITMAP_SIZE = 65535


class GuiState():
    """Interface for shared process state between fuzzing process and GUI"""

    def __init__(self):
        # Guard read/write from this object using this lock for simplicity
        self.lock = Lock()
        self.alive = Event()
        self.fuzzer_exited = Event()
        self.gui_exited = Event()
        # Shared data

        # basic stats
        self.execs_per_sec = Value('d', 0)
        self.total_execs = Value('L', 0)
        self.total_time = Value('d', 0)
        self.since_last_path= Value('d', 0)
        self.since_last_crash = Value('d', 0)
        self.files_in_queue = Value('I', 0)
        self.new_paths = Value('I', 0)
        self.crashes = Value('I', 0)
        self.unique_crashes = Value('I', 0)

        # mutation stats
        self.mutator_name = Array('c', ZERO_STRING)
        self.cur_filename = Array('c', ZERO_STRING)
        self.modified_slice = Array('i', (-1, -1))
        self.hexdump_data = Array('B', [0] * MUTATION_WINDOW_SIZE)
        self.hexdump_size = Value('i', -1)
        self.hexdump_offset = Value('i', -1)

        # bitmaps
        self.cur_bitmap = Array('B', [0] * BITMAP_SIZE)
        # NOTE: Manul inverts their global bitmap, initializing similarly
        self.global_bitmap = Array('B', [0xff] * BITMAP_SIZE)

    def set_execs_per_sec(self, execs_per_sec: float):
        self.execs_per_sec.value = execs_per_sec

    def get_execs_per_sec(self) -> float:
        return self.execs_per_sec.value

    def set_total_execs(self, total_execs: int):
        self.total_execs.value = total_execs

    def get_total_execs(self) -> int:
        return self.total_execs.value

    def set_total_time(self, total_time: float):
        self.total_time.value = total_time

    def get_total_time(self) -> float:
        return self.total_time.value

    def set_since_last_path(self, since_last_path: float):
        self.since_last_path.value = since_last_path

    def get_since_last_path(self) -> float:
        return self.since_last_path.value

    def set_since_last_crash(self, since_last_crash: float):
        self.since_last_crash.value = since_last_crash

    def get_since_last_crash(self) -> float:
        return self.since_last_crash.value

    def set_files_in_queue(self, files_in_queue: int):
        self.files_in_queue.value = files_in_queue

    def get_files_in_queue(self) -> int:
        return self.files_in_queue.value

    def set_new_paths(self, new_paths: int):
        self.new_paths.value = new_paths

    def get_new_paths(self) -> int:
        return self.new_paths.value

    def set_crashes(self, crashes: int):
        self.crashes.value = crashes

    def get_crashes(self) -> int:
        return self.crashes.value

    def set_unique_crashes(self, unique_crashes: int):
        self.unique_crashes.value = unique_crashes

    def get_unique_crashes(self) -> int:
        return self.unique_crashes.value

    def set_mutator(self, name: str):
        with self.lock:
            self.mutator_name.value = ZERO_STRING
            self.mutator_name.value = name.encode('utf-8')

    def get_mutator(self) -> str:
        name = ''
        with self.lock:
            name = self.mutator_name.value.decode('utf-8')
        return name

    def set_modified_slice(self, modified_slice: Optional[Tuple[int, int]]):
        with self.lock:
            if modified_slice is None:
                self.modified_slice[0], self.modified_slice[1] = [-1, -1]
            else:
                self.modified_slice[0], self.modified_slice[1] = modified_slice

    def get_modified_slice(self) -> Tuple[int, int]:
        with self.lock:
            modified_slice = (self.modified_slice[0], self.modified_slice[1])
        return modified_slice

    def set_hexdump(self, data):
        """Pass hexdump data centered on modified slice; not the whole input"""
        with self.lock:
            orig_data_size = len(data)
            data_size = orig_data_size
            offset = 0

            # If all the data fits in the window, we're done, otherwise...
            if data_size > MUTATION_WINDOW_SIZE:
                data_size = MUTATION_WINDOW_SIZE

                # Null modification slice is possible
                if self.modified_slice[0] == -1 or self.modified_slice[1] == -1:
                    offset = 0

                else:
                    mod_start = self.modified_slice[0]
                    mod_end = self.modified_slice[1]
                    mod_start_row = int(mod_start / ROW_SIZE)
                    mod_end_row = int(mod_end / ROW_SIZE)
                    last_data_row = int(orig_data_size / ROW_SIZE)

                    # Check for close to data start/end
                    num_window_rows = int(MUTATION_WINDOW_SIZE / ROW_SIZE)
                    halfway = int(num_window_rows / 2)

                    # If close to start/end, use those as bounds
                    if mod_start_row <= halfway:
                        offset = 0

                    elif (last_data_row - mod_end_row) <= halfway:
                        offset_row = last_data_row - num_window_rows + 1
                        offset = offset_row * ROW_SIZE
                        # the data may now end earlier than the last full row
                        data_size = orig_data_size - offset

                    else:
                        # we've got at least "halfway" rows on each side,
                        # so center the rows spanned by the modification
                        span_rows = mod_end_row - mod_start_row
                        if span_rows < 3:
                            start_row = mod_start_row - 3
                        elif span_rows < 6:
                            start_row = mod_start_row - 2
                        elif span_rows < num_window_rows:
                            start_row = mod_start_row - 1
                        else:
                            start_row = mod_start_row
                        offset = start_row * ROW_SIZE

            self.hexdump_data[:data_size] = data[offset:offset+data_size]
            self.hexdump_size.value = data_size
            self.hexdump_offset.value = offset

    def get_hexdump(self) -> Tuple[bytes, int]:
        with self.lock:
            hexdump_size = self.hexdump_size.value
            hexdump_bytes = self.hexdump_data[:hexdump_size]
            offset = self.hexdump_offset.value
        return hexdump_bytes, offset

    def set_cur_filename(self, filename: str):
        with self.lock:
            self.cur_filename.value = ZERO_STRING
            self.cur_filename.value = filename.encode('utf-8')

    def get_cur_filename(self) -> str:
        name = ''
        with self.lock:
            name = self.cur_filename.value.decode('utf-8')
        return name

    def set_cur_bitmap(self, cur_bitmap: bytes):
        with self.lock:
            self.cur_bitmap[:] = cur_bitmap

    def get_cur_bitmap(self) -> bytes:
        cur_bitmap = b''
        with self.lock:
            cur_bitmap = bytes(self.cur_bitmap[:])
        return cur_bitmap

    def set_global_bitmap(self, global_bitmap: bytes):
        with self.lock:
            self.global_bitmap[:] = global_bitmap

    def get_global_bitmap(self) -> bytes:
        global_bitmap = b''
        with self.lock:
            global_bitmap = bytes(self.global_bitmap[:])
        # manul uses an inverted global bitmap, so re-invert here. Doing so
        # here is more expensive, but it keeps the data consistent between
        # global and current bitmaps coming out of this class
        return bytes(b ^ 0xff for b in global_bitmap)

    # Fuzzer/GUI sync functions
    def set_fuzzer_exited(self):
        self.fuzzer_exited.set()

    def check_fuzzer_exited(self) -> bool:
        return self.fuzzer_exited.is_set()

    def set_gui_exited(self):
        self.gui_exited.set()

    def check_gui_exited(self) -> bool:
        return self.gui_exited.is_set()

    def set_alive(self):
        self.alive.set()

    def check_alive(self) -> bool:
        return self.alive.is_set()
