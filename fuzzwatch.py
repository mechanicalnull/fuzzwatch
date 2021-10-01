#   Fuzzwatch - A UI for seeing what's happening inside a fuzzer
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


from typing import Tuple, List, Set

import time
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import PySimpleGUI as sg

from hashlib import sha1
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from fuzzwatch_state import GuiState
from fuzzwatch_utils import (
    calculate_row_indices, split_hex_row, bytes_to_matrix,
    format_hexdump, summarize_bitmap, get_bitmap_coverage_stats
)


class FuzzGui():
    def __init__(self, gui_state: GuiState) -> None:
        self.gui_state = gui_state
        self.gui_state.set_alive()

        # GUI variables
        updates_per_sec = 30
        self.ms_update_freq = 1000 / updates_per_sec
        self.gui_loop_iterations = 0
        #self.ms_update_freq = 5000

        # GUI members
        self.window = None
        self.cur_bitmap = None
        self.global_bitmap = b''
        self.bitmaps_seen: Set[str] = set()  # actually set of hashes for speed

        # Stats for coverage graph
        self.start_time = time.time()
        self.total_coverage_over_time: List[Tuple[int, float]] = [(0, 0.0)]
        self.prev_bits_set = 0

        # In very small bitmaps (typically toy instrumented targets), the very
        # small number of bits have a decent chance of being occluded by the
        # frames. We detect this and apply a constant mixing array to the
        # positions to scatter them and reduce the chance they are hidden.
        self.mix_bitmap_positions = False

        # Matplotlib-related variables
        self.axes_labels = {
            'bottom': False,
            'labelbottom': False,
            'labelleft': False,
            'labelright': False,
            'labeltop': False,
            'left': False,
            'right': False,
            'top': False
        }

    @staticmethod
    def set_theme():
        """Add a theme that harkens back to the good old days"""
        bg = '#071404'
        bg_highlight = '#1c4811'
        fg_darker = '#47ae40'
        fg = '#6EEE4E'

        green_on_black_theme = {
            'BACKGROUND': bg,
            'TEXT': fg,
            'INPUT': bg_highlight,
            'TEXT_INPUT': fg,
            'SCROLL': bg_highlight,
            'BUTTON': (fg, bg_highlight),
            'PROGRESS': (bg_highlight, fg_darker),
            'BORDER': 1,
            'SLIDER_DEPTH': 0,
            'PROGRESS_DEPTH': 0,
            'COLOR_LIST': [bg, bg_highlight, fg_darker, fg],
            'DESCRIPTION': ['#FF0000']
        }
        sg.theme_add_new('GreenOnBlack', green_on_black_theme)
        sg.theme('GreenOnBlack')

    @staticmethod
    def update_hexdump(
        hexdump_element: sg.Multiline,
        formatted_hexdump: str,
        modified_slice: Tuple[int, int],
    ):
        """Update the hexdump element with the modified slice highlighted in red

        Using a separate function because the Multiline element has to have a
        method invoked to change colors on and off. Built with the assumption of
        only one modified slice but that it can be arbitrary size.

        This function relies upon preformatting the text to insert null bytes to
        indicate where column splits are in the row, in the three-column format
        typical to hexdumps: "offset | hex bytes | ascii"."""
        COLUMN_MARKER = '\x00'
        # no modification case
        if modified_slice == (-1, -1):
            hexdump_element.Update(formatted_hexdump.replace(COLUMN_MARKER, '  '))
            return

        mod_start, mod_end = modified_slice
        hexdump_element.Update('')
        # Build the output row-by-row
        for row in formatted_hexdump.split('\n'):
            row_offset, row_hex, row_ascii = row.split(COLUMN_MARKER)
            row_start = int(row_offset[:-1], 16)

            # only care when we start, stop, or continue highlighting
            if (row_start <= mod_start) or (mod_end >= row_start):
                # Use the helper to get the indices
                start_index, stop_index = calculate_row_indices(row_start, mod_start, mod_end)

                hexdump_element.update(row_offset + '  ', append=True)

                before_hex, highlight_hex, after_hex = split_hex_row(row_hex, start_index, stop_index)
                hexdump_element.Update(f'{before_hex}', append=True)
                hexdump_element.Update(f'{highlight_hex}', text_color_for_value='red', append=True)
                hexdump_element.Update(f'{after_hex}  ', append=True)

                hexdump_element.Update(f'{row_ascii[:start_index]}', append=True)
                hexdump_element.Update(f'{row_ascii[start_index:stop_index]}', text_color_for_value='red', append=True)
                hexdump_element.Update(f'{row_ascii[stop_index:]}\n', append=True)
            else:
                # this isn't a row we need to highlight
                hexdump_element.Update(row.replace(COLUMN_MARKER, '  ') + '\n', append=True)

    def init_bitmap_graph(self):
        matplotlib.style.use('dark_background')

        fig = matplotlib.figure.Figure([10, 3.5])
        fig.set_facecolor('#071404')
        coverage_axes = fig.add_subplot(131)
        cur_axes = fig.add_subplot(132)
        global_axes = fig.add_subplot(133)

        cur_axes.set_box_aspect(1)
        cur_axes.plot()
        cur_axes.tick_params(axis='both', which='both', **self.axes_labels)
        cur_axes.set_title('Last Unique Bitmap')

        global_axes.set_box_aspect(1)
        global_axes.plot()
        global_axes.tick_params(axis='both', which='both', **self.axes_labels)
        global_axes.set_title('Global Bitmap Coverage')

        coverage_axes.set_box_aspect(1)
        coverage_axes.plot(self.total_coverage_over_time)

        matplotlib.use("TkAgg")
        figure_canvas_agg = FigureCanvasTkAgg(fig, self.elem_bitmap_canvas.TKCanvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side="top", fill="both", expand=1)

        self.fig_agg = figure_canvas_agg
        self.cur_axes = cur_axes
        self.global_axes = global_axes
        self.coverage_axes = coverage_axes

    def add_coverage_bits_datapoint(self, current_coverage_bits: int):
        seconds_elapsed = time.time() - self.start_time
        self.total_coverage_over_time.append((current_coverage_bits, seconds_elapsed))

    def update_coverage_graph(self):
        self.coverage_axes.clear()
        coverage_bits_entries, timestamp_entries = zip(*self.total_coverage_over_time)
        self.coverage_axes.set_xlabel('Seconds Elapsed')
        self.coverage_axes.set_ylabel('Coverage bits')
        self.coverage_axes.set_title('Coverage Bits over Time')
        self.coverage_axes.plot(timestamp_entries, coverage_bits_entries, color='red')
        self.fig_agg.draw()

    def maybe_add_coverage_timestamp(self, prev_bits_set: int):
        """Occasionally update the graph if coverage stayed the same"""
        seconds_elapsed = time.time() - self.start_time
        last_timestamp = self.total_coverage_over_time[-1][1]
        time_delta = seconds_elapsed - last_timestamp

        # Want infrequent updates scaled to time elapsed, but not a lot early on
        MIN_DELTA = 4
        UPDATE_SCALE = 1000
        current_threshold = seconds_elapsed / UPDATE_SCALE
        if time_delta > MIN_DELTA and time_delta > current_threshold:
            self.add_coverage_bits_datapoint(prev_bits_set)
            self.update_coverage_graph()

    def do_bitmap_update(self):
        """Update the bitmap graphs each time they change"""

        def update_graph(bitmap, axis):
            """Helper to clear and draw the bitmap for a given axis"""
            axis.clear()
            bitmap_data = bytes_to_matrix(bitmap, self.mix_bitmap_positions)
            marker_style = {
                'markersize': 1,
                'color': 'red',
                'markerfacecolor': 'tab:red',
                'markerfacecoloralt': 'red',
                'markeredgecolor': 'red'
            }
            marker_symbol = 's'
            axis.spy(
                bitmap_data,
                aspect='equal',
                marker=marker_symbol,
                **marker_style
            )
            axis.tick_params(axis='both', which='both', **self.axes_labels)
            return bitmap_data

        update_graph(self.cur_bitmap, self.cur_axes)
        self.cur_axes.set_title('Last Unique Bitmap')

        update_graph(self.global_bitmap, self.global_axes)
        self.global_axes.set_title('Global Bitmap Coverage')

        self.fig_agg.draw()

    def init_window(self):
        """Layout and instantiate GUI"""
        self.set_theme()

        # Stats
        #    Column 1
        self.elem_execs_per_sec = sg.Text('Initializing...', key='ExecsPerSec', size=[25, 1])
        self.elem_total_execs = sg.Text('', key='TotalExecs', size=[25, 1])
        self.elem_total_time = sg.Text('', key='TotalTime', size=[25, 1])
        self.elem_since_last_path = sg.Text('N/A', key='SinceLastPath', size=[25, 1])
        self.elem_since_last_crash = sg.Text('N/A', key='SinceLastCrash', size=[25, 1])
        #    Column 2
        self.elem_files_in_queue = sg.Text('', key='FilesInQueue', size=[25, 1])
        self.elem_new_paths = sg.Text('', key='NewPaths', size=[25, 1])
        self.elem_crashes = sg.Text('', key='Crashes', size=[25, 1])
        self.elem_unique_crashes = sg.Text('', key='UniqueCrashes', size=[25, 1])
        self.elem_bitmap_stats = sg.Text('', key='BitmapStats', size=[25, 1])
        # Mutation
        self.elem_cur_filename = sg.Text('Initializing...', key='CurrentFile', size=[60, 1])
        self.elem_cur_mutator = sg.Text('', key='MutatorName', size=[60, 1])
        self.elem_cur_slice = sg.Text('', key='ModifiedSlice', size=[60, 1])
        self.elem_hexdump = sg.Multiline('', size=(81, 8), key='MutatedHexdump', disabled=True)
        # Bitmaps
        self.elem_bitmap_canvas = sg.Canvas(key='BitmapCanvas', size=(512,512))

        def make_header(text):
            """Helper to add textual spacers to header text for visual breaks"""
            text_break = '=' * 16
            return f'{text_break} {text} {text_break}'

        layout = [
            [sg.Text(make_header('General Stats'))],
            [
                sg.Column([
                    [sg.Text('Execs/sec:   '), self.elem_execs_per_sec],
                    [sg.Text('Total Execs: '), self.elem_total_execs],
                    [sg.Text('Time Elapsed:'), self.elem_total_time],
                    [sg.Text('Time Since Last New Path:'), self.elem_since_last_path],
                    [sg.Text('Time Since Last Crash:   '), self.elem_since_last_crash],
                ]),
                sg.Column([
                    [sg.Text('Inputs in Queue: '), self.elem_files_in_queue],
                    [sg.Text('New Inputs Found:'), self.elem_new_paths],
                    [sg.Text('Crashes Found:   '), self.elem_crashes],
                    [sg.Text('Unique Crashes:  '), self.elem_unique_crashes],
                    [sg.Text('Global Bitmap:'), self.elem_bitmap_stats],
                ]),
            ],

            [sg.Text('\n' + make_header('Current Mutation'))],
            [sg.Text('Current File:', size=[18,1]), self.elem_cur_filename],
            [sg.Text('Current Mutator:', size=[18,1]), self.elem_cur_mutator],
            [sg.Text('Mutated Slice:', size=[18,1]), self.elem_cur_slice],
            [self.elem_hexdump],

            [sg.Text('\n' + make_header('Coverage Graphs'))],
            [self.elem_bitmap_canvas],
        ]

        self.window = sg.Window(
            "Fuzzwatch",
            layout,
            size=(1600,1600),
            location=(0, 0),
            finalize=True,
            element_justification="center",
            font="fixedsys 14",
        )

    def update_text_stats(self):
        self.elem_execs_per_sec.Update(f'{self.gui_state.get_execs_per_sec():.2f}')
        self.elem_total_execs.Update(f'{self.gui_state.get_total_execs()}')
        self.elem_total_time.Update(f'{self.gui_state.get_total_time():.2f}')
        self.elem_files_in_queue.Update(f'{self.gui_state.get_files_in_queue()}')

        new_paths = self.gui_state.get_new_paths()
        self.elem_new_paths.Update(f'{new_paths}')

        crashes = self.gui_state.get_crashes()
        if crashes > 0:
            self.elem_crashes.Update(str(crashes), text_color='red')
        else:
            self.elem_crashes.Update(str(crashes))

        uniq_crashes = self.gui_state.get_unique_crashes()
        if uniq_crashes > 0:
            self.elem_unique_crashes.Update(str(uniq_crashes), text_color='red')
        else:
            self.elem_unique_crashes.Update(str(uniq_crashes))

        if new_paths != 0:
            self.elem_since_last_path.Update(f'{self.gui_state.get_since_last_path():.2f}')

        if crashes != 0:
            self.elem_since_last_crash.Update(f'{self.gui_state.get_since_last_crash():.2f}')

    def update_mutation_window(self):
        current_filename = str(self.gui_state.get_cur_filename())
        self.elem_cur_filename.Update(current_filename)

        current_mutator = str(self.gui_state.get_mutator())
        self.elem_cur_mutator.Update(current_mutator)

        modified_slice = self.gui_state.get_modified_slice()
        self.elem_cur_slice.Update(modified_slice)

        hexdump_data, hexdump_offset = self.gui_state.get_hexdump()
        formatted_hexdump = format_hexdump(hexdump_data, hexdump_offset)
        self.update_hexdump(self.elem_hexdump, formatted_hexdump, modified_slice)

    def update_coverage_elements(self):
        # Don't update bitmaps every iteration, just when needed
        update_bitmaps = False
        new_bitmap = self.gui_state.get_cur_bitmap()
        if new_bitmap != self.cur_bitmap:
            bitmap_hash = sha1(new_bitmap).hexdigest()
            # To keep the cur bitmap from flipping too quickly to see (which
            # would look like just the common bitmap), show last unique bitmap
            if bitmap_hash not in self.bitmaps_seen:
                self.bitmaps_seen.add(bitmap_hash)
                self.cur_bitmap = new_bitmap
                update_bitmaps = True

        new_global_bitmap = self.gui_state.get_global_bitmap()
        if new_global_bitmap != self.global_bitmap:
            bytes_set, bits_set = get_bitmap_coverage_stats(new_global_bitmap)
            bitmap_coverage_str = f'{bits_set} bits / '
            bitmap_coverage_str += f'{bytes_set} bytes'
            self.elem_bitmap_stats.Update(bitmap_coverage_str)

            #new_bitmap_summary = summarize_bitmap(new_bitmap)
            #global_bitmap_summary = summarize_bitmap(new_global_bitmap)
            #print(f'[{self.gui_loop_iterations}] Global bitmap update ({bits_set} bits): {global_bitmap_summary}')

            if bits_set != self.prev_bits_set:
                # Apply mixing array if we start with a small number of bits
                if bits_set < 20:
                    self.mix_bitmap_positions = True
                # Adding a point for before and after creates a nice stairstep
                self.add_coverage_bits_datapoint(self.prev_bits_set)
                self.add_coverage_bits_datapoint(bits_set)
                self.update_coverage_graph()

            update_bitmaps = True
            self.global_bitmap = new_global_bitmap
            self.prev_bits_set = bits_set
        else:
            self.maybe_add_coverage_timestamp(self.prev_bits_set)

        if update_bitmaps:
            self.do_bitmap_update()

    def run(self):
        """The primary GUI poll/update function"""
        self.init_window()
        self.init_bitmap_graph()

        try:
            while True:
                event, values = self.window.read(timeout=self.ms_update_freq)
                if event == sg.WIN_CLOSED or event == 'Ok':
                    break
                # Check if the other side closed down
                if self.gui_state.fuzzer_exited.is_set():
                    break

                # Update each of the GUI elements by section
                self.update_text_stats()
                self.update_mutation_window()
                self.update_coverage_elements()

                self.gui_loop_iterations += 1

        except KeyboardInterrupt:
            print('[*] Caught CTRL+C in GUI process')
        self.window.close()


def run_gui(gui_state: GuiState):
    try:
        fuzz_gui = FuzzGui(gui_state)
        fuzz_gui.run()
    finally:
        gui_state.set_gui_exited()
