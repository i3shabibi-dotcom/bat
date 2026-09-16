# -*- coding: utf-8 -*-
import os
import queue
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import arabic_reshaper
from bidi.algorithm import get_display
import engine as eng

APP_NAME = "Arabic Hesham - Universal 3DS Patcher"
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
        self.geometry("780x610")
        self.minsize(720, 570)
        self.configure(bg=BG)
        self.patch_path = ""
        self.game_path = ""
        self.manifest = None
        self.validated = False
        self.worker = None
        self._build_ui()
        self.after(100, self._poll)

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
        tk.Label(top, text="H", fg=AMBER, bg=BG, font=("Segoe UI", 38, "bold")).pack(side="left")
        titles = tk.Frame(top, bg=BG)
        titles.pack(side="left", padx=14)
        tk.Label(titles, text=rtl("أداة دمج باتشات Nintendo 3DS"), fg=FG, bg=BG,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(titles, text="Arabic Hesham - Universal 3DS Patcher", fg=MUTED, bg=BG,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        card = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground="#333333")
        card.pack(fill="both", expand=True, padx=28, pady=12)

        self._section(card, "1", "اختر ملف الباتش AH3P", self.choose_patch, "اختيار الباتش")
        self.patch_var = tk.StringVar(value=rtl("لم يتم اختيار باتش"))
        self.patch_entry = tk.Entry(card, textvariable=self.patch_var, state="readonly",
                                    readonlybackground="#151515", fg="#d9d9d9", relief="flat",
                                    font=("Segoe UI", 9))
        self.patch_entry.pack(fill="x", padx=22, ipady=7)
        self.patch_info = tk.StringVar(value=rtl("بانتظار الباتش"))
        self.patch_info_label = tk.Label(card, textvariable=self.patch_info, fg=MUTED, bg=PANEL,
                                         font=("Segoe UI", 9), justify="right")
        self.patch_info_label.pack(anchor="e", padx=22, pady=(6, 10))

        self._section(card, "2", "اختر ملف اللعبة الأصلي", self.choose_game, "اختيار اللعبة")
        self.game_var = tk.StringVar(value=rtl("لم يتم اختيار لعبة"))
        self.game_entry = tk.Entry(card, textvariable=self.game_var, state="readonly",
                                   readonlybackground="#151515", fg="#d9d9d9", relief="flat",
                                   font=("Segoe UI", 9))
        self.game_entry.pack(fill="x", padx=22, ipady=7)
        self.verify_var = tk.StringVar(value=rtl("اختر الباتش أولاً ثم اللعبة"))
        self.verify_label = tk.Label(card, textvariable=self.verify_var, fg=MUTED, bg=PANEL,
                                     font=("Segoe UI", 9))
        self.verify_label.pack(anchor="e", padx=22, pady=(6, 12))

        self.bar = ttk.Progressbar(card, style="AH.Horizontal.TProgressbar", mode="determinate",
                                   maximum=100, value=0)
        self.bar.pack(fill="x", padx=22, pady=(4, 8))
        self.status_var = tk.StringVar(value=rtl("جاهز"))
        tk.Label(card, textvariable=self.status_var, fg=FG, bg=PANEL,
                 font=("Segoe UI", 10)).pack(anchor="e", padx=22, pady=(0, 8))

        self.log = tk.Text(card, height=7, bg="#151515", fg="#cfcfcf", relief="flat",
                           font=("Consolas", 9), wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=22, pady=(0, 12))

        self.merge_btn = tk.Button(card, text=rtl("دمج الباتش مع اللعبة"), command=self.start_merge,
                                   state="disabled", bg=AMBER, fg="#171717",
                                   activebackground="#ffbd37", activeforeground="#171717",
                                   disabledforeground="#777777", relief="flat", pady=10,
                                   font=("Segoe UI", 12, "bold"), cursor="hand2")
        self.merge_btn.pack(fill="x", padx=22, pady=(0, 20))

    def _section(self, parent, num, title, command, button_text):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=22, pady=(16 if num == "1" else 8, 7))
        tk.Label(row, text=num, bg=AMBER, fg="#171717", width=3,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(row, text=rtl(title), fg=FG, bg=PANEL,
                 font=("Segoe UI", 11, "bold")).pack(side="right")
        tk.Button(row, text=rtl(button_text), command=command, bg="#3b3b3b", fg=FG,
                  activebackground="#4b4b4b", activeforeground=FG, relief="flat",
                  padx=16, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=(10, 0))
        if num == "1":
            self.patch_btn = row.winfo_children()[-1]
        else:
            self.game_btn = row.winfo_children()[-1]

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_busy(self, yes):
        state = "disabled" if yes else "normal"
        self.patch_btn.configure(state=state)
        self.game_btn.configure(state=state)
        self.merge_btn.configure(state="disabled" if yes or not self.validated else "normal")

    def choose_patch(self):
        if self.worker and self.worker.is_alive():
            return
        p = filedialog.askopenfilename(
            title=rtl("اختر ملف الباتش"),
            filetypes=[("Arabic Hesham 3DS Patch", "*.ah3p"), ("ZIP patch", "*.zip"), ("All files", "*.*")],
        )
        if not p:
            return
        self.patch_path = p
        self.patch_var.set(p)
        self.manifest = None
        self.validated = False
        self.merge_btn.configure(state="disabled")
        self.patch_info.set(rtl("جاري فحص الباتش..."))
        self.status_var.set(rtl("فحص الباتش"))
        self._set_busy(True)
        self.worker = threading.Thread(target=self._inspect_patch_worker, daemon=True)
        self.worker.start()

    def _inspect_patch_worker(self):
        try:
            m = eng.inspect_patch(self.patch_path)
            Q.put(("patch_ok", m))
        except Exception:
            Q.put(("error", traceback.format_exc()))

    def choose_game(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.manifest:
            messagebox.showwarning(rtl("اختر الباتش"), rtl("اختر ملف الباتش أولاً."))
            return
        p = filedialog.askopenfilename(
            title=rtl("اختر ملف اللعبة الأصلي"),
            filetypes=[("Nintendo 3DS", "*.3ds *.cci"), ("All files", "*.*")],
        )
        if not p:
            return
        self.game_path = p
        self.game_var.set(p)
        self.validated = False
        self.merge_btn.configure(state="disabled")
        self.verify_label.configure(fg=MUTED)
        self.verify_var.set(rtl("جاري التحقق من نسخة اللعبة..."))
        self.status_var.set(rtl("التحقق من SHA-256"))
        self._set_busy(True)
        self.worker = threading.Thread(target=self._validate_worker, daemon=True)
        self.worker.start()

    def _validate_worker(self):
        try:
            ok, detail = eng.validate_source(self.game_path, self.manifest)
            Q.put(("validated", (ok, detail)))
        except Exception:
            Q.put(("error", traceback.format_exc()))

    def start_merge(self):
        if not self.validated or not self.manifest or not self.patch_path or not self.game_path:
            return
        self.bar["value"] = 0
        self.status_var.set(rtl("بدء الدمج..."))
        self._log("Starting patch merge...")
        self._set_busy(True)
        self.worker = threading.Thread(target=self._merge_worker, daemon=True)
        self.worker.start()

    def _merge_worker(self):
        try:
            eng.PROGRESS_CB = progress_cb
            result = eng.apply_patch(self.patch_path, self.game_path)
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
                    self.status_var.set(rtl(name) if any("\u0600" <= c <= "\u06ff" for c in name) else name)
                    if int(pct) in (2, 18, 25, 33, 60, 69, 77, 82, 85, 94, 100):
                        self._log("%3d%%  %s" % (int(pct), name))
                elif kind == "patch_ok":
                    self.manifest = data
                    self._set_busy(False)
                    info = f"{data['patch_name']} | {data['game_name']} | v{data['patch_version']} | {data['file_count']} files"
                    self.patch_info.set(info)
                    self.patch_info_label.configure(fg=GREEN)
                    self.status_var.set(rtl("تم التحقق من الباتش"))
                    self._log("Patch: " + info)
                    self._log("Patch SHA-256: " + data["patch_sha256"])
                    if self.game_path:
                        self.choose_game()
                elif kind == "validated":
                    ok, detail = data
                    self._set_busy(False)
                    if ok:
                        self.validated = True
                        self.verify_label.configure(fg=GREEN)
                        self.verify_var.set(rtl("تم التحقق: نسخة اللعبة مطابقة للباتش"))
                        self.status_var.set(rtl("جاهز للدمج"))
                        self.merge_btn.configure(state="normal")
                        self._log("Source SHA-256 verified: " + detail)
                    else:
                        self.validated = False
                        self.verify_label.configure(fg=RED)
                        self.verify_var.set(rtl("نسخة اللعبة غير مطابقة للباتش"))
                        self.status_var.set(rtl("اختر نسخة اللعبة الصحيحة"))
                        messagebox.showerror(rtl("نسخة غير صحيحة"), detail)
                elif kind == "done":
                    self._set_busy(False)
                    self.bar["value"] = 100
                    self.status_var.set(rtl("اكتمل الدمج"))
                    out = eng.LAST_OUTPUT or ""
                    sha = eng.LAST_OUTPUT_SHA256 or ""
                    self._log("Output: " + out)
                    self._log("SHA-256: " + sha)
                    messagebox.showinfo(
                        rtl("تم بنجاح"),
                        rtl("تم إنشاء نسخة جديدة دون تعديل الملف الأصلي.") +
                        "\n\n" + out + "\n\nSHA-256:\n" + sha,
                    )
                elif kind == "error":
                    self._set_busy(False)
                    self.status_var.set(rtl("فشلت العملية"))
                    lines = [x for x in data.strip().splitlines() if x.strip()]
                    msg = lines[-1] if lines else data
                    self._log(data)
                    messagebox.showerror(
                        rtl("خطأ"),
                        msg + "\n\n" + rtl("إذا تم إنشاء Arabic_Hesham_3DS_Patcher_Error.log أرسله للمطور."),
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
