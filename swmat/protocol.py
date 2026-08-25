import json

from swm_ctrl.websocket_client import parse_pin_tokens


class SwitchProtocolError(RuntimeError):
    """Raised when a switch controller returns an invalid response."""


def _pin_tokens(value):
    if isinstance(value, str):
        fields = value.split()
        return fields if len(fields) > 1 else (value,)
    if isinstance(value, int):
        return (value,)
    return tuple(value)


def normalize_command(data):
    """Return one canonical Pico JSON command from a dict or legacy text."""
    if isinstance(data, dict):
        command = dict(data)
    else:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        if not isinstance(data, str):
            raise TypeError("command must be a dict, JSON string, or command string")

        text = data.strip()
        if not text:
            raise ValueError("command is empty")

        if text.startswith("{"):
            command = json.loads(text)
            if not isinstance(command, dict):
                raise ValueError("JSON command must be an object")
        else:
            fields = text.split()
            cmd = fields[0].upper()
            args = fields[1:]
            if cmd in ("ON", "OFF"):
                if cmd == "OFF" and len(args) == 1 and args[0].lower() == "all":
                    command = {"cmd": "ALLOFF"}
                else:
                    command = {"cmd": cmd, "pins": args}
            elif cmd in ("PINSTAT", "PCFSTAT"):
                if len(args) != 1:
                    raise ValueError(f"{cmd} requires exactly one argument")
                command = {"cmd": cmd, "which": args[0]}
            elif cmd in ("ALLOFF", "PING"):
                if args:
                    raise ValueError(f"{cmd} does not accept arguments")
                command = {"cmd": cmd}
            else:
                raise ValueError(f"unsupported command: {cmd}")

    cmd = command.get("cmd")
    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("missing or invalid cmd")
    cmd = cmd.strip().upper()
    command["cmd"] = cmd

    if cmd in ("ON", "OFF"):
        if "pins" not in command:
            raise ValueError(f"{cmd} requires pins")
        command["pins"] = parse_pin_tokens(_pin_tokens(command["pins"]))
    elif cmd in ("PINSTAT", "PCFSTAT"):
        if "which" not in command:
            raise ValueError(f"{cmd} requires which")
        which = command["which"]
        if isinstance(which, str):
            which = which.strip()
            if which.upper() == "ALL":
                which = "ALL"
            else:
                try:
                    which = int(which)
                except ValueError as exc:
                    raise ValueError(f"invalid {cmd} target: {which}") from exc
        if which != "ALL" and (
            isinstance(which, bool)
            or not isinstance(which, int)
            or not 0 <= which <= 15
        ):
            raise ValueError(f"invalid {cmd} target: {which}")
        command["which"] = which

    return command


def validate_response(response, expected_cmd):
    """Validate a response against the common Pico response envelope."""
    if not isinstance(response, dict):
        raise SwitchProtocolError(f"response is not a JSON object: {response!r}")
    if response.get("ok") != 1:
        raise SwitchProtocolError(f"switch command failed: {response}")
    if response.get("cmd") != expected_cmd:
        raise SwitchProtocolError(
            f"unexpected response command: expected {expected_cmd}, "
            f"got {response.get('cmd')}, response={response}"
        )
    return response
