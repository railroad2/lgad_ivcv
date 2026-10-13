"""Instrument backend selection for VISA serial and NI GPIB-USB-HS."""

import importlib
import re

import pyvisa


GPIB_RESOURCE_PATTERN = re.compile(
    r"^GPIB(?P<board>\d+)::(?P<address>\d+)::INSTR$",
    re.IGNORECASE,
)
GPIB_PRIMARY_ADDRESSES = range(1, 31)


class InstrumentBackendError(RuntimeError):
    """Raised when an instrument communication backend cannot be opened."""


def parse_gpib_resource(resource_name):
    """Return ``(board, primary_address)`` for a VISA-style GPIB name."""
    match = GPIB_RESOURCE_PATTERN.fullmatch(str(resource_name).strip())
    if match is None:
        return None

    board = int(match.group("board"))
    address = int(match.group("address"))
    if board != 0:
        raise ValueError("NI GPIB-USB-HS supports GPIB0 resources only")
    if address not in GPIB_PRIMARY_ADDRESSES:
        raise ValueError("GPIB primary address must be between 1 and 30")
    return board, address


def _load_ni_gpib_controller():
    try:
        module = importlib.import_module("ni_gpib_usb_hs")
    except ImportError as exc:
        raise InstrumentBackendError(
            "NI GPIB-USB-HS support requires the ni_gpib_usb_hs module"
        ) from exc
    return module.NIUSBGPIB


class NIGPIBResource:
    """VISA-like resource facade over a shared ``NIUSBGPIB`` controller."""

    def __init__(
        self,
        controller,
        address,
        read_termination=None,
        write_termination=None,
    ):
        self.controller = controller
        self.address = address
        self.read_termination = read_termination
        self.write_termination = write_termination
        self.timeout = None

    def write(self, command):
        return self.controller.write(self.address, command)

    def query(self, command):
        return self.controller.query(self.address, command)

    def close(self):
        # InstrumentBackend owns the shared USB controller.
        return None


class InstrumentBackend:
    """Open GPIB through NI GPIB-USB-HS and other resources through PyVISA."""

    def __init__(
        self,
        visa_manager_factory=None,
        gpib_controller_factory=None,
    ):
        self._visa_manager_factory = (
            visa_manager_factory or pyvisa.ResourceManager
        )
        self._gpib_controller_factory = gpib_controller_factory
        self._visa_manager = None
        self._gpib_controller = None
        self._closed = False

    def _get_visa_manager(self):
        if self._visa_manager is None:
            self._visa_manager = self._visa_manager_factory()
        return self._visa_manager

    def _get_gpib_controller(self):
        if self._gpib_controller is None:
            factory = self._gpib_controller_factory
            if factory is None:
                factory = _load_ni_gpib_controller()
            self._gpib_controller = factory()
        return self._gpib_controller

    def open_resource(self, resource_name, **options):
        gpib_address = parse_gpib_resource(resource_name)
        if gpib_address is not None:
            _, address = gpib_address
            return NIGPIBResource(
                self._get_gpib_controller(),
                address,
                read_termination=options.get("read_termination"),
                write_termination=options.get("write_termination"),
            )
        return self._get_visa_manager().open_resource(resource_name, **options)

    def list_resources(self):
        """List serial VISA resources and NI GPIB primary addresses."""
        resources = []
        try:
            visa_resources = self._get_visa_manager().list_resources()
        except Exception:
            visa_resources = ()

        for resource in visa_resources:
            # GPIB access on this branch always goes through NIUSBGPIB.
            if GPIB_RESOURCE_PATTERN.fullmatch(str(resource).strip()):
                continue
            resources.append(str(resource))

        try:
            self._get_gpib_controller()
        except InstrumentBackendError:
            pass
        else:
            resources.extend(
                f"GPIB0::{address}::INSTR"
                for address in GPIB_PRIMARY_ADDRESSES
            )
        return tuple(resources)

    def close(self):
        if self._closed:
            return
        self._closed = True

        errors = []
        if self._gpib_controller is not None:
            try:
                self._gpib_controller.close()
            except Exception as exc:
                errors.append(exc)
            finally:
                self._gpib_controller = None

        if self._visa_manager is not None:
            try:
                self._visa_manager.close()
            except Exception as exc:
                errors.append(exc)
            finally:
                self._visa_manager = None

        if errors:
            raise errors[0]


def query_identity(resource_name, read_termination=None):
    """Query ``*IDN?`` using the backend selected for *resource_name*."""
    backend = InstrumentBackend()
    resource = None
    try:
        options = {}
        if read_termination is not None:
            options["read_termination"] = read_termination
        resource = backend.open_resource(resource_name, **options)
        return resource.query("*IDN?").strip()
    finally:
        try:
            if resource is not None:
                resource.close()
        finally:
            backend.close()
