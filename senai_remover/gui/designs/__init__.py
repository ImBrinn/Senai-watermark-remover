"""Themes, in the order of their Ctrl+1, Ctrl+2, … shortcuts and the
Settings cards. The first four stay in their original places."""

from .apple_classic import AppleClassicWindow
from .apple_glass import AppleGlassWindow
from .aurora import AuroraWindow
from .contrast import ContrastWindow
from .exercise_book import ExerciseBookWindow
from .fluent import FluentWindow
from .midnight import MidnightWindow
from .mono import MonoWindow

DESIGNS = [AppleClassicWindow, AppleGlassWindow, ExerciseBookWindow, FluentWindow,
           MidnightWindow, AuroraWindow, MonoWindow, ContrastWindow]
