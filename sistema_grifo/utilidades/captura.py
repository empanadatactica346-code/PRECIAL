"""Captura de la ventana del programa (Windows, PrintWindow) para el manual."""
import ctypes
from ctypes import wintypes


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32)]


def capturar_ventana(ventana, ruta):
    """Guarda en 'ruta' una imagen de la ventana aunque esté tapada. Devuelve True si pudo."""
    try:
        from PIL import Image
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        hwnd = u.GetParent(ventana.winfo_id()) or ventana.winfo_id()
        r = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w <= 0 or h <= 0:
            return False
        hdc = u.GetWindowDC(hwnd)
        mdc = g.CreateCompatibleDC(hdc)
        bmp = g.CreateCompatibleBitmap(hdc, w, h)
        g.SelectObject(mdc, bmp)
        u.PrintWindow(hwnd, mdc, 2)
        bi = _BITMAPINFOHEADER(40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        u.ReleaseDC(hwnd, hdc)
        img = Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)
        if img.getextrema() == ((0, 0), (0, 0), (0, 0)):   # captura vacía
            return False
        img.save(ruta)
        return True
    except Exception:
        return False
