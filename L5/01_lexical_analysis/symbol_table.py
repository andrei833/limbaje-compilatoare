"""Small Python interface to the C symbol table; CFFI handles compilation."""

from functools import lru_cache
from os import getuid
from pathlib import Path
from tempfile import gettempdir

from cffi import FFI

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_library():
    """Compile once when needed, reusing CFFI's cache on subsequent runs."""
    ffi = FFI()
    ffi.cdef("""
        typedef ... SymbolTable;
        SymbolTable *st_create(void);
        int st_insert(SymbolTable *table, const char *value, int type);
        int st_lookup(const SymbolTable *table, const char *value);
        int st_position(const SymbolTable *table, const char *value);
        int st_size(const SymbolTable *table);
        int st_type(const SymbolTable *table, int row);
        int st_bucket(const SymbolTable *table, int row);
        const char *st_value(const SymbolTable *table, int row);
        void st_destroy(SymbolTable *table);
    """)
    cache = Path(gettempdir()) / f"lab5-cffi-{getuid()}"
    cache.mkdir(parents=True, exist_ok=True)
    source = (ROOT / "02_symbol_table/symbol_table.c").read_text(encoding="utf-8")
    library = ffi.verify(source, tmpdir=str(cache), extra_compile_args=["-std=c11"])
    return ffi, library


class SymbolTable:
    def __init__(self):
        self.ffi, self.lib = load_library()
        self.ptr = self.lib.st_create()
        if self.ptr == self.ffi.NULL:
            raise MemoryError("Cannot create symbol table")

    def insert(self, value, symbol_type):
        symbol_id = self.lib.st_insert(self.ptr, value.encode("ascii"), symbol_type)
        if symbol_id < 0:
            raise MemoryError("Cannot insert symbol")
        return symbol_id, self.lib.st_position(self.ptr, value.encode("ascii"))

    def rows(self):
        return [
            {
                "index": self.lib.st_bucket(self.ptr, index),
                "bucket_position": self.lib.st_position(
                    self.ptr, self.lib.st_value(self.ptr, index)
                ),
                "type": ("Identifier", "Constant", "Constant")[
                    self.lib.st_type(self.ptr, index)
                ],
                "value": self.ffi.string(self.lib.st_value(self.ptr, index)).decode(
                    "ascii"
                ),
            }
            for index in range(self.lib.st_size(self.ptr))
        ]

    def close(self):
        if self.ptr != self.ffi.NULL:
            self.lib.st_destroy(self.ptr)
            self.ptr = self.ffi.NULL

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
