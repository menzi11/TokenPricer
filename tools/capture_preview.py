"""Capture only this application's window; Pillow is a development-only dependency."""
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from PIL import ImageGrab

folder = Path(__file__).resolve().parents[1] / "docs"
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as temp:
    app = App(Path(temp) / "prices.json")
    app.geometry("1080x820+20+20")
    app.model.set("Kimi K2.7 Code / 国内 API")
    app.select_model()
    app.cached.set("900k")
    app.lift()

    def capture(name):
        app.update_idletasks()
        x, y = app.winfo_rootx(), app.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(folder / name)

    def second():
        capture("api.png")
        app.tabs.select(1)
        app.plan.set("Kimi Allegretto / 帮助中心月费")
        app.select_plan()
        app.use_sample()
        app.update_idletasks()
        app.scroll_canvas.yview_moveto(0.44)
        app.after(800, finish)

    def finish():
        capture("subscription.png")
        app.destroy()

    app.after(1000, second)
    app.mainloop()
print("Captured docs/api.png and docs/subscription.png")
