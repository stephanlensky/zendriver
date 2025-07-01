from enum import Enum, IntEnum, StrEnum
from dataclasses import dataclass, asdict
from typing import Union, Dict, Tuple, List, Optional, TypedDict


class KeyModifiers(IntEnum):

    Default = 0
    Alt = 1
    Ctrl = 2
    Meta = 4
    Shift = 8


class SpecialKeys(Enum):
    ENTER = ("Enter", 13)
    BACKSPACE = ("Backspace", 8)
    ESCAPE = ("Escape", 27)
    DELETE = ("Delete", 46)
    ARROW_LEFT = ("ArrowLeft", 37)
    ARROW_UP = ("ArrowUp", 38)
    ARROW_RIGHT = ("ArrowRight", 39)
    ARROW_DOWN = ("ArrowDown", 40)


class KeyEventType(StrEnum):
    KEY_DOWN = "keyDown"
    KEY_UP = "keyUp"
    RAW_KEY_DOWN = "rawKeyDown"

    CHAR = "char"
    "sends a keyDown and keyUp event for an ASCII character"

    DOWN_AND_UP = "downAndUp"
    """Way to give both key down and up events in one go for non-ASCII characters, 
    
    `not standard implementation`"""


num_shift = ")!@#$%^&*("

special_char_1 = {
    ";": "Semicolon",
    ":": "Semicolon",
    "=": "Equal",
    "+": "Equal",
    ",": "Comma",
    "<": "Comma",
    "-": "Minus",
    "_": "Minus",
    ".": "Period",
    ">": "Period",
    "/": "Slash",
    "?": "Slash",
    "`": "Backquote",
    "~": "Backquote",
}

special_char_2 = {
    "[": "BracketLeft",
    "{": "BracketLeft",
    "\\": "Backslash",
    "|": "Backslash",
    "]": "BracketRight",
    "}": "BracketRight",
    "'": "Quote",
    '"': "Quote",
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
    def get_key_code_and_keyCode(key: Union[str, SpecialKeys]) -> Tuple[str, str, int]:
        if key is None or (isinstance(key, str) and len(key) != 1):
            raise ValueError("Key must be a single ASCII character.")

        if isinstance(key, SpecialKeys):
            return key.value[0], key.value[0], key.value[1]
        elif key.isalpha():
            return key.lower(), "Key" + key.upper(), ord(key.upper())
        elif key.isdigit() or key in num_shift:
            if key in num_shift:
                key = str(num_shift.index(key))
            return key, "Digit" + key, ord(key)
        
        
        lookup_dict: Optional[Dict[str, str]] = None
        startIndex: Optional[int] = None
        
        if key in special_char_1.keys():
            lookup_dict = special_char_1
            startIndex = 186
            
        elif key in special_char_2.keys():
            lookup_dict = special_char_2
            startIndex = 219
        else:
            raise ValueError(f"Key '{key}' is not a key event")

        data = get_special_char_code_and_keyCode(
            key, lookup_dict, startIndex
        )

        return data[0], data[0], data[1]

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
            

        payload: Union[CharAction, OtherAction]

        @classmethod
        def get_char_action(cls, key: str, modifiers: KeyModifiers):
            return KeyEvents.Action(
                cls.CharAction(type_=KeyEventType.CHAR, modifiers=modifiers, text=key)
            )

        @classmethod
        def get_non_char_action(
            cls,
            key: Union[str, SpecialKeys],
            modifiers: KeyModifiers,
            event_type: KeyEventType,
        ):
            key_, code, keyCode = KeyEvents.get_key_code_and_keyCode(key)
            return KeyEvents.Action(
                cls.OtherAction(
                    type_=event_type,
                    modifiers=modifiers,
                    key=key_,
                    code=code,
                    windows_virtual_key_code=keyCode,
                    native_virtual_key_code=keyCode,
                )
            )

        def to_dict(self) :
            """Convert the action to a dictionary for CDP."""
            if isinstance(self.payload, self.OtherAction) and self.payload.type_ == KeyEventType.DOWN_AND_UP:
                return [
                    asdict(self.OtherAction(
                        type_=KeyEventType.KEY_DOWN,
                        modifiers=self.payload.modifiers,
                        key=self.payload.key,
                        code=self.payload.code,
                        windows_virtual_key_code=self.payload.windows_virtual_key_code,
                        native_virtual_key_code=self.payload.native_virtual_key_code,
                    )),
                    asdict(self.OtherAction(
                        type_=KeyEventType.KEY_UP,
                        modifiers=self.payload.modifiers,
                        key=self.payload.key,
                        code=self.payload.code,
                        windows_virtual_key_code=self.payload.windows_virtual_key_code,
                        native_virtual_key_code=self.payload.native_virtual_key_code,
                    ))
                ]
            else:
                return [asdict(self.payload)]

    @staticmethod
    def get_key_action(
        key: Union[str, SpecialKeys],
        modifiers: KeyModifiers = KeyModifiers.Default,
        event_type: KeyEventType = KeyEventType.CHAR,
    ) -> Optional[Action]:

        if event_type == KeyEventType.CHAR and isinstance(key, str):
            return KeyEvents.Action.get_char_action(key, modifiers)
        else:
            return KeyEvents.Action.get_non_char_action(key, modifiers, event_type)
