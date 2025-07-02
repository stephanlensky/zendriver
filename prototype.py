from enum import Enum, IntEnum, StrEnum
from dataclasses import dataclass, asdict
from typing import Union, Dict, Tuple, Optional


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

    __SHIFT__ = ("Shift", 16)
    "internal use only"
    __ALT__ = ("Alt", 18)
    "internal use only"
    __CTRL__ = ("Control", 17)
    "internal use only"


class KeyEventType(StrEnum):
    KEY_DOWN = "keyDown"
    KEY_UP = "keyUp"
    RAW_KEY_DOWN = "rawKeyDown"

    CHAR = "char"
    "sends a keyDown and keyUp event for an ASCII character"

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


def get_special_char_code_and_keyCode(
    key: str, keyCodeDict: Dict[str, str], start_index: int
) -> Tuple[str, int]:
    cur_index = list(keyCodeDict.keys()).index(key) // 2
    return keyCodeDict[key], start_index + cur_index


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

        return key.value

    @dataclass
    class Action:
        """Represents a key action with all necessary properties."""

        @dataclass
        class BaseAction:
            type_: KeyEventType
            modifiers: int

        @dataclass
        class CharAction(BaseAction):
            text: str

        @dataclass
        class OtherAction(BaseAction):
            key: str
            code: str
            windows_virtual_key_code: int
            native_virtual_key_code: int
            text: Optional[str] = None

        payload: Union[CharAction, OtherAction]

        @classmethod
        def get_char_action(cls, key: str, modifiers: KeyModifiers):
            return KeyEvents.Action(
                cls.CharAction(type_=KeyEventType.CHAR, modifiers=modifiers, text=key)
            )

        @staticmethod
        def get_otherAction_data(key: Union[str, SpecialKeys], modifiers: KeyModifiers) :

            code, keyCode = KeyEvents.code_keyCode_lookup(key)
            if isinstance(key, str) and not key in "\n\r\t":   
                if modifiers != KeyModifiers.Shift:
                    return key, code, keyCode, keyCode, key
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

                return key, code, keyCode, keyCode, key
            else:
                return code, code, keyCode, keyCode, code

        @classmethod
        def get_non_char_action(
            cls,
            key: Union[str, SpecialKeys],
            modifiers: KeyModifiers,
            event_type: KeyEventType,
        ):
            return KeyEvents.Action(
                cls.OtherAction(
                    event_type,
                    modifiers,
                    *cls.get_otherAction_data(key, modifiers)
                )
            )

        def to_dict(self):
            """Convert the action to a dictionary for CDP."""
            if (
                isinstance(self.payload, self.OtherAction)
                and self.payload.type_ == KeyEventType.DOWN_AND_UP
            ):
                base_dict = {
                    "modifiers": self.payload.modifiers,
                    "key": self.payload.key,
                    "code": self.payload.code,
                    "windowsVirtualKeyCode": self.payload.windows_virtual_key_code,
                    "nativeVirtualKeyCode": self.payload.native_virtual_key_code,
                    "text": self.payload.text,
                }
                return [
                    asdict(self.OtherAction(type_=KeyEventType.KEY_DOWN, **base_dict)),
                    asdict(self.OtherAction(type_=KeyEventType.KEY_UP, **base_dict)),
                ]
            else:
                return [asdict(self.payload)]

    @staticmethod
    def get_key_action(
        key: Union[str, SpecialKeys],
        event_type: KeyEventType,
        modifiers: KeyModifiers = KeyModifiers.Default,
    ) -> Action:

        if event_type == KeyEventType.CHAR and isinstance(key, str):
            return KeyEvents.Action.get_char_action(key, modifiers)
        else:
            return KeyEvents.Action.get_non_char_action(key, modifiers, event_type)
