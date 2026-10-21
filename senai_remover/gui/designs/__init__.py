"""The four themes, in the order of their Ctrl+1 to Ctrl+4 shortcuts and the
Settings cards."""

from .apple_classic import AppleClassicWindow
from .apple_glass import AppleGlassWindow
from .exercise_book import ExerciseBookWindow
from .fluent import FluentWindow

DESIGNS = [AppleClassicWindow, AppleGlassWindow, ExerciseBookWindow, FluentWindow]
