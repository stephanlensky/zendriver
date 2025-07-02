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

        return key.value

    @dataclass
    class Action:
        """Represents a key action with all necessary properties."""

        @dataclass
        class CharAction:
            text: str

        @dataclass
        class OtherAction:
            modifiers: int
            key: str
            code: str
            windows_virtual_key_code: int
            native_virtual_key_code: int
            text: str

        type_: KeyEventType
        payload: Union[CharAction, OtherAction]

        @classmethod
        def get_char_action(cls, key: str):
            return KeyEvents.Action(KeyEventType.CHAR, cls.CharAction(text=key))

        @staticmethod
        def get_otherAction_data(key: Union[str, SpecialKeys], modifiers: KeyModifiers) -> Tuple[int, str, str, int, int, str]:

            code, keyCode = KeyEvents.code_keyCode_lookup(key)
            if isinstance(key, str) and not key in "\n\r\t":
                if modifiers != KeyModifiers.Shift:
                    return modifiers.value, key, code, keyCode, keyCode, key
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

                return modifiers.value, key, code, keyCode, keyCode, key
            else:
                return modifiers.value, code, code, keyCode, keyCode, code

        @classmethod
        def get_non_char_action(
            cls,
            key: Union[str, SpecialKeys],
            modifiers: KeyModifiers,
            event_type: KeyEventType,
        ):
            return KeyEvents.Action(
                event_type, cls.OtherAction(*cls.get_otherAction_data(key, modifiers))
            )

        def to_dict(self):
            """Convert the action to a dictionary for CDP."""
            # Handle simple character actions
            if isinstance(self.payload, self.CharAction):
                return [asdict(self.payload)]

            if self.type_ in (KeyEventType.KEY_DOWN, KeyEventType.RAW_KEY_DOWN, KeyEventType.KEY_UP):
                raise NotImplementedError()

            return self._create_key_sequence()

        def _create_key_sequence(self) -> List[Dict]:
            """Create key down/up sequence with optional modifier keys."""
            events = []
            
            # Type guard - this method should only be called with OtherAction
            if not isinstance(self.payload, self.OtherAction):
                raise ValueError("_create_key_sequence can only be called with OtherAction payload")
            
            other_payload = self.payload  # Now type checker knows this is OtherAction
            
            # Add modifier key down if needed
            if other_payload.modifiers != KeyModifiers.Default:
                modifier_key = self._get_modifier_key(KeyModifiers(other_payload.modifiers))
                modifier_down = self._create_modifier_action(modifier_key, True)
                events.append({"type_": KeyEventType.KEY_DOWN.value, **asdict(modifier_down)})
            
            # Add main key down
            events.append({"type_": KeyEventType.KEY_DOWN.value, **asdict(other_payload)})
            
            
            # Add modifier key up if needed
            if other_payload.modifiers != KeyModifiers.Default:
                modifier_key = self._get_modifier_key(KeyModifiers(other_payload.modifiers))
                modifier_up = self._create_modifier_action(modifier_key, False)
                events.append({"type_": KeyEventType.KEY_UP.value, **asdict(modifier_up)})

            # Add main key up
            events.append({"type_": KeyEventType.KEY_UP.value, **asdict(other_payload)})
            
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

        def _create_modifier_action(self, modifier_key: SpecialKeys, is_pressed: bool) -> 'OtherAction':
            """Create a modifier key action."""
            modifier_value = KeyModifiers.Default if not is_pressed else self._get_modifier_enum_from_key(modifier_key)
            return self.OtherAction(*self.get_otherAction_data(modifier_key, modifier_value))

        def _get_modifier_enum_from_key(self, modifier_key: SpecialKeys) -> KeyModifiers:
            """Get KeyModifiers enum from SpecialKeys."""
            key_to_modifier = {
                SpecialKeys.ALT: KeyModifiers.Alt,
                SpecialKeys.CTRL: KeyModifiers.Ctrl,
                SpecialKeys.SHIFT: KeyModifiers.Shift,
                SpecialKeys.META: KeyModifiers.Meta,
            }
            return key_to_modifier[modifier_key]

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
