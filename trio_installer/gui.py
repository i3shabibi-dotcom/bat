# -*- coding: utf-8 -*-
import os
import queue
import threading
import traceback
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import arabic_reshaper
from bidi.algorithm import get_display
import apply as eng

GAME_NAME = "STORY OF SEASONS: Trio of Towns"
APP_NAME = "Arabic_Hesham_Story_of_Seasons_Trio_of_Towns"
X_URL = "https://x.com/Arabic_Hesham"
KOFI_URL = "https://ko-fi.com/arabichesham"

BG = "#171717"
PANEL = "#222222"
FG = "#f2f2f2"
MUTED = "#a8a8a8"
AMBER = "#f3a712"
GREEN = "#35b46f"
RED = "#e45d5d"

Q = queue.Queue()


def rtl(text):
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def progress_cb(name, pct):
    Q.put(("progress", (name, pct)))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("720x520")
        self.minsize(680, 500)
        self.configure(bg=BG)
        self.source = ""
        self.validated = False
        self.worker = None
        self._build_ui()
        self.after(100, self._poll)
        self.after(350, self.choose_source)

    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("AH.Horizontal.TProgressbar", troughcolor="#303030", background=AMBER,
                        bordercolor="#303030", lightcolor=AMBER, darkcolor=AMBER)

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=28, pady=(24, 8))

        logo = tk.Label(top, text="H", fg=AMBER, bg=BG, font=("Segoe UI", 38, "bold"))
        logo.pack(side="left")
        titles = tk.Frame(top, bg=BG)
        titles.pack(side="left", padx=14)
        tk.Label(titles, text=rtl("تعريب هشام"), fg=FG, bg=BG,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(titles, text=GAME_NAME, fg=MUTED, bg=BG,
                 font=("Segoe UI", 11)).pack(anchor="w", pady=(2, 0))

        card = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground="#333333")
        card.pack(fill="both", expand=True, padx=28, pady=12)

        tk.Label(card, text=rtl("اختر ملف اللعبة الأصلي"), fg=FG, bg=PANEL,
                 font=("Segoe UI", 13, "bold")).pack(anchor="e", padx=22, pady=(22, 8))

        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", padx=22)
        self.path_var = tk.StringVar(value=rtl("لم يتم اختيار ملف بعد"))
        self.path_entry = tk.Entry(row, textvariable=self.path_var, state="readonly",
                                   readonlybackground="#151515", fg="#d9d9d9",
                                   insertbackground=FG, relief="flat", font=("Segoe UI", 10))
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.browse_btn = tk.Button(row, text=rtl("استعراض"), command=self.choose_source,
                                    bg="#3b3b3b", fg=FG, activebackground="#4b4b4b",
                                    activeforeground=FG, relief="flat", padx=20, pady=7,
                                    font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.browse_btn.pack(side="left", padx=(10, 0))

        self.verify_var = tk.StringVar(value=rtl("بانتظار اختيار النسخة الأصلية"))
        self.verify_label = tk.Label(card, textvariable=self.verify_var, fg=MUTED, bg=PANEL,
                                     font=("Segoe UI", 10))
        self.verify_label.pack(anchor="e", padx=22, pady=(8, 14))

        self.bar = ttk.Progressbar(card, style="AH.Horizontal.TProgressbar", mode="determinate",
                                   maximum=100, value=0)
        self.bar.pack(fill="x", padx=22, pady=(4, 8))

        self.status_var = tk.StringVar(value=rtl("جاهز"))
        self.status = tk.Label(card, textvariable=self.status_var, fg=FG, bg=PANEL,
                               font=("Segoe UI", 11))
        self.status.pack(anchor="e", padx=22, pady=(0, 12))

        self.log = tk.Text(card, height=6, bg="#151515", fg="#cfcfcf", relief="flat",
                           font=("Consolas", 9), wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=22, pady=(0, 14))

        self.install_btn = tk.Button(card, text=rtl("تثبيت التعريب"), command=self.start_install,
                                     state="disabled", bg=AMBER, fg="#171717",
                                     activebackground="#ffbd37", activeforeground="#171717",
                                     disabledforeground="#777777", disabledbackground="#4b4230",
                                     relief="flat", pady=10, font=("Segoe UI", 12, "bold"),
                                     cursor="hand2")
        self.install_btn.pack(fill="x", padx=22, pady=(0, 22))

        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=28, pady=(0, 18))
        tk.Button(foot, text="@Arabic_Hesham", command=lambda: webbrowser.open(X_URL),
                  bg=BG, fg=MUTED, activebackground=BG, activeforeground=AMBER,
                  relief="flat", cursor="hand2").pack(side="left")
        tk.Button(foot, text=rtl("ادعم استمرار التعريب"), command=lambda: webbrowser.open(KOFI_URL),
                  bg=BG, fg=MUTED, activebackground=BG, activeforeground=AMBER,
                  relief="flat", cursor="hand2").pack(side="right")

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _busy(self, yes):
        self.browse_btn.configure(state="disabled" if yes else "normal")
        self.install_btn.configure(state="disabled" if yes or not self.validated else "normal")

    def choose_source(self):
        if self.worker and self.worker.is_alive():
            return
        p = filedialog.askopenfilename(
            title=rtl("اختر ملف STORY OF SEASONS: Trio of Towns الأصلي"),
            filetypes=[("Nintendo 3DS", "*.3ds *.cci"), ("All files", "*.*")]
        )
        if not p:
            return
        self.source = p
        self.path_var.set(p)
        self.validated = False
        self.install_btn.configure(state="disabled")
        self.verify_label.configure(fg=MUTED)
        self.verify_var.set(rtl("جاري التحقق من SHA-256..."))
        self.status_var.set(rtl("التحقق من النسخة الأصلية"))
        self.bar["value"] = 0
        self._busy(True)
        self.worker = threading.Thread(target=self._validate_worker, daemon=True)
        self.worker.start()

    def _validate_worker(self):
        try:
            ok, detail = eng.validate_source(self.source)
            Q.put(("validated", (ok, detail)))
        except Exception:
            Q.put(("error", traceback.format_exc()))

    def start_install(self):
        if not self.validated or not self.source:
            return
        self.bar["value"] = 0
        self.status_var.set(rtl("بدء تثبيت التعريب..."))
        self._log("Starting Arabic installation...")
        self._busy(True)
        self.worker = threading.Thread(target=self._install_worker, daemon=True)
        self.worker.start()

    def _install_worker(self):
        try:
            eng.PROGRESS_CB = progress_cb
            result = eng.main(game_path=self.source)
            Q.put(("done", result))
        except Exception:
            Q.put(("error", traceback.format_exc()))

    def _poll(self):
        try:
            while True:
                kind, data = Q.get_nowait()
                if kind == "progress":
                    name, pct = data
                    self.bar["value"] = pct
                    self.status_var.set(rtl(name) if any('\u0600' <= c <= '\u06ff' for c in name) else name)
                    if int(pct) in (20, 27, 35, 61, 70, 79, 84, 88, 91, 94, 100):
                        self._log("%3d%%  %s" % (int(pct), name))
                elif kind == "validated":
                    ok, detail = data
                    self._busy(False)
                    if ok:
                        self.validated = True
                        self.verify_label.configure(fg=GREEN)
                        self.verify_var.set(rtl("تم التحقق: النسخة الأصلية صحيحة"))
                        self.status_var.set(rtl("جاهز لتثبيت التعريب"))
                        self.install_btn.configure(state="normal")
                        self._log("Source SHA-256 verified: " + detail)
                    else:
                        self.validated = False
                        self.verify_label.configure(fg=RED)
                        self.verify_var.set(rtl("النسخة المحددة غير مطابقة"))
                        self.status_var.set(rtl("اختر النسخة الأمريكية الأصلية الصحيحة"))
                        messagebox.showerror(rtl("نسخة غير صحيحة"), detail)
                elif kind == "done":
                    self._busy(False)
                    self.bar["value"] = 100
                    self.status_var.set(rtl("اكتمل تثبيت التعريب"))
                    out = eng.LAST_OUTPUT or ""
                    sha = eng.LAST_OUTPUT_SHA256 or ""
                    self._log("Output: " + out)
                    self._log("SHA-256: " + sha)
                    messagebox.showinfo(
                        rtl("تم بنجاح"),
                        rtl("تم إنشاء نسخة عربية جديدة دون تعديل الملف الأصلي.") +
                        "\n\n" + out + "\n\nSHA-256:\n" + sha
                    )
                elif kind == "error":
                    self._busy(False)
                    self.status_var.set(rtl("فشلت العملية"))
                    self.verify_label.configure(fg=RED)
                    lines = [x for x in data.strip().splitlines() if x.strip()]
                    msg = lines[-1] if lines else data
                    self._log(data)
                    messagebox.showerror(
                        rtl("خطأ في المثبت"),
                        msg + "\n\n" + rtl("إذا أنشئ ملف Trio_Arabic_Patcher_Error.log أرسله للمطور.")
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
