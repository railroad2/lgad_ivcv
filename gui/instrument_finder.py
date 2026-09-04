import pyvisa

from PySide6.QtCore import QThread, Signal

from ..inst import Keithley2400, Keithley2470, Keithley6487, WayneKerr4300


INSTRUMENT_FACTORIES = {
    "smu": (Keithley2400, Keithley2470),
    "pau": Keithley6487,
    "lcr": WayneKerr4300,
}


class InstrumentFinder(QThread):
    """Run blocking VISA discovery outside the GUI thread."""

    found = Signal(str, str)
    not_found = Signal()
    failed = Signal(str)

    def __init__(self, instrument_type, parent=None, preferred_resource=None):
        super().__init__(parent)
        self.instrument_type = instrument_type
        self.preferred_resource = preferred_resource

    @staticmethod
    def _factory_list(factories):
        if isinstance(factories, (tuple, list)):
            return tuple(factories)
        return (factories,)

    @staticmethod
    def _matches_identity(instrument, identity):
        messages = getattr(instrument, "_verify_msg", ())
        if isinstance(messages, str):
            messages = (messages,)
        return any(message in identity for message in messages)

    @staticmethod
    def _query_identity(resource_name, read_termination):
        manager = pyvisa.ResourceManager()
        resource = None
        try:
            resource = manager.open_resource(
                resource_name,
                read_termination=read_termination,
            )
            return resource.query("*IDN?").strip()
        finally:
            if resource is not None:
                resource.close()
            manager.close()

    def _check_preferred_resource(self, instruments):
        if not self.preferred_resource:
            return None

        attempted_terminations = set()
        for instrument in instruments:
            read_termination = getattr(instrument, "_read_termination", None)
            if read_termination in attempted_terminations:
                continue
            attempted_terminations.add(read_termination)
            try:
                identity = self._query_identity(
                    self.preferred_resource,
                    read_termination,
                )
            except Exception:
                continue

            if any(
                self._matches_identity(candidate, identity)
                for candidate in instruments
            ):
                return self.preferred_resource, identity
            return None

        return None

    def run(self):
        try:
            factories = INSTRUMENT_FACTORIES[self.instrument_type]
            factories = self._factory_list(factories)
            instruments = [factory() for factory in factories]

            preferred = self._check_preferred_resource(instruments)
            if preferred is not None:
                self.found.emit(*preferred)
                return

            for instrument in instruments:
                resource = instrument.find_inst()
                if resource:
                    self.found.emit(
                        str(resource),
                        str(getattr(instrument, "found_idn", "") or ""),
                    )
                    return

            self.not_found.emit()
        except Exception as exc:
            self.failed.emit(str(exc) or type(exc).__name__)
