#!/usr/bin/env python3
"""CRI CPK (UTF table) reader for YU-NO assets.

CPK layout used by this game (CRI Filesystem 2.40):
  0x00  "CPK " magic + 4 bytes
  0x10  CpkHeader UTF table (holds TocOffset/TocSize/ContentOffset/...)
  TocOffset  CpkTocInfo UTF table (DirName/FileName/FileSize/ExtractSize/FileOffset/ID/UserString)

The TOC uses "default/const" columns (flag bit 0x20): those carry a 4-byte default
value inside the column definition and are not stored per row.

Usage:
  python cpk.py list    <file.cpk>
  python cpk.py extract <file.cpk> <outdir> [name-filter]
  python cpk.py cat     <file.cpk> <name-or-id>
"""
import os
import struct
import sys

TYPE_SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 0xA: 4, 0xB: 4}


class UtfTable:
    def __init__(self, data, off=0, label=""):
        if data[off:off + 4] != b"@UTF":
            raise ValueError("no @UTF at %#x" % off)
        self.data = data
        self.off = off
        (table_size, rows_off, strings_off, data_off, name_off,
         ncols, rowlen, nrows) = struct.unpack(">IIIIIHHI", data[off + 4:off + 32])
        self.strings = off + 8 + strings_off
        self.rows_off = off + 8 + rows_off
        self.rowlen = rowlen
        self.nrows = nrows
        self.cols = []          # (flags, name, const_value_or_None)
        p = off + 32
        for _ in range(ncols):
            flags = data[p]
            name_offset = struct.unpack(">I", data[p + 1:p + 5])[0]
            p += 5
            name = self.string(name_offset)
            const = None
            if flags & 0x20:
                const = struct.unpack(">I", data[p:p + 4])[0]
                p += 4
            self.cols.append((flags, name, const))
        self.col_names = [c[1] for c in self.cols]
        self.rows = self._read_rows()

    def string(self, offset):
        end = self.data.find(b"\0", self.strings + offset)
        if end < 0:
            end = len(self.data)
        return self.data[self.strings + offset:end].decode("utf-8", "replace")

    def _read_rows(self):
        rows = []
        for r in range(self.nrows):
            rp = self.rows_off + r * self.rowlen
            vals = {}
            for flags, name, const in reversed(self.cols):
                if const is not None:
                    if flags & 0x0F == 0x0A:
                        vals[name] = self.string(const) if const else ""
                    else:
                        vals[name] = const
                    continue
                t = flags & 0x0F
                size = TYPE_SIZES[t]
                raw = self.data[rp:rp + size]
                rp += size
                if t == 0x0A:
                    v = struct.unpack(">I", raw)[0]
                    vals[name] = self.string(v) if v else ""
                elif t == 0x0B:
                    vals[name] = struct.unpack(">I", raw)[0]
                else:
                    vals[name] = struct.unpack({1: ">B", 2: ">H", 4: ">I", 8: ">Q"}[size], raw)[0]
            rows.append(vals)
        return rows


def open_cpk(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"CPK ":
        raise ValueError("not a CPK: %r" % data[:4])
    header = UtfTable(data, 0x10, "CpkHeader")
    h = header.rows[0]
    toc = UtfTable(data, h["TocOffset"], "CpkTocInfo")
    return data, header, toc


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, path = argv[1], argv[2]
    data, header, toc = open_cpk(path)
    cols = toc.col_names
    if cmd == "list":
        print("columns:", cols)
        print("files:", toc.nrows)
        for r in toc.rows:
            print("%6d %-40s %10d %10d %10d %s" % (r.get("ID", -1), r.get("FileName", ""),
                                                   r.get("FileSize", 0), r.get("ExtractSize", 0),
                                                   r.get("FileOffset", 0), r.get("DirName", "")))
        return 0
    if cmd == "cat":
        key = argv[3]
        for r in toc.rows:
            if r.get("FileName") == key or str(r.get("ID")) == key:
                off, size = r["FileOffset"], r["FileSize"]
                sys.stdout.buffer.write(data[off:off + size])
                return 0
        print("not found:", key, file=sys.stderr)
        return 2
    if cmd == "extract":
        outdir = argv[3]
        filt = argv[4] if len(argv) > 4 else ""
        n = 0
        for r in toc.rows:
            fn = r.get("FileName", "")
            if filt and filt.lower() not in fn.lower():
                continue
            dest = os.path.join(outdir, r.get("DirName", ""), fn)
            os.makedirs(os.path.dirname(dest) or outdir, exist_ok=True)
            off, size = r["FileOffset"], r["FileSize"]
            with open(dest, "wb") as fh:
                fh.write(data[off:off + size])
            n += 1
        print("extracted", n, "files to", outdir)
        return 0
    print("unknown command", cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
