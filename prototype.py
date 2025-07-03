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


class KeyPressEvent(StrEnum):
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


class KeyEvents:
    """
    Enum for key modifiers.
    https://stackoverflow.com/a/79194672
    """

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

    @staticmethod
    def code_keyCode_lookup(key: Union[str, SpecialKeys]) -> Tuple[str, int]:

        if isinstance(key, str):
            if len(key) != 1:
                raise ValueError("Key must be a single ASCII character.")

            if key.isalpha():
                key = key.upper()
                return "Key" + key, ord(key)
            elif key.isdigit() or key in KeyEvents.num_shift:
                if key in KeyEvents.num_shift:
                    key = str(KeyEvents.num_shift.index(key))
                return "Digit" + key, ord(key)
            elif key in "\n\r":
                return SpecialKeys.ENTER.value
            elif key == "\t":
                return SpecialKeys.TAB.value
            elif key in KeyEvents.special_char_map.keys():
                return KeyEvents.special_char_map[key]

            return KeyEvents.special_char_map[KeyEvents.special_char_shift_map[key]]

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

        type_: KeyPressEvent
        text: str
        modifiers: Optional[KeyModifiers] = None
        key: Optional[str] = None
        code: Optional[str] = None
        windows_virtual_key_code: Optional[int] = None
        native_virtual_key_code: Optional[int] = None

        @classmethod
        def get_char_action(cls, key: str):
            return cls(KeyPressEvent.CHAR, key)

        @classmethod
        def get_non_char_action(
            cls,
            key: Union[str, SpecialKeys],
            modifiers: KeyModifiers,
            event_type: KeyPressEvent,
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
                        key = KeyEvents.num_shift[int(key)]
                    else:
                        for shift_key, _key in KeyEvents.special_char_shift_map.items():
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

        def to_dict_basic(self) -> List[Dict[str, Union[str, int]]]:
            """Convert the action to a dictionary for CDP."""
            # Handle simple character actions
            if self.modifiers == KeyModifiers.Default:
                return [asdict(self)]

            return [{**asdict(self), "type_": self.type_.value}]

        def to_dict_DOWN_UP(self, original_key: Union[str, SpecialKeys]) -> List[Dict[str, Union[str, int]]]:
            """Create key down/up sequence"""
            events: List[Dict[str, Union[str, int]]] = []
            if (
                self.modifiers is None
                or self.key is None
                or self.code is None
                or self.windows_virtual_key_code is None
                or self.native_virtual_key_code is None
            ):
                raise ValueError("Key action must have all properties set.")

            # Add modifier key down if needed
            if (
                self.modifiers != KeyModifiers.Default
                and not self.key in KeyModifiers._member_names_
            ):
                modifier_key = self._get_modifier_key(KeyModifiers(self.modifiers))
                modifier_down = self.get_non_char_action(
                    modifier_key,
                    self.modifiers,
                    KeyPressEvent.KEY_DOWN,
                ).to_dict_basic()
                events.extend(modifier_down)

            # Add main key down
            events.append({"type_": KeyPressEvent.KEY_DOWN.value, **asdict(self)})

            # Add modifier key up if needed
            if (
                self.modifiers != KeyModifiers.Default
                and not self.key in KeyModifiers._member_names_
            ):
                modifier_key = self._get_modifier_key(KeyModifiers(self.modifiers))
                modifier_up = self.get_non_char_action(
                    modifier_key,
                    KeyModifiers.Default,
                    KeyPressEvent.KEY_UP,
                ).to_dict_basic()
                events.extend(modifier_up)

            # Add main key up
            events.extend(
                self.get_non_char_action(
                    original_key, KeyModifiers.Default, KeyPressEvent.KEY_UP
                ).to_dict_basic()
            )

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

    def __init__(
        self,
        action: Action,
        key: Union[str, SpecialKeys],
        event_type: KeyPressEvent,
        modifiers: KeyModifiers,
    ) -> None:
        self.action = action
        self.key = key
        self.event_type = event_type
        self.modifiers = modifiers

    @classmethod
    def get_keyEvent(
        cls,
        key: Union[str, SpecialKeys],
        event_type: KeyPressEvent,
        modifiers: KeyModifiers = KeyModifiers.Default,
    ) -> "KeyEvents":

        if event_type == KeyPressEvent.CHAR and isinstance(key, str):
            return cls(
                KeyEvents.Action.get_char_action(key), key, event_type, modifiers
            )
        else:
            return cls(
                KeyEvents.Action.get_non_char_action(key, modifiers, event_type),
                key,
                event_type,
                modifiers,
            )


    def to_dict(self) -> List[Dict[str, Union[str, int]]]:
        """Convert the key event to a dictionary for CDP."""
        if self.event_type != KeyPressEvent.DOWN_AND_UP:
            return self.action.to_dict_basic()
        
        return self.action.to_dict_DOWN_UP(self.key)