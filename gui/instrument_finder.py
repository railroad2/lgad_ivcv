from PySide6.QtCore import QObject, Signal, Slot

from ..inst import Keithley2400, Keithley6487, WayneKerr4300


INSTRUMENT_FACTORIES = {
    "smu": Keithley2400,
    "pau": Keithley6487,
    "lcr": WayneKerr4300,
}


class InstrumentFinder(QObject):
    """Run blocking VISA discovery outside the GUI thread."""

    found = Signal(str)
    not_found = Signal()
    failed = Signal(str)
    finished = Signal()

    def __init__(self, instrument_type, parent=None):
        super().__init__(parent)
        self.instrument_type = instrument_type

    @Slot()
    def run(self):
        try:
            factory = INSTRUMENT_FACTORIES[self.instrument_type]
            resource = factory().find_inst()
            if resource:
                self.found.emit(str(resource))
            else:
                self.not_found.emit()
        except Exception as exc:
            self.failed.emit(str(exc) or type(exc).__name__)
        finally:
            self.finished.emit()
