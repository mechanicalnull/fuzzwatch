from manul_utils import SHM_SIZE
from typing import Tuple

import logging
import numpy as np
import random
import string

from fuzzwatch_state import BITMAP_SIZE, ROW_SIZE


LOG_FILE = 'gui_log.txt'

def get_logger() -> logging.Logger:
    logger = logging.getLogger('__FILE__')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def get_rand_bytes(n: int) -> bytes:
    """Get a random string of bytes of length n"""
    return bytes([random.getrandbits(8) for _ in range(n)])


def format_hexdump(
    dump_data: bytes,
    data_offset: int=0,
):
    """Return an xxd-style hexdump with NULL byte separator between columns"""

    printable_chars = string.ascii_letters + string.digits + string.punctuation + ' '
    dump_size = len(dump_data)
    num_hex_digits = len(f'{len(dump_data)+data_offset:x}')
    # Any respectable hexdump has at least four digits of offset
    if num_hex_digits < 4:
        num_hex_digits = 4

    output = ''
    for i in range(0, dump_size, ROW_SIZE):
        row_data = dump_data[i:i+ROW_SIZE]
        row_offset = '{offset:0{width}x}'.format(offset=data_offset+i, width=num_hex_digits)
        row_hex = ''
        row_ascii = ''

        for j in range(ROW_SIZE):
            if j >= len(row_data):
                row_hex += '   '
            else:
                row_hex += f' {row_data[j]:02x}'
                cur_char = chr(row_data[j])
                if cur_char in printable_chars:
                    row_ascii += cur_char
                else:
                    row_ascii += '.'
            # break up long rows
            if (j+1) % 8 == 0:
                row_hex += ' '

        # Using a non-printable separator for ease of re-parsing by highlighting code
        output += f'{row_offset}:\x00{row_hex}\x00{row_ascii}\n'
    return output.strip()


def calculate_row_indices(
    row_start: int,
    mod_start: int,
    mod_end: int
) -> Tuple[int, int]:
    """Helper for determining the part of the row that needs highlighting"""
    if row_start > mod_start:
        highlight_start = 0
    else:
        highlight_start = mod_start - row_start
    highlight_stop = (mod_end+1) - row_start
    if highlight_stop > ROW_SIZE:
        highlight_stop = ROW_SIZE
    return highlight_start, highlight_stop


def split_hex_row(
    row_hex: str,
    start_index: int,
    stop_index: int
) -> Tuple[str, str, str]:
    """Helper for figuring out how to cleanly split a hex row for highlights"""
    # bytes are 2 hex chars plus 1 space, plus extra space every 8 bytes
    start_index = start_index * 3 + int(start_index / 8)
    stop_index = stop_index * 3 + int(stop_index / 8)

    before_hex = row_hex[:start_index]
    during_hex = row_hex[start_index:stop_index]
    after_hex = row_hex[stop_index:]
    return before_hex, during_hex, after_hex


def summarize_bitmap(bitmap: list) -> str:
    """Give a compact text summary for sparse bitmaps"""
    nonzero_bits = []
    for i, b in enumerate(bitmap):
        if b != 0:
            nonzero_bits.append(f'{i:x}:{b:02x}')
    sorted_nonzero_bits = ', '.join(sorted(nonzero_bits))
    summary = f'{len(nonzero_bits)}/{len(bitmap)}: {sorted_nonzero_bits}'
    return summary


hamming_weights = bytes(bin(x).count("1") for x in range(256))
def get_bitmap_coverage_stats(bitmap: list) -> Tuple[int, int]:
    """Get bits/bytes covered"""
    bits_set = 0
    nonzero_bytes = 0
    for i, b in enumerate(bitmap):
        if b != 0:
            nonzero_bytes += 1
            bits_set += hamming_weights[b]
    return nonzero_bytes, bits_set


fake_bitmap = None
def use_fake_bitmap(ignored_bitmap: bytes) -> np.ndarray:
    """Return a bitmap getting more saturated, for demonstration purposes"""
    global fake_bitmap
    if fake_bitmap is None:
        fake_bitmap = bytearray(BITMAP_SIZE+1)

    add_factor = random.randint(8, 1024)
    adds = 0
    prev_index = -1
    repeat_percent = 25

    while adds < add_factor:
        if prev_index == -1 or random.randint(0, 99) < repeat_percent:
            rand_index = random.randint(0, BITMAP_SIZE)
        else:
            rand_index = prev_index
        if fake_bitmap[rand_index] != 255:
            fake_bitmap[rand_index] += 1
            adds += 1
        prev_index = rand_index

    return bytes_to_matrix(fake_bitmap)


def bytes_to_matrix(byte_str: bytes, do_mix: bool=False) -> np.ndarray:
    """Format the bitmap so it can been ingested by matplotlib's matshow"""
    if len(byte_str) < BITMAP_SIZE:
        raise Exception(f'bytes_to_matrix(): incorrect input length: {len(byte_str)}')
    if do_mix:
        byte_str = mix_64k(byte_str)
    # tack on an extra byte if given 65,535 so we can make it square
    if len(byte_str) == BITMAP_SIZE:
        byte_str += b'\x00'
    data_array = np.frombuffer(byte_str, dtype='ubyte')
    return data_array.reshape(256, 256)


shuffled_array = None
def mix_64k(byte_str: bytes) -> bytes:
    global shuffled_array

    if shuffled_array is None:
        shuffled_array = list(range(BITMAP_SIZE))
        # Deterministically shuffle the array so it's the same across runs
        shuffler = random.Random()
        shuffler.seed(0)
        shuffler.shuffle(shuffled_array)

    if len(byte_str) != len(shuffled_array):
        raise Exception(f'mix_array got arg of len {len(byte_str)}, expected: {len(shuffled_array)}')

    # Use shuffled array to map indexes to a new deterministically mixed index
    return bytes(
        byte_str[shuffled_array[i]] for i in range(SHM_SIZE)
    )
