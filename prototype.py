from enum import Enum, IntEnum, StrEnum
from dataclasses import dataclass, asdict
from typing import Union, Dict, Tuple, Optional, List
import emoji
import emoji.unicode_codes
import time
import random

class KeyModifiers(IntEnum):
    """Enumeration of keyboard modifiers used in key events.
    For multiple modifiers, use bitwise OR to combine them.

       Example:
        >>> modifiers = KeyModifiers.Alt | KeyModifiers.Shift # Combines Alt and Shift modifiers
    """

    Default = 0
    Alt = 1
    Ctrl = 2
    Meta = 4
    Shift = 8


class SpecialKeys(Enum):
    """Enumeration of special keys with their corresponding names and key codes."""

    SPACE = (" ", 32)  # space key
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
    """Enumeration of different types of key press events."""

    KEY_DOWN = "keyDown"
    KEY_UP = "keyUp"
    RAW_KEY_DOWN = "rawKeyDown"

    CHAR = "char"
    """Directly sends ASCII character to the element. Cannot send non-ASCII characters and commands (Ctrl+A, etc.)"""
    DOWN_AND_UP = "downAndUp"
    """Way to give both key down and up events in one go for non-ASCII characters, **not standard implementation**"""


class KeyEvents:
    """
    Key events handling class for processing keyboard input and converting to CDP format.

    This class manages keyboard events and converts them into appropriate CDP commands.
    It handles ASCII characters, special keys, and modifier combinations.

    Reference: https://stackoverflow.com/a/79194672
    """

    # Class constants for character mappings
    NUM_SHIFT = ")!@#$%^&*("

    SPECIAL_CHAR_MAP = {
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

    SPECIAL_CHAR_SHIFT_MAP = {
        ":": ";",
        "+": "=",
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

    SPECIAL_CHAR_REVERSE_MAP = {v: k for k, v in SPECIAL_CHAR_SHIFT_MAP.items()}

    MODIFIER_KEYS = [
        SpecialKeys.SHIFT,
        SpecialKeys.ALT,
        SpecialKeys.CTRL,
        SpecialKeys.META,
    ]

    def __init__(
        self,
        key: Union[str, SpecialKeys],
        key_press_event: KeyPressEvent,
        modifiers: Union[KeyModifiers, int] = KeyModifiers.Default, timing_ms: int=0
    ):
        """
        Initialize a KeyEvents instance.

        Args:
            key: The key to be processed (single character string or SpecialKeys enum)
            key_press_event: The type of key press event to generate (Currently supported are `DOWN_AND_UP` and `CHAR`)
            modifiers: Modifier keys to be applied (can be combined with bitwise OR)
        """
        if isinstance(key, str) and emoji.is_emoji(key):
            key_press_event = KeyPressEvent.CHAR
        
        self.key_press_event = key_press_event
        self.modifiers = modifiers
        self.key = (
            key if key_press_event == KeyPressEvent.CHAR else self._normalise_key(key)
        )

        self.action: KeyEvents.Action = self._create_action()
        self.timing_ms = timing_ms

    def conv_to_str(self, specialKey_key: SpecialKeys) -> str:
        if specialKey_key == SpecialKeys.SPACE:
            return " "
        elif specialKey_key == SpecialKeys.ENTER:
            return "\n"
        elif specialKey_key == SpecialKeys.TAB:
            return "\t"
        raise ValueError(
            f"Cannot convert {specialKey_key} to string, only SPACE, ENTER and TAB are supported."
        )

    def _create_action(self) -> "Action":
        """
        Create the appropriate action for this key event.

        Returns:
            Action object containing the processed key information

        Raises:
            ValueError: If key is invalid for CHAR event type
        """
        if self.key_press_event == KeyPressEvent.CHAR:
            if isinstance(self.key, SpecialKeys):
                self.key = self.conv_to_str(self.key)
            return KeyEvents.Action(self.key)

        return KeyEvents.Action.from_key_and_modifiers(self.key, self.modifiers)

    def _normalise_key(self, key: Union[str, SpecialKeys]) -> Union[str, SpecialKeys]:
        """
        Convert a shifted key to its non-shifted equivalent.

        Args:
            key: The key to convert (may be shifted)

        Returns:
            The non-shifted equivalent of the key

        Raises:
            ValueError: If the key is not recognized or supported
        """
        if isinstance(key, SpecialKeys):
            return key  # all the special keys dont have shifted variants
        
        self.modifiers |= KeyModifiers.Shift  # apply shift modifier for non-special keys
        
        if key in self.NUM_SHIFT:
            return str(self.NUM_SHIFT.index(key))
        elif key in self.SPECIAL_CHAR_SHIFT_MAP:
            return self.SPECIAL_CHAR_SHIFT_MAP[key]
        elif key.isalpha() and key.isupper():
            return key.lower()

        self.modifiers &= ~KeyModifiers.Shift  # remove shift modifier if not applicable        

        if key in "\n\r":
            return SpecialKeys.ENTER
        elif key == "\t":
            return SpecialKeys.TAB
        elif key == " ":
            return SpecialKeys.SPACE
        
        return key

    def to_cdp_events(self) -> List[Dict[str, Union[str, int]]]:
        """
        Convert the key event to CDP format.

        Returns:
            List of dictionaries containing CDP payload
        """
        if self.key_press_event != KeyPressEvent.DOWN_AND_UP:
            return self.action.to_basic_event(self.key_press_event, self.modifiers)

        return self.action.to_down_up_sequence(self.key, self.modifiers)
    
    def to_cdp_events_with_timing(self):
        """Return events with timing for realistic typing"""
        events = self.to_cdp_events()
        if self.timing_ms > 0:
            for i, event in enumerate(events):
                event['timestamp'] = time.time() + (i * self.timing_ms / 1000)
        return events

    def add_human_variation(self):
        """Add slight random variations to appear more human"""
        if self.timing_ms > 0:
            self.timing_ms = max(0, self.timing_ms + random.randint(-10, 10))

    @staticmethod
    def get_key_code_info(key: Union[str, SpecialKeys]) -> Tuple[str, int]:
        """
        Get the `code` and `keyCode` for a given key.

        Args:
            key: The key to look up (single character string or SpecialKeys enum)

        Returns:
            Tuple containing (`code`, `keyCode`) for the key

        Raises:
            ValueError: If the key is not supported or invalid
        """
        if isinstance(key, str):
            return KeyEvents._handle_string_key_lookup(key)
        return KeyEvents._handle_special_key_lookup(key)

    @staticmethod
    def _handle_string_key_lookup(key: str) -> Tuple[str, int]:
        """Handle string key lookup logic."""
        if len(key) != 1:
            raise ValueError("Key must be a single ASCII character.")

        if key.isalpha():
            return f"Key{key.upper()}", ord(key.upper())
        elif key.isdigit() or key in KeyEvents.NUM_SHIFT:
            digit = (
                str(KeyEvents.NUM_SHIFT.index(key))
                if key in KeyEvents.NUM_SHIFT
                else key
            )
            return f"Digit{digit}", ord(digit)
        elif key in "\n\r":
            return SpecialKeys.ENTER.value
        elif key == "\t":
            return SpecialKeys.TAB.value
        elif key in KeyEvents.SPECIAL_CHAR_MAP:
            return KeyEvents.SPECIAL_CHAR_MAP[key]
        elif key in KeyEvents.SPECIAL_CHAR_SHIFT_MAP.keys():
            return KeyEvents.SPECIAL_CHAR_MAP[KeyEvents.SPECIAL_CHAR_SHIFT_MAP[key]]

        raise ValueError(f"Unsupported key: '{key}'")

    @staticmethod
    def _handle_special_key_lookup(key: SpecialKeys) -> Tuple[str, int]:
        """Handle special key lookup logic."""
        if key in KeyEvents.MODIFIER_KEYS:
            return f"{key.value[0]}Left", key.value[1]
        return key.value

    @staticmethod
    def _extract_modifier_keys(
        modifiers: Union[KeyModifiers, int],
    ) -> List[Tuple[SpecialKeys, KeyModifiers]]:
        """
        Extract individual modifier keys from a modifier bitmask.

        Args:
            modifiers: The modifier bitmask to process

        Returns:
            List of tuples containing (SpecialKey, KeyModifier) pairs
        """
        if modifiers == KeyModifiers.Default:
            return []

        modifier_keys = []
        if modifiers & KeyModifiers.Alt:
            modifier_keys.append((SpecialKeys.ALT, KeyModifiers.Alt))
        if modifiers & KeyModifiers.Ctrl:
            modifier_keys.append((SpecialKeys.CTRL, KeyModifiers.Ctrl))
        if modifiers & KeyModifiers.Meta:
            modifier_keys.append((SpecialKeys.META, KeyModifiers.Meta))
        if modifiers & KeyModifiers.Shift:
            modifier_keys.append((SpecialKeys.SHIFT, KeyModifiers.Shift))

        if not modifier_keys:
            raise ValueError("No valid modifier keys found.")

        return modifier_keys

    @dataclass
    class Action:
        """
        Represents a key action with all necessary properties for CDP.

        This dataclass encapsulates all the information needed to send
        a key event through the Chrome DevTools Protocol.
        """

        text: str
        key: Optional[str] = None
        code: Optional[str] = None
        windows_virtual_key_code: Optional[int] = None
        native_virtual_key_code: Optional[int] = None

        @classmethod
        def from_key_and_modifiers(
            cls, key: Union[str, SpecialKeys], modifiers: Union[KeyModifiers, int]
        ) -> "KeyEvents.Action":
            """
            Create an Action instance from a key and modifiers.

            Args:
                key: The key to create an action for
                modifiers: Modifier keys to apply

            Returns:
                Action instance with appropriate properties set
            """
            return cls(*cls._build_action_data(key, modifiers))

        @staticmethod
        def _build_action_data(
            key: Union[str, SpecialKeys], modifiers: Union[KeyModifiers, int]
        ) -> Tuple[str, str, str, int, int]:
            """
            Build the data needed for a key press action.

            Args:
                key: The key to process
                modifiers: Modifier keys to apply

            Returns:
                Tuple containing (text, key, code, windowsVirtualKeyCode, nativeVirtualKeyCode)
            """
            code, key_code = KeyEvents.get_key_code_info(key)

            # Handle printable characters with potential shift modifier
            if isinstance(key, str) and key not in "\n\r\t":
                return KeyEvents.Action._handle_printable_char(
                    key, modifiers, code, key_code
                )

            # Handle modifier keys
            if isinstance(key, SpecialKeys) and key in KeyEvents.MODIFIER_KEYS:
                key_name = key.value[0]
                return key_name, key_name, code, key_code, key_code

            # Handle other special keys
            return code, code, code, key_code, key_code

        @staticmethod
        def _handle_printable_char(
            key: str, modifiers: Union[KeyModifiers, int], code: str, key_code: int
        ) -> Tuple[str, str, str, int, int]:
            """Handle printable character with potential shift modifier."""
            if modifiers != KeyModifiers.Shift:
                return key, key, code, key_code, key_code

            # Apply shift transformation
            if key.isalpha():
                shifted_key = key.upper()
            elif key.isdigit():
                shifted_key = KeyEvents.NUM_SHIFT[int(key)]
            else:
                shifted_key = KeyEvents.SPECIAL_CHAR_REVERSE_MAP.get(key, key)

            return shifted_key, shifted_key, code, key_code, key_code

        def to_basic_event(
            self,
            key_press_event: KeyPressEvent,
            modifiers: Union[KeyModifiers, int],
            key_override: Optional[str] = None,
        ) -> List[Dict[str, Union[str, int]]]:
            """
            Convert the action to a basic CDP event.

            Args:
                key_press_event: The type of key press event
                modifiers: Modifier keys to apply
                key_override: Optional key override for the event

            Returns:
                List containing a single dictionary with CDP event data
            """
            event_dict = asdict(self)
            event_dict["type_"] = key_press_event.value
            event_dict["modifiers"] = modifiers

            if key_override:
                event_dict["key"] = key_override
                event_dict["text"] = key_override

            return [event_dict]

        def to_down_up_sequence(
            self,
            original_key: Union[str, SpecialKeys],
            modifiers: Union[KeyModifiers, int],
        ) -> List[Dict[str, Union[str, int]]]:
            """
            Create a complete key down/up sequence with modifiers.

            This method generates a sequence of key events that properly handles
            modifier keys by sending modifier key down events before the main key,
            and modifier key up events after the main key.

            Args:
                original_key: The original key that was requested
                modifiers: Modifier keys to apply

            Returns:
                List of dictionaries containing the complete key event sequence

            Raises:
                ValueError: If the action doesn't have all required properties
            """
            # Validate that all required properties are set
            if not all(
                [
                    self.key,
                    self.code,
                    self.windows_virtual_key_code,
                    self.native_virtual_key_code,
                ]
            ):
                raise ValueError(
                    "Action must have all properties set for DOWN_AND_UP event."
                )

            events = []
            modifier_keys = KeyEvents._extract_modifier_keys(modifiers)
            modifier_key_names = [key.value[0] for key, _ in modifier_keys]
            is_modifier_key = self.key in modifier_key_names

            # 1: Add modifier key down events
            current_modifiers = 0
            for modifier_key, modifier_flag in modifier_keys:
                current_modifiers |= modifier_flag  # done like this since all the keys are not pressed or processed at once
                modifier_action = KeyEvents.Action.from_key_and_modifiers(
                    modifier_key, current_modifiers
                )
                events.extend(
                    modifier_action.to_basic_event(
                        KeyPressEvent.KEY_DOWN, current_modifiers
                    )
                )

            # 2: Add main key down (if itself is not a modifier key)
            if not is_modifier_key:
                events.extend(
                    self.to_basic_event(KeyPressEvent.KEY_DOWN, current_modifiers)
                )

            # 3: Add modifier key up events (in reverse order)
            for modifier_key, modifier_flag in modifier_keys:
                current_modifiers &= (
                    ~modifier_flag
                )  # remove the modifier from current modifiers (the same idea)
                modifier_action = KeyEvents.Action.from_key_and_modifiers(
                    modifier_key, current_modifiers
                )
                events.extend(
                    modifier_action.to_basic_event(
                        KeyPressEvent.KEY_UP, current_modifiers
                    )
                )

            # 4: Add main key up (if itself is not a modifier key)
            if not is_modifier_key:
                if isinstance(original_key, SpecialKeys):
                    events.extend(
                        self.to_basic_event(KeyPressEvent.KEY_UP, current_modifiers)
                    )
                else:
                    events.extend(
                        self.to_basic_event(KeyPressEvent.KEY_UP, 0, str(original_key))
                    )

            return events
