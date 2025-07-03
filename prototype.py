from enum import Enum, IntEnum, StrEnum
from dataclasses import dataclass, asdict
from typing import Union, Dict, Tuple, Optional, List


class KeyModifiers(IntEnum):
    Default = 0
    Alt = 1
    Ctrl = 2
    Meta = 4
    Shift = 8


class SpecialKeys(Enum):
    ENTER = ("Enter", 13)
    TAB = ("Tab", 9)
    BACKSPACE = ("Backspace", 8)
    ESCAPE = ("Escape", 27)
    DELETE = ("Delete", 46)
    ARROW_LEFT = ("ArrowLeft", 37)
    ARROW_UP = ("ArrowUp", 38)
    ARROW_RIGHT = ("ArrowRight", 39)
    ARROW_DOWN = ("ArrowDown", 40)

    SHIFT = ("Shift", 16)  # internal use only
    ALT = ("Alt", 18)  # internal use only
    CTRL = ("Control", 17)  # internal use only
    META = ("Meta", 91)  # internal use only


class KeyEventType(StrEnum):
    KEY_DOWN = "keyDown"
    KEY_UP = "keyUp"
    RAW_KEY_DOWN = "rawKeyDown"
    # not sure if any of the above are useful

    CHAR = "char"
    """directly sends ASCII character to the element
    
    Cannot send non-ASCII characters and commands (Ctrl+A, etc.)
    """

    DOWN_AND_UP = "downAndUp"
    """Way to give both key down and up events in one go for non-ASCII characters, 
    **not standard implementation**"""


num_shift = ")!@#$%^&*("

special_char_map = {
    ";": ("Semicolon", 186),
    "=": ("Equal", 187),
    ",": ("Comma", 188),
    "-": ("Minus", 189),
    ".": ("Period", 190),
    "/": ("Slash", 191),
    "`": ("Backquote", 192),
    "[": ("BracketLeft", 219),
    "\\": ("Backslash", 220),
    "]": ("BracketRight", 221),
    "'": ("Quote", 222),
}

special_char_shift_map = {
    ":": ";",
    "=": "+",
    "<": ",",
    "_": "-",
    ">": ".",
    "?": "/",
    "~": "`",
    "{": "[",
    "|": "\\",
    "}": "]",
    '"': "'",
}


class KeyEvents:
    """
    Enum for key modifiers.
    https://stackoverflow.com/a/79194672
    """

    @staticmethod
    def code_keyCode_lookup(key: Union[str, SpecialKeys]) -> Tuple[str, int]:

        if isinstance(key, str):
            if len(key) != 1:
                raise ValueError("Key must be a single ASCII character.")

            if key.isalpha():
                key = key.upper()
                return "Key" + key, ord(key)
            elif key.isdigit() or key in num_shift:
                if key in num_shift:
                    key = str(num_shift.index(key))
                return "Digit" + key, ord(key)
            elif key in "\n\r":
                return SpecialKeys.ENTER.value
            elif key == "\t":
                return SpecialKeys.TAB.value
            elif key in special_char_map.keys():
                return special_char_map[key]

            return special_char_map[special_char_shift_map[key]]

        if key in [
            SpecialKeys.SHIFT,
            SpecialKeys.ALT,
            SpecialKeys.CTRL,
            SpecialKeys.META,
        ]:
            values = key.value
            return key.value[0] + "Left", values[1]

        return key.value

    @dataclass
    class Action:
        """Represents a key action with all necessary properties."""

        type_: KeyEventType
        text: str
        modifiers: Optional[KeyModifiers] = None
        key: Optional[str] = None
        code: Optional[str] = None
        windows_virtual_key_code: Optional[int] = None
        native_virtual_key_code: Optional[int] = None

        @classmethod
        def get_char_action(cls, key: str):
            return cls(KeyEventType.CHAR, key)

        @classmethod
        def get_non_char_action(
            cls,
            key: Union[str, SpecialKeys],
            modifiers: KeyModifiers,
            event_type: KeyEventType,
        ):
            return cls(event_type, *cls.get_keyPress_action_data(key, modifiers))

        @staticmethod
        def get_keyPress_action_data(
            key: Union[str, SpecialKeys], modifiers: KeyModifiers
        ) -> Tuple[str, KeyModifiers, str, str, int, int]:
            # text, modifiers, key, code, keyCode, keyCode

            code, keyCode = KeyEvents.code_keyCode_lookup(key)
            if isinstance(key, str) and not key in "\n\r\t":
                if modifiers != KeyModifiers.Shift:
                    return key, modifiers, key, code, keyCode, keyCode
                else:
                    if key.isalpha():
                        key = key.upper()
                    elif key.isdigit():
                        key = num_shift[int(key)]
                    else:
                        for shift_key, _key in special_char_shift_map.items():
                            if key != _key:
                                continue
                            key = shift_key
                            break
                return key, modifiers, key, code, keyCode, keyCode

            if key in [
                SpecialKeys.SHIFT,
                SpecialKeys.ALT,
                SpecialKeys.CTRL,
                SpecialKeys.META,
            ]:
                key_vals = key.value
                return key_vals[0], modifiers, key_vals[0], code, keyCode, keyCode

            return code, modifiers, code, code, keyCode, keyCode

        def to_dict(self) -> List[Dict[str, Union[str, int]]]:
            """Convert the action to a dictionary for CDP."""
            # Handle simple character actions
            if self.modifiers == KeyModifiers.Default:
                return [asdict(self)]

            if self.type_ in (
                KeyEventType.KEY_DOWN,
                KeyEventType.RAW_KEY_DOWN,
                KeyEventType.KEY_UP,
            ):
                return [{**asdict(self), "type_": self.type_.value}]

            return self._create_key_sequence()

        def _create_key_sequence(self) -> List[Dict[str, Union[str, int]]]:
            """Create key down/up sequence with optional modifier keys."""
            events: List[Dict[str, Union[str, int]]] = []

            # Add modifier key down if needed
            if self.modifiers != KeyModifiers.Default:
                modifier_key = self._get_modifier_key(KeyModifiers(self.modifiers))
                modifier_down = self.get_non_char_action(
                    modifier_key,
                    self.modifiers if self.modifiers else KeyModifiers.Default,
                    KeyEventType.KEY_DOWN,
                ).to_dict()
                events.extend(modifier_down)

            # Add main key down
            events.append({"type_": KeyEventType.KEY_DOWN.value, **asdict(self)})

            # Add modifier key up if needed
            if self.modifiers != KeyModifiers.Default:
                modifier_key = self._get_modifier_key(KeyModifiers(self.modifiers))
                modifier_up = self.get_non_char_action(
                    modifier_key,
                    KeyModifiers.Default,
                    KeyEventType.KEY_UP,
                ).to_dict()
                events.extend(modifier_up)

            # Add main key up
            events.append({"type_": KeyEventType.KEY_UP.value, **asdict(self)})

            return events

        def _get_modifier_key(self, modifier: KeyModifiers) -> SpecialKeys:
            """Get the SpecialKey for a modifier."""
            modifier_map = {
                KeyModifiers.Alt: SpecialKeys.ALT,
                KeyModifiers.Ctrl: SpecialKeys.CTRL,
                KeyModifiers.Shift: SpecialKeys.SHIFT,
                KeyModifiers.Meta: SpecialKeys.META,
            }
            if modifier not in modifier_map:
                raise ValueError(f"Invalid key modifier: {modifier}")
            return modifier_map[modifier]

    @staticmethod
    def get_key_action(
        key: Union[str, SpecialKeys],
        event_type: KeyEventType,
        modifiers: KeyModifiers = KeyModifiers.Default,
    ) -> Action:

        if event_type == KeyEventType.CHAR and isinstance(key, str):
            return KeyEvents.Action.get_char_action(key)
        else:
            return KeyEvents.Action.get_non_char_action(key, modifiers, event_type)
