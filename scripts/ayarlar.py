"""KOU'de Hava — ayar arayuzu.

  python scripts/ayarlar.py

Gonderiyle ilgili tum ayarlari duzenler (config/campuses.json, .env ve
workflow zamanlamasi), onizleme uretir ve istege bagli olarak degisiklikleri
dogrudan GitHub'a gonderir.

Yalnizca standart kutuphane kullanir (tkinter).
"""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import settings_io as io  # noqa: E402

PAD = {"padx": 10, "pady": 6}


# --------------------------------------------------------------- yardimci

def run_command(args: list[str], log) -> int:
    """Komutu calistirir, ciktisini satir satir log'a yazar."""
    log("$ " + " ".join(args))
    try:
        proc = subprocess.Popen(
            args, cwd=str(ROOT), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1,
        )
    except FileNotFoundError:
        log(f"  HATA: '{args[0]}' bulunamadı.")
        return 127

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            log("  " + line)
    return proc.wait()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("KOÜ'de Hava — Ayarlar")
        self.geometry("1000x780")
        self.minsize(900, 700)

        self.config_data = io.load_config()
        self.env_data = io.load_env()
        self.campuses = list(self.config_data.get("campuses", []))
        self.busy = False
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._load_values()
        self.after(100, self._drain_log)

    # ------------------------------------------------------------ arayuz

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        self._tab_post(notebook)
        self._tab_caption(notebook)
        self._tab_campuses(notebook)
        self._tab_account(notebook)
        self._tab_instagram(notebook)

        # --- alt eylem cubugu ---
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12)

        self.status = ttk.Label(bar, text="Hazır", foreground="#444")
        self.status.pack(side="left", pady=6)

        self.btn_push = ttk.Button(bar, text="Kaydet ve GitHub'a gönder",
                                   command=self.save_and_push)
        self.btn_push.pack(side="right", padx=(6, 0), pady=6)
        self.btn_save = ttk.Button(bar, text="Kaydet", command=self.save_only)
        self.btn_save.pack(side="right", padx=6, pady=6)
        self.btn_check = ttk.Button(bar, text="Kurulum kontrolü",
                                    command=self.run_preflight)
        self.btn_check.pack(side="right", padx=6, pady=6)
        self.btn_preview = ttk.Button(bar, text="Önizleme üret",
                                      command=self.run_preview)
        self.btn_preview.pack(side="right", padx=6, pady=6)

        # --- gunluk ---
        frame = ttk.LabelFrame(self, text="Günlük")
        frame.pack(fill="both", expand=False, padx=12, pady=(0, 12))
        self.log_text = tk.Text(frame, height=11, wrap="word",
                                font=("Consolas", 9))
        scroll = ttk.Scrollbar(frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True, padx=(6, 0),
                           pady=6)
        scroll.pack(side="right", fill="y", pady=6, padx=(0, 6))

    def _tab_post(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Gönderi  ")

        box = ttk.LabelFrame(tab, text="Zamanlama")
        box.grid(row=0, column=0, sticky="ew", **PAD)
        ttk.Label(box, text="Paylaşım saati (Türkiye saati)").grid(
            row=0, column=0, sticky="w", **PAD)
        self.var_time = tk.StringVar()
        ttk.Entry(box, textvariable=self.var_time, width=10).grid(
            row=0, column=1, sticky="w", **PAD)
        self.lbl_cron = ttk.Label(box, text="", foreground="#666")
        self.lbl_cron.grid(row=0, column=2, sticky="w", **PAD)
        self.var_time.trace_add("write", lambda *_: self._update_cron_hint())

        box2 = ttk.LabelFrame(tab, text="Slaytlar")
        box2.grid(row=1, column=0, sticky="ew", **PAD)

        ttk.Label(box2, text="Tema").grid(row=0, column=0, sticky="w", **PAD)
        self.var_theme = tk.StringVar()
        ttk.Combobox(box2, textvariable=self.var_theme, width=10,
                     values=["light", "dark"], state="readonly").grid(
            row=0, column=1, sticky="w", **PAD)

        ttk.Label(box2, text="En fazla slayt").grid(row=0, column=2,
                                                    sticky="w", **PAD)
        self.var_max = tk.IntVar()
        spin = ttk.Spinbox(box2, from_=2, to=10, textvariable=self.var_max,
                           width=5, command=self._update_slide_hint)
        spin.grid(row=0, column=3, sticky="w", **PAD)

        self.var_summary = tk.BooleanVar()
        ttk.Checkbutton(box2, text="Özet tablosu slaytı (2. sırada)",
                        variable=self.var_summary,
                        command=self._update_slide_hint).grid(
            row=1, column=0, columnspan=2, sticky="w", **PAD)

        self.var_chart = tk.BooleanVar()
        ttk.Checkbutton(box2, text="Gün içi sıcaklık/yağış grafiği",
                        variable=self.var_chart).grid(
            row=1, column=2, columnspan=2, sticky="w", **PAD)

        self.lbl_slides = ttk.Label(box2, text="", foreground="#666")
        self.lbl_slides.grid(row=2, column=0, columnspan=4, sticky="w", **PAD)

        box3 = ttk.LabelFrame(tab, text="Açıklama metni")
        box3.grid(row=2, column=0, sticky="nsew", **PAD)
        tab.rowconfigure(2, weight=1)
        tab.columnconfigure(0, weight=1)

        row = ttk.Frame(box3)
        row.pack(fill="x")
        ttk.Label(row, text="Detay satırı sayısı").pack(side="left", **PAD)
        self.var_lines = tk.IntVar()
        ttk.Spinbox(row, from_=0, to=15, textvariable=self.var_lines,
                    width=5).pack(side="left", **PAD)
        ttk.Label(row, text="Şemsiye uyarısı eşiği (%)").pack(side="left", **PAD)
        self.var_rain = tk.IntVar()
        ttk.Spinbox(row, from_=0, to=100, textvariable=self.var_rain,
                    width=5).pack(side="left", **PAD)
        ttk.Label(row, text="Rüzgâr uyarısı (km/s)").pack(side="left", **PAD)
        self.var_wind = tk.IntVar()
        ttk.Spinbox(row, from_=0, to=120, textvariable=self.var_wind,
                    width=5).pack(side="left", **PAD)

        ttk.Label(box3, text="Hashtag'ler").pack(anchor="w", padx=10)
        self.txt_tags = tk.Text(box3, height=4, wrap="word")
        self.txt_tags.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _tab_caption(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Açıklama  ")

        ttk.Label(
            tab,
            text="Instagram gönderisinin açıklama metni. Süslü parantez içindeki "
                 "değişkenler paylaşım anında gerçek verilerle doldurulur.",
            foreground="#666", justify="left", wraplength=900,
        ).pack(anchor="w", padx=10, pady=(10, 4))

        self.txt_caption = tk.Text(tab, height=16, wrap="word",
                                   font=("Consolas", 10), undo=True)
        self.txt_caption.pack(fill="both", expand=True, padx=10, pady=6)

        box = ttk.LabelFrame(tab, text="Kullanılabilir değişkenler "
                                       "(çift tıkla ekle)")
        box.pack(fill="x", padx=10, pady=(0, 10))
        grid = ttk.Frame(box)
        grid.pack(fill="x", padx=6, pady=6)

        import caption as cap_mod
        for i, (key, hint) in enumerate(cap_mod.PLACEHOLDERS):
            row, col = divmod(i, 3)
            item = ttk.Label(grid, text=f"{{{key}}}  —  {hint}",
                             foreground="#334", cursor="hand2")
            item.grid(row=row, column=col, sticky="w", padx=8, pady=2)
            item.bind("<Double-1>",
                      lambda _e, k=key: self.txt_caption.insert(
                          "insert", "{" + k + "}"))

        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bar, text="Varsayılan metne dön",
                   command=self._reset_caption).pack(side="left")
        ttk.Label(bar, text="Instagram sınırı 2200 karakter; aşarsa "
                            "otomatik kısaltılır.",
                  foreground="#666").pack(side="left", padx=12)

    def _reset_caption(self) -> None:
        import caption as cap_mod
        if messagebox.askyesno("Varsayılan metin",
                               "Açıklama metni varsayılana dönsün mü?"):
            self.txt_caption.delete("1.0", "end")
            self.txt_caption.insert("1.0", cap_mod.DEFAULT_TEMPLATE)

    def _tab_campuses(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Yerleşkeler  ")

        cols = ("sira", "ad", "alt", "enlem", "boylam", "slayt")
        self.tree = ttk.Treeview(tab, columns=cols, show="headings", height=16)
        for key, title, width in (
            ("sira", "#", 40), ("ad", "Yerleşke", 170),
            ("alt", "Alt başlık", 290), ("enlem", "Enlem", 95),
            ("boylam", "Boylam", 95), ("slayt", "Kendi slaytı", 100),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width,
                             anchor="center" if key in ("sira", "slayt")
                             else "w")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda _e: self.edit_campus())

        side = ttk.Frame(tab)
        side.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 10))
        for text, cmd in (
            ("Yukarı taşı", lambda: self.move_campus(-1)),
            ("Aşağı taşı", lambda: self.move_campus(1)),
            ("Slaytı aç / kapa", self.toggle_campus),
            ("Düzenle…", self.edit_campus),
            ("Ekle…", self.add_campus),
            ("Sil", self.delete_campus),
        ):
            ttk.Button(side, text=text, command=cmd, width=18).pack(pady=4)

        ttk.Label(
            tab,
            text="Sıralama slayt sırasını belirler: ilk yerleşke her zaman "
                 "1. slayttır, özet tablosu 2. sıraya girer.",
            foreground="#666",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

    def _tab_account(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Hesap  ")
        self.var_brand = tk.StringVar()
        self.var_tagline = tk.StringVar()
        self.var_university = tk.StringVar()
        self.var_handle = tk.StringVar()
        for i, (label, var, hint) in enumerate((
            ("Marka adı", self.var_brand, "Slaytların sol üstünde görünür"),
            ("Alt başlık", self.var_tagline, "Marka adının altında"),
            ("Üniversite", self.var_university, "Resmî logonun alt metni"),
            ("Kullanıcı adı", self.var_handle, "Slaytların alt barında"),
        )):
            ttk.Label(tab, text=label).grid(row=i, column=0, sticky="w", **PAD)
            ttk.Entry(tab, textvariable=var, width=46).grid(
                row=i, column=1, sticky="w", **PAD)
            ttk.Label(tab, text=hint, foreground="#666").grid(
                row=i, column=2, sticky="w", **PAD)

    def _tab_instagram(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Instagram  ")
        self.var_ig_id = tk.StringVar()
        self.var_token = tk.StringVar()
        self.var_base = tk.StringVar()
        self.var_version = tk.StringVar()
        self.var_image_base = tk.StringVar()

        rows = (
            ("Hesap ID (IG_USER_ID)", self.var_ig_id, False),
            ("Erişim token'ı", self.var_token, True),
            ("Graph sunucusu", self.var_base, False),
            ("API sürümü", self.var_version, False),
            ("Görsel kök URL'i", self.var_image_base, False),
        )
        for i, (label, var, secret) in enumerate(rows):
            ttk.Label(tab, text=label).grid(row=i, column=0, sticky="w", **PAD)
            entry = ttk.Entry(tab, textvariable=var, width=58,
                              show="•" if secret else "")
            entry.grid(row=i, column=1, sticky="w", **PAD)
            if secret:
                self.token_entry = entry
                self.var_show_token = tk.BooleanVar(value=False)
                ttk.Checkbutton(
                    tab, text="Göster", variable=self.var_show_token,
                    command=lambda: self.token_entry.configure(
                        show="" if self.var_show_token.get() else "•"),
                ).grid(row=i, column=2, sticky="w", **PAD)

        ttk.Label(
            tab,
            text="Bu değerler yalnızca .env dosyasına yazılır; .env "
                 "gitignore'da olduğu için GitHub'a gönderilmez.\n"
                 "GitHub Actions bunları repo Secrets'tan okur — token'ı "
                 "değiştirirsen Secrets'ı da güncelle.",
            foreground="#666", justify="left",
        ).grid(row=len(rows), column=0, columnspan=3, sticky="w", **PAD)

    # ------------------------------------------------------- deger yukleme

    def _load_values(self) -> None:
        post = self.config_data.get("post", {})
        carousel = self.config_data.get("carousel", {})
        account = self.config_data.get("account", {})

        self.var_time.set(io.read_workflow_time())
        self.var_theme.set(self.config_data.get("theme", "light"))
        self.var_max.set(int(carousel.get("max_slides", 10)))
        self.var_summary.set(bool(carousel.get("include_summary_slide", True)))
        self.var_chart.set(bool(post.get("show_chart", True)))
        self.var_lines.set(int(post.get("caption_detail_lines", 10)))
        self.var_rain.set(int(post.get("rain_warning_percent", 50)))
        self.var_wind.set(int(post.get("wind_warning_kmh", 40)))
        self.txt_tags.delete("1.0", "end")
        self.txt_tags.insert("1.0", post.get("hashtags", ""))
        import caption as cap_mod
        self.txt_caption.delete("1.0", "end")
        self.txt_caption.insert("1.0", post.get("caption_template")
                                or cap_mod.DEFAULT_TEMPLATE)

        self.var_brand.set(account.get("brand", ""))
        self.var_tagline.set(account.get("tagline", ""))
        self.var_university.set(account.get("university", ""))
        self.var_handle.set(account.get("handle", ""))

        self.var_ig_id.set(self.env_data.get("IG_USER_ID", ""))
        self.var_token.set(self.env_data.get("IG_ACCESS_TOKEN", ""))
        self.var_base.set(self.env_data.get("GRAPH_BASE", ""))
        self.var_version.set(self.env_data.get("GRAPH_VERSION", "v26.0"))
        self.var_image_base.set(self.env_data.get("IMAGE_BASE_URL", ""))

        self._refresh_tree()
        self._update_cron_hint()

    def _refresh_tree(self, select: int | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.campuses):
            self.tree.insert(
                "", "end", iid=str(i),
                values=(i + 1, c.get("name", ""), c.get("subtitle", ""),
                        f"{c.get('lat', 0):.6f}", f"{c.get('lon', 0):.6f}",
                        "✓" if c.get("carousel") else "—"),
            )
        if select is not None and 0 <= select < len(self.campuses):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))
        self._update_slide_hint()

    def _update_cron_hint(self) -> None:
        try:
            cron = io.tr_time_to_cron(self.var_time.get())
            self.lbl_cron.configure(text=f"workflow cron: {cron}  (UTC)")
        except (ValueError, AttributeError):
            self.lbl_cron.configure(text="saat biçimi: SS:DD")

    def _update_slide_hint(self) -> None:
        in_carousel = sum(1 for c in self.campuses if c.get("carousel"))
        total = in_carousel + (1 if self.var_summary.get() else 0)
        limit = self.var_max.get()
        if total > limit:
            text = (f"{total} slayt gerekiyor, sınır {limit} — "
                    f"son {total - limit} yerleşke gönderiye girmeyecek.")
            color = "#B00020"
        else:
            text = f"{total} slayt üretilecek (sınır {limit})."
            color = "#2E7D32"
        self.lbl_slides.configure(text=text, foreground=color)

    # -------------------------------------------------------- yerleske ops

    def _selected(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def move_campus(self, delta: int) -> None:
        i = self._selected()
        if i is None:
            return
        j = i + delta
        if not 0 <= j < len(self.campuses):
            return
        self.campuses[i], self.campuses[j] = self.campuses[j], self.campuses[i]
        self._refresh_tree(select=j)

    def toggle_campus(self) -> None:
        i = self._selected()
        if i is None:
            return
        self.campuses[i]["carousel"] = not self.campuses[i].get("carousel")
        self._refresh_tree(select=i)

    def delete_campus(self) -> None:
        i = self._selected()
        if i is None:
            return
        name = self.campuses[i].get("name", "")
        if messagebox.askyesno("Sil", f"“{name}” silinsin mi?"):
            self.campuses.pop(i)
            self._refresh_tree(select=min(i, len(self.campuses) - 1))

    def add_campus(self) -> None:
        self._campus_dialog(None)

    def edit_campus(self) -> None:
        i = self._selected()
        if i is not None:
            self._campus_dialog(i)

    def _campus_dialog(self, index: int | None) -> None:
        data = (self.campuses[index] if index is not None
                else {"id": "", "name": "", "subtitle": "", "lat": 40.8,
                      "lon": 29.9, "carousel": False})

        win = tk.Toplevel(self)
        win.title("Yerleşke" if index is None else data.get("name", "Yerleşke"))
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)

        fields = {}
        for row, (key, label) in enumerate((
            ("id", "Kimlik (dosya adı)"), ("name", "Ad"),
            ("subtitle", "Alt başlık"), ("lat", "Enlem"), ("lon", "Boylam"),
        )):
            ttk.Label(win, text=label).grid(row=row, column=0, sticky="w", **PAD)
            var = tk.StringVar(value=str(data.get(key, "")))
            ttk.Entry(win, textvariable=var, width=44).grid(
                row=row, column=1, sticky="w", **PAD)
            fields[key] = var

        var_car = tk.BooleanVar(value=bool(data.get("carousel")))
        ttk.Checkbutton(win, text="Kendi slaytı olsun",
                        variable=var_car).grid(row=5, column=1, sticky="w",
                                               **PAD)

        def apply() -> None:
            try:
                lat = float(fields["lat"].get().replace(",", "."))
                lon = float(fields["lon"].get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Hata",
                                     "Enlem ve boylam sayı olmalı.", parent=win)
                return
            ident = fields["id"].get().strip() or fields["name"].get().strip().lower()
            if not ident or not fields["name"].get().strip():
                messagebox.showerror("Hata", "Kimlik ve ad boş olamaz.",
                                     parent=win)
                return
            record = {
                "id": ident,
                "name": fields["name"].get().strip(),
                "subtitle": fields["subtitle"].get().strip(),
                "lat": lat, "lon": lon, "carousel": var_car.get(),
            }
            if index is None:
                self.campuses.append(record)
                self._refresh_tree(select=len(self.campuses) - 1)
            else:
                self.campuses[index] = record
                self._refresh_tree(select=index)
            win.destroy()

        bar = ttk.Frame(win)
        bar.grid(row=6, column=0, columnspan=2, sticky="e", **PAD)
        ttk.Button(bar, text="İptal", command=win.destroy).pack(side="right",
                                                                padx=4)
        ttk.Button(bar, text="Tamam", command=apply).pack(side="right", padx=4)

    # ----------------------------------------------------------- kaydetme

    def collect(self) -> tuple[dict, dict, str]:
        cfg = dict(self.config_data)
        cfg["theme"] = self.var_theme.get()
        cfg["account"] = {
            "brand": self.var_brand.get(),
            "tagline": self.var_tagline.get(),
            "university": self.var_university.get(),
            "handle": self.var_handle.get(),
        }
        cfg["carousel"] = {
            "max_slides": int(self.var_max.get()),
            "include_summary_slide": bool(self.var_summary.get()),
        }
        cfg["post"] = {
            "time": self.var_time.get(),
            "hashtags": self.txt_tags.get("1.0", "end").strip(),
            "caption_template": self.txt_caption.get("1.0", "end").strip(),
            "show_chart": bool(self.var_chart.get()),
            "caption_detail_lines": int(self.var_lines.get()),
            "rain_warning_percent": int(self.var_rain.get()),
            "wind_warning_kmh": int(self.var_wind.get()),
        }
        cfg["campuses"] = self.campuses

        env = {
            "IG_USER_ID": self.var_ig_id.get().strip(),
            "IG_ACCESS_TOKEN": self.var_token.get().strip(),
            "GRAPH_BASE": self.var_base.get().strip(),
            "GRAPH_VERSION": self.var_version.get().strip(),
            "IMAGE_BASE_URL": self.var_image_base.get().strip(),
        }
        return cfg, env, self.var_time.get()

    def save_only(self) -> None:
        if self._save():
            self.set_status("Kaydedildi.")

    def _save(self) -> bool:
        try:
            io.tr_time_to_cron(self.var_time.get())
        except ValueError:
            messagebox.showerror("Hata", "Paylaşım saati SS:DD biçiminde olmalı.")
            return False
        if not self.campuses:
            messagebox.showerror("Hata", "En az bir yerleşke gerekli.")
            return False

        cfg, env, time_hhmm = self.collect()
        io.save_config(cfg)
        io.save_env(env)
        changed = io.write_workflow_time(time_hhmm)

        self.config_data = cfg
        self.env_data = env
        self.log("Ayarlar kaydedildi: config/campuses.json, .env"
                 + (", workflow zamanlaması" if changed else ""))
        return True

    # ------------------------------------------------------------ islemler

    def _run_async(self, title: str, work) -> None:
        if self.busy:
            return
        self.busy = True
        for b in (self.btn_preview, self.btn_check, self.btn_save,
                  self.btn_push):
            b.configure(state="disabled")
        self.set_status(title + "…")

        def runner() -> None:
            try:
                work()
            except Exception as exc:  # arayuz kapanmasin
                self.log(f"HATA: {exc}")
            finally:
                self.log_queue.put("__DONE__")

        threading.Thread(target=runner, daemon=True).start()

    def run_preview(self) -> None:
        if not self._save():
            return
        self._run_async("Önizleme üretiliyor", lambda: (
            run_command([sys.executable, "src/main.py", "--dry-run"], self.log),
            self.log("Görseller output/ klasöründe."),
        ))

    def run_preflight(self) -> None:
        self._run_async("Kurulum kontrol ediliyor", lambda: run_command(
            [sys.executable, "scripts/preflight.py"], self.log))

    def save_and_push(self) -> None:
        if not self._save():
            return
        if not messagebox.askyesno(
            "GitHub'a gönder",
            "Ayarlar GitHub'a gönderilecek ve yarınki otomatik paylaşım "
            "bu ayarlarla çalışacak.\n\nDevam edilsin mi?",
        ):
            return

        def work() -> None:
            run_command(["git", "add", "config", ".github", "src", "scripts",
                         "README.md"], self.log)
            code = run_command(
                ["git", "-c", "core.safecrlf=false", "commit", "-m",
                 "Ayarları güncelle (arayüz)"], self.log)
            if code != 0:
                self.log("Gönderilecek yeni değişiklik yok.")
                return
            if run_command(["git", "push", "origin", "main"], self.log) == 0:
                self.log("GitHub'a gönderildi.")
            else:
                self.log("Gönderim başarısız — günlüğe bak.")

        self._run_async("GitHub'a gönderiliyor", work)

    # --------------------------------------------------------------- log

    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _drain_log(self) -> None:
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if item == "__DONE__":
                self.busy = False
                for b in (self.btn_preview, self.btn_check, self.btn_save,
                          self.btn_push):
                    b.configure(state="normal")
                self.set_status("Hazır")
                continue
            self.log_text.configure(state="normal")
            self.log_text.insert("end", item + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(120, self._drain_log)


if __name__ == "__main__":
    App().mainloop()
