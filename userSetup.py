import max_style_timeline_controls as mstc

def load_tool():
    try:
        mstc.install_max_timeline_controls()
        print("Max Timeline Tool Loaded")
    except Exception as e:
        print("Tool load error:", e)

# Maya UI hazır olunca çalıştır
import maya.utils
maya.utils.executeDeferred(load_tool)