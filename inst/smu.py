"""SMU driver selection independent of the instrument connection backend."""

from .Keithley2400 import Keithley2400
from .Keithley2470 import Keithley2470
from .backend import query_identity
from .instbase import InstError


SMU_DRIVERS = (Keithley2400, Keithley2470)


def smu_driver_for_identity(identity):
    """Return the supported SMU driver class matching an ``*IDN?`` reply."""
    normalized_identity = identity.upper()
    if "MODEL 2470" in normalized_identity:
        return Keithley2470
    if (
        "MODEL 2400" in normalized_identity
        or "MODEL 2410" in normalized_identity
    ):
        return Keithley2400
    raise InstError(f"Unsupported SMU: {identity.strip()}")


def identify_smu(resource_name, backend=None):
    """Identify a supported SMU without retaining a connection."""
    resource_text = str(resource_name)
    if resource_text.upper().startswith("ASRL") or "ttyUSB" in resource_text:
        read_terminations = ("\r", "\n")
    else:
        read_terminations = (None,)

    identity = None
    last_error = None
    for read_termination in read_terminations:
        try:
            identity = query_identity(
                resource_name,
                read_termination=read_termination,
                backend=backend,
            )
            break
        except Exception as exc:
            last_error = exc

    if identity is None:
        raise InstError(
            f"No *IDN? response from {resource_name}: {last_error}"
        ) from last_error

    driver = smu_driver_for_identity(identity)()
    driver.found_idn = identity
    return driver


def open_smu(resource_name, backend=None):
    """Identify and open a supported SMU at a VISA-style resource name."""
    driver = identify_smu(resource_name, backend=backend)
    driver.open(resource_name, backend=backend)
    return driver
