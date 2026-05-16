# -*- coding: utf-8 -*-
"""
Maya - Max style timeline controls

Features
--------
Ctrl + Alt + LMB drag on timeline:
    Resize playback MIN (inverted)
    drag right  -> min goes left
    drag left   -> min goes right

Ctrl + Alt + RMB drag on timeline:
    Resize playback MAX (inverted)
    drag right  -> max gets smaller
    drag left   -> max gets bigger

Ctrl + Alt + MMB drag on timeline:
    Slide whole playback range left/right

Usage
-----
1) Drag & drop this .py file into Maya.
2) It auto-installs.

Manual:
    import max_style_timeline_controls as mstc
    mstc.install_max_timeline_controls()
    mstc.uninstall_max_timeline_controls()

Notes
-----
- Works on Maya main time slider.
- Designed for drag-and-drop install via onMayaDroppedPythonFile.
"""

from maya import cmds, mel
from maya import OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtWidgets
    import shiboken6 as shiboken
except ImportError:
    from PySide2 import QtCore, QtWidgets
    import shiboken2 as shiboken


_MAX_TIMELINE_FILTER = None


def _find_playback_slider_widget():
    slider_name = mel.eval('$tmpVar = $gPlayBackSlider')
    if not slider_name:
        return None

    ptr = omui.MQtUtil.findControl(slider_name)
    if ptr is None:
        ptr = omui.MQtUtil.findLayout(slider_name)
    if ptr is None:
        ptr = omui.MQtUtil.findMenuItem(slider_name)
    if ptr is None:
        return None

    return shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)


class MaxStyleTimelineFilter(QtCore.QObject):
    def __init__(self, target_widget, parent=None):
        super(MaxStyleTimelineFilter, self).__init__(parent)

        self.target_widget = target_widget
        self.dragging = False
        self.drag_mode = None  # "min", "max", "slide"

        self.start_global_x = 0
        self.start_min = 0.0
        self.start_max = 0.0

        # Smaller = faster, larger = more precise
        self.pixels_per_frame = 6.0

    def _is_target_or_child(self, obj):
        if obj is None or self.target_widget is None:
            return False
        if obj == self.target_widget:
            return True
        try:
            return self.target_widget.isAncestorOf(obj)
        except Exception:
            return False

    def _global_x(self, event):
        if hasattr(event, "globalPosition"):
            return event.globalPosition().x()
        return event.globalX()

    def _mods_ctrl_alt(self, event):
        mods = event.modifiers()
        return bool(mods & QtCore.Qt.ControlModifier) and bool(mods & QtCore.Qt.AltModifier)

    def _start_drag(self, event, mode):
        self.dragging = True
        self.drag_mode = mode
        self.start_global_x = self._global_x(event)

        self.start_min = cmds.playbackOptions(q=True, min=True)
        self.start_max = cmds.playbackOptions(q=True, max=True)

        if mode == "min":
            msg = "<hl>Resize MIN</hl> : Ctrl+Alt+LMB"
        elif mode == "max":
            msg = "<hl>Resize MAX</hl> : Ctrl+Alt+RMB"
        else:
            msg = "<hl>Slide Range</hl> : Ctrl+Alt+MMB"

        cmds.inViewMessage(amg=msg, pos="botCenter", fade=True)

    def _update_drag(self, event):
        current_x = self._global_x(event)
        delta_pixels = current_x - self.start_global_x
        delta_frames = round(delta_pixels / self.pixels_per_frame)

        start_min = self.start_min
        start_max = self.start_max

        if self.drag_mode == "max":
            # drag right -> smaller, drag left -> bigger
            new_max = start_max - delta_frames
            if new_max <= start_min:
                new_max = start_min + 1
            cmds.playbackOptions(max=new_max)

        elif self.drag_mode == "min":
            # drag right -> min goes left, drag left -> min goes right
            new_min = start_min - delta_frames
            if new_min >= start_max:
                new_min = start_max - 1
            cmds.playbackOptions(min=new_min)

        elif self.drag_mode == "slide":
            # whole range slide
            new_min = start_min - delta_frames
            new_max = start_max - delta_frames
            cmds.playbackOptions(min=new_min, max=new_max)

    def _end_drag(self):
        self.dragging = False
        self.drag_mode = None

    def eventFilter(self, obj, event):
        if not self._is_target_or_child(obj):
            return False

        etype = event.type()

        if etype == QtCore.QEvent.MouseButtonPress:
            if self._mods_ctrl_alt(event):
                if event.button() == QtCore.Qt.LeftButton:
                    self._start_drag(event, "min")
                    return True
                elif event.button() == QtCore.Qt.RightButton:
                    self._start_drag(event, "max")
                    return True
                elif event.button() == QtCore.Qt.MiddleButton:
                    self._start_drag(event, "slide")
                    return True

        elif etype == QtCore.QEvent.MouseMove:
            if self.dragging:
                self._update_drag(event)
                return True

        elif etype == QtCore.QEvent.MouseButtonRelease:
            if self.dragging:
                self._end_drag()
                return True

        elif etype == QtCore.QEvent.ContextMenu:
            if self.dragging:
                return True

        return False


def install_max_timeline_controls():
    global _MAX_TIMELINE_FILTER

    uninstall_max_timeline_controls(silent=True)

    timeline_widget = _find_playback_slider_widget()
    if timeline_widget is None:
        cmds.warning("Maya playback slider widget bulunamadı.")
        return False

    app = QtWidgets.QApplication.instance()
    if app is None:
        cmds.warning("QApplication bulunamadı.")
        return False

    _MAX_TIMELINE_FILTER = MaxStyleTimelineFilter(
        target_widget=timeline_widget,
        parent=app
    )
    app.installEventFilter(_MAX_TIMELINE_FILTER)

    print("Max-style timeline controls installed.")
    print("Ctrl+Alt+LMB = resize MIN (inverted)")
    print("Ctrl+Alt+RMB = resize MAX (inverted)")
    print("Ctrl+Alt+MMB = slide whole range")

    try:
        cmds.inViewMessage(
            amg='<hl>Max-style timeline controls installed</hl>',
            pos='midCenterTop',
            fade=True
        )
    except Exception:
        pass

    return True


def uninstall_max_timeline_controls(silent=False):
    global _MAX_TIMELINE_FILTER

    app = QtWidgets.QApplication.instance()
    if app is not None and _MAX_TIMELINE_FILTER is not None:
        try:
            app.removeEventFilter(_MAX_TIMELINE_FILTER)
        except Exception:
            pass

    _MAX_TIMELINE_FILTER = None
    if not silent:
        print("Max-style timeline controls uninstalled.")
    return True


def onMayaDroppedPythonFile(*args):
    """Called automatically when this file is drag-dropped into Maya."""
    install_max_timeline_controls()

