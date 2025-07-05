from enum import Enum, IntEnum, StrEnum
import emoji
from typing import Union, List, Tuple, Optional
from typing_extensions import TypedDict


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

    MODIFIER_KEYS = [
        SpecialKeys.SHIFT,
        SpecialKeys.ALT,
        SpecialKeys.CTRL,
        SpecialKeys.META,
    ]

    SPECIAL_KEY_CHAR_MAP = {
        SpecialKeys.SPACE: " ",
        SpecialKeys.ENTER: "\n",
        SpecialKeys.TAB: "\t",
    }

    class Payload(TypedDict):
        type_: str
        modifiers: int
        text: Optional[str]
        key: Optional[str]
        code: Optional[str]
        windows_virtual_key_code: Optional[int]
        native_virtual_key_code: Optional[int]

    def __init__(self, key: Union[str, SpecialKeys]):
        """
        Initialize a KeyEvents instance.

        Args:
            key: The key to be processed (single character string or SpecialKeys enum)
            key_press_event: The type of key press event to generate (Currently supported are `DOWN_AND_UP` and `CHAR`)
            modifiers: Modifier keys to be applied (can be combined with bitwise OR)
        """

        # modifiers = modifiers
        self.key = key

        self.code, self.keyCode = (
            self._handle_string_key_lookup(self.key)
            if isinstance(self.key, str)
            else self._handle_special_key_lookup(self.key)
        )

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

    def _get_key_and_text(
        self, key_press_event: KeyPressEvent, modifiers: Union[KeyModifiers, int]
    ) -> Tuple[str, Optional[str]]:
        """
        Create the appropriate action for this key event.

        Returns:
            Action object containing the processed key information

        Raises:
            ValueError: If key is invalid for CHAR event type
        """
        if key_press_event == KeyPressEvent.CHAR:
            if isinstance(self.key, SpecialKeys):
                self.key = self.conv_to_str(self.key)
            return self.key, self.key

        return self._build_action_data(modifiers)

    def _normalise_key(
        self, key: Union[str, SpecialKeys], modifiers: Union[KeyModifiers, int]
    ) -> Tuple[Union[str, SpecialKeys], Union[KeyModifiers, int]]:
        """
        Convert a shifted key to its non-shifted equivalent.

        Args:
            key: The key to convert (may be shifted)

        Returns:
            The non-shifted equivalent of the key

        Raises:
            ValueError: If the key is not recognized or supported
        """
        lowercase_key: Optional[str] = None
        if isinstance(key, SpecialKeys):
            return key, modifiers  # all the special keys dont have shifted variants

        if key in self.NUM_SHIFT:
            modifiers |= KeyModifiers.Shift
            lowercase_key = str(self.NUM_SHIFT.index(key))
        elif key in self.SPECIAL_CHAR_SHIFT_MAP:
            modifiers |= KeyModifiers.Shift
            lowercase_key = self.SPECIAL_CHAR_SHIFT_MAP[key]
        elif key.isalpha() and key.isupper():
            modifiers |= KeyModifiers.Shift
            lowercase_key = key.lower()
        elif key in "\n\r":
            return SpecialKeys.ENTER, modifiers
        elif key == "\t":
            return SpecialKeys.TAB, modifiers
        elif key == " ":
            return SpecialKeys.SPACE, modifiers

        if (
            modifiers != KeyModifiers.Default | KeyModifiers.Shift
            and lowercase_key is not None
        ):
            raise ValueError(
                f"Key '{key}' is not supported with modifiers {modifiers}."
            )

        if lowercase_key is None:
            return key, modifiers

        modifiers |= KeyModifiers.Shift
        return lowercase_key, modifiers

    def _to_basic_event(
        self,
        key_press_event: KeyPressEvent,
        modifiers: Union[KeyModifiers, int] = KeyModifiers.Default,
    ):
        key, text = self._get_key_and_text(key_press_event, modifiers)
        if key_press_event == KeyPressEvent.CHAR:
            if text is None:
                raise ValueError(
                    f"Key '{self.key}' is not supported for CHAR event type. Only single ASCII characters are allowed."
                )
            return self.Payload(
                type_=key_press_event.value,
                modifiers=modifiers,
                text=text,
                key=None,
                code=None,
                windows_virtual_key_code=None,
                native_virtual_key_code=None,
            )

        return self.Payload(
            type_=key_press_event.value,
            modifiers=modifiers,
            text=text,
            key=key,
            code=self.code,
            windows_virtual_key_code=self.keyCode,
            native_virtual_key_code=self.keyCode,
        )

    def to_cdp_events(
        self,
        key_press_event: KeyPressEvent,
        modifiers: Union[KeyModifiers, int] = KeyModifiers.Default,
    ) -> List["KeyEvents.Payload"]:
        """
        Convert the key event to CDP format.

        Returns:
            List of dictionaries containing CDP `payload`
        """
        if isinstance(self.key, str) and emoji.is_emoji(self.key):
            key_press_event = KeyPressEvent.CHAR

        match key_press_event:
            case (
                KeyPressEvent.KEY_DOWN
                | KeyPressEvent.RAW_KEY_DOWN
                | KeyPressEvent.KEY_UP
            ):
                raise ValueError(
                    "Not supported by itself, use CHAR or DOWN_AND_UP instead."
                )
            case KeyPressEvent.CHAR:
                if not isinstance(self.key, str) or len(self.key) != 1:
                    raise ValueError(
                        f"Key '{self.key}' is not supported for CHAR event type. Only single ASCII characters are allowed."
                    )
                return [self._to_basic_event(key_press_event)]
            case KeyPressEvent.DOWN_AND_UP:
                self.key, modifiers = self._normalise_key(self.key, modifiers)
                return self.to_down_up_sequence(modifiers)
            case _:
                raise ValueError(f"Unsupported key press event type: {key_press_event}")

    def _handle_string_key_lookup(self, key: str) -> Tuple[str, int]:
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

    def _handle_special_key_lookup(self, key: SpecialKeys) -> Tuple[str, int]:
        """Handle special key lookup logic."""
        if key in KeyEvents.MODIFIER_KEYS:
            return f"{key.value[0]}Left", key.value[1]
        return key.value

    def _decompose_modifiers(
        self, modifiers: Union[KeyModifiers, int]
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

    def _build_action_data(
        self, modifiers: Union[KeyModifiers, int]
    ) -> Tuple[str, Optional[str]]:
        """
        Build the data needed for a key press action.

        Args:
            key: The key to process
            modifiers: Modifier keys to apply

        Returns:
            Tuple containing (text, key, code, windowsVirtualKeyCode, nativeVirtualKeyCode)
        """

        # Handle printable characters with potential shift modifier
        if isinstance(self.key, str):
            return self._handle_printable_char(self.key, modifiers)

        # Handle modifier keys
        if self.key in KeyEvents.SPECIAL_KEY_CHAR_MAP:
            # Special keys that are not modifiers
            return (
                self.SPECIAL_KEY_CHAR_MAP[self.key],
                self.SPECIAL_KEY_CHAR_MAP[self.key],
            )

        # Handle other special keys
        return self.key.value[0], None

    def _handle_printable_char(
        self, key: str, modifiers: Union[KeyModifiers, int]
    ) -> Tuple[str, str]:
        """Handle printable character with potential shift modifier."""
        if modifiers != KeyModifiers.Shift:
            return key, key

        # Apply shift transformation
        if key.isalpha():
            shifted_key = key.upper()
        elif key.isdigit():
            shifted_key = KeyEvents.NUM_SHIFT[int(key)]
        else:
            shifted_key = key
            for shift_char, orig_char in KeyEvents.SPECIAL_CHAR_SHIFT_MAP.items():
                if key == orig_char:
                    shifted_key = shift_char
                    break

        return shifted_key, shifted_key

    def to_down_up_sequence(
        self, modifiers: Union[KeyModifiers, int]
    ) -> List["KeyEvents.Payload"]:
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
        events: List[KeyEvents.Payload] = []
        modifier_events = [
            (KeyEvents(key), _modifier)
            for key, _modifier in self._decompose_modifiers(modifiers)
        ]
        is_modifier_key = any(key.key == self.key for key, _ in modifier_events)

        # 1: Add modifier key down events
        current_modifiers = 0
        for modifier_key, modifier_flag in modifier_events:
            current_modifiers |= modifier_flag  # done like this since all the keys are not pressed or processed at once
            modifier_payload = modifier_key._to_basic_event(
                KeyPressEvent.KEY_DOWN, current_modifiers
            )
            events.append(modifier_payload)

        # 2: Add main key down (if itself is not a modifier key)
        if not is_modifier_key:
            events.append(
                self._to_basic_event(KeyPressEvent.KEY_DOWN, current_modifiers)
            )

        # 3: Add modifier key up events (in reverse order)
        for modifier_key, modifier_flag in modifier_events:
            current_modifiers &= (
                ~modifier_flag
            )  # remove the modifier from current modifiers (the same idea)
            modifier_payload = modifier_key._to_basic_event(
                KeyPressEvent.KEY_UP, current_modifiers
            )
            events.append(modifier_payload)

        # 4: Add main key up (if itself is not a modifier key)
        if not is_modifier_key:
            events.append(self._to_basic_event(KeyPressEvent.KEY_UP, current_modifiers))

        return events

    # @classmethod
    # def from_string(cls, text:str) -> List["KeyEvents"]:
