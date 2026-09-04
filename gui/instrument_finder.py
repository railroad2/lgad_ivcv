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

    def __init__(self, instrument_type, parent=None):
        super().__init__(parent)
        self.instrument_type = instrument_type

    def run(self):
        try:
            factories = INSTRUMENT_FACTORIES[self.instrument_type]
            if not isinstance(factories, (tuple, list)):
                factories = (factories,)

            for factory in factories:
                instrument = factory()
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
