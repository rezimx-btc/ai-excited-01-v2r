#!/usr/bin/env python3
"""The Chart Came Alive -- ai-excited-01 v2r.

Entry program for make.fun's "Make the AI judge excited" bounty.
It writes the entry image (entry.png, JPEG bytes in a file named
entry.png -- the gate tells PNG and JPEG apart by their first bytes)
to $MAKEFUN_OUTPUT_DIR/entry.png (default /output), after checking
it against the gate limits: at most 1 MiB, at most 1024x1024 pixels,
and a whole, well-formed image file.

Python standard library only. No network, no randomness, no clock,
no third-party imports: the grader runs bare python:3.13. The copy
is byte-for-byte, so both grading runs write identical output.
"""

import hashlib
import os
import struct
import sys

MAX_BYTES = 1_048_576
MAX_SIDE = 1024

PNG_SIG = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"

# JPEG start-of-frame markers that carry width/height.
SOF_MARKERS = frozenset((0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                         0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF))


def png_size(data):
    """(width, height) if data is a PNG with a readable IHDR, else None."""
    if not data.startswith(PNG_SIG) or len(data) < 33:
        return None
    if data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def png_whole(data):
    """True if the PNG ends with a complete IEND chunk."""
    if len(data) < 12:
        return False
    # IEND is a 12-byte chunk: length 0, type IEND, CRC.
    return data[-12:-8] == b"\x00\x00\x00\x00" and data[-8:-4] == b"IEND"


def jpeg_whole(data):
    """True if the JPEG ends with its end-of-image marker."""
    return len(data) >= 2 and data[-2:] == b"\xff\xd9"


def jpeg_size(data):
    """(width, height) if data is a JPEG with a readable SOF, else None."""
    if not data.startswith(JPEG_SOI):
        return None
    pos = 2
    end = len(data)
    while pos + 4 <= end:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in SOF_MARKERS:
            if pos + 9 > end:
                return None
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD9:
            pos += 2
            continue
        if pos + 4 > end:
            return None
        seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if seg_len < 2:
            return None
        pos += 2 + seg_len
    return None


def image_size(data):
    """(width, height) for a PNG or JPEG, else None."""
    size = png_size(data)
    if size is not None:
        return size
    return jpeg_size(data)


def fail(message):
    sys.exit("entry rejected: " + message)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    try:
        with open(src, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        fail("cannot read entry image: %s" % exc)

    if len(data) == 0:
        fail("entry image is empty")
    if len(data) > MAX_BYTES:
        fail("entry image is %d bytes, over the 1 MiB cap" % len(data))

    size = image_size(data)
    if size is None:
        fail("entry image is neither a whole PNG nor a whole JPEG")
    width, height = size
    if width == 0 or height == 0:
        fail("entry image has a zero dimension")
    if width > MAX_SIDE or height > MAX_SIDE:
        fail("entry image is %dx%d, over the 1024x1024 cap"
             % (width, height))
    if data.startswith(PNG_SIG):
        if not png_whole(data):
            fail("entry PNG is truncated: no complete IEND chunk")
    elif not jpeg_whole(data):
        fail("entry JPEG is truncated: no end-of-image marker")

    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    dst = os.path.join(outdir, "entry.png")
    with open(dst, "wb") as handle:
        handle.write(data)

    with open(dst, "rb") as handle:
        written = handle.read()
    if written != data:
        fail("output verification failed: written bytes differ")

    digest = hashlib.sha256(data).hexdigest()
    print("wrote %s: %d bytes, %dx%d, sha256=%s"
          % (dst, len(data), width, height, digest))


if __name__ == "__main__":
    main()
