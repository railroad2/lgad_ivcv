"""VISA resource access with an optional NI GPIB-USB-HS user-space backend.

GPIB resource names such as ``GPIB0::24::INSTR`` are served through the
``ni_gpib_usb_hs`` package when it is selected; every other resource name is
opened by PyVISA. ``IVCV_GPIB_BACKEND`` selects the GPIB backend:

* ``auto`` (default): use the NI GPIB-USB-HS when the package is installed and
  the adapter is attached, otherwise PyVISA.
* ``niusb``: always use the NI GPIB-USB-HS.
* ``visa``: always use PyVISA.
"""
import os
import re
import threading

import pyvisa

try:
    import usb.core
    from ni_gpib_usb_hs import (
        NIUSBGPIB,
        GpibError,
        NI_GPIB_USB_HS_PID,
        NI_VID,
    )
except ImportError:
    NIUSBGPIB = None

    class GpibError(RuntimeError):
        pass


GPIB_BACKEND_ENV = "IVCV_GPIB_BACKEND"
RESOURCE_ERRORS = (pyvisa.VisaIOError, GpibError)

_GPIB_NAME = re.compile(r"^GPIB\d*::(\d+)::INSTR$", re.IGNORECASE)
_GPIB_SCAN_ADDRESSES = range(1, 31)
_GPIB_TIMEOUT_USEC = 10_000_000
_READ_LENGTH = 1024

_controller_lock = threading.RLock()
_controller = None
_controller_users = 0


def gpib_address(resource_name):
    """Return the primary address of a GPIB INSTR resource name, or None."""
    match = _GPIB_NAME.match(str(resource_name).strip())
    if match is None:
        return None
    return int(match.group(1))


def gpib_backend():
    backend = os.environ.get(GPIB_BACKEND_ENV, "auto").strip().lower() or "auto"
    if backend not in ("auto", "niusb", "visa"):
        raise ValueError(
            f"{GPIB_BACKEND_ENV} must be 'auto', 'niusb', or 'visa': {backend}"
        )
    return backend


def _adapter_attached():
    if _controller is not None:
        return True
    try:
        return usb.core.find(idVendor=NI_VID, idProduct=NI_GPIB_USB_HS_PID) is not None
    except Exception:
        return False


def use_niusb_gpib():
    """Whether GPIB resources are served by the NI GPIB-USB-HS backend."""
    backend = gpib_backend()
    if backend == "visa":
        return False
    if NIUSBGPIB is None:
        if backend == "niusb":
            raise GpibError(
                "ni_gpib_usb_hs is not installed; "
                "install it with 'pip install ni-gpib-usb-hs'"
            )
        return False
    return backend == "niusb" or _adapter_attached()


def _acquire_controller():
    """Open the adapter once and share it between all GPIB resources."""
    global _controller, _controller_users
    with _controller_lock:
        if _controller is None:
            _controller = NIUSBGPIB(timeout_usec=_GPIB_TIMEOUT_USEC)
        _controller_users += 1
        return _controller


def _release_controller():
    global _controller, _controller_users
    with _controller_lock:
        _controller_users -= 1
        if _controller_users <= 0 and _controller is not None:
            _controller.close()
            _controller = None
            _controller_users = 0


class NIUSBGPIBResource:
    """The subset of the PyVISA message-based resource API used by ``inst``."""

    def __init__(self, address):
        self.address = address
        self.resource_name = f"GPIB0::{address}::INSTR"
        # Accepted for PyVISA compatibility; the adapter uses a fixed timeout.
        self.timeout = _GPIB_TIMEOUT_USEC // 1000
        self._controller = _acquire_controller()

    def _require_controller(self):
        if self._controller is None:
            raise GpibError(f"{self.resource_name} is closed")
        return self._controller

    def write(self, message):
        with _controller_lock:
            self._require_controller().write(self.address, message)

    def read(self):
        with _controller_lock:
            data = self._require_controller().read(self.address, _READ_LENGTH)
        return data.decode(errors="replace").strip()

    def query(self, message):
        with _controller_lock:
            self.write(message)
            return self.read()

    def close(self):
        if self._controller is not None:
            self._controller = None
            _release_controller()


class ResourceManager:
    """A ``pyvisa.ResourceManager`` that can route GPIB to an NI GPIB-USB-HS."""

    def __init__(self):
        self._visa_manager = None

    def _visa(self):
        if self._visa_manager is None:
            self._visa_manager = pyvisa.ResourceManager()
        return self._visa_manager

    def _scan_gpib(self):
        resources = []
        try:
            resource = NIUSBGPIBResource(0)
        except GpibError as exc:
            print(f"NI GPIB-USB-HS is not available: {exc}")
            return resources

        try:
            for address in _GPIB_SCAN_ADDRESSES:
                resource.address = address
                try:
                    resource.query("*IDN?")
                except GpibError:
                    continue
                resources.append(f"GPIB0::{address}::INSTR")
        finally:
            resource.close()
        return resources

    def list_resources(self):
        resources = tuple(self._visa().list_resources())
        if not use_niusb_gpib():
            return resources
        visa_resources = tuple(
            name for name in resources if gpib_address(name) is None
        )
        return visa_resources + tuple(self._scan_gpib())

    def open_resource(self, resource_name, **options):
        address = gpib_address(resource_name)
        if address is not None and use_niusb_gpib():
            return NIUSBGPIBResource(address)
        return self._visa().open_resource(resource_name, **options)

    def close(self):
        if self._visa_manager is not None:
            self._visa_manager.close()
            self._visa_manager = None
