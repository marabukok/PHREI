# -*- coding: utf-8 -*-
"""

"""


import importlib
import subprocess
import sys

def ensure_package(pkg):
    try:
        importlib.import_module(pkg)
    except ImportError:
        print(f"Installing missing package: {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# Needed packages
for p in ["customtkinter", "numpy", "matplotlib", "pandas", "reportlab", "openpyxl"]:
    ensure_package(p)

import customtkinter
from tkinter import *
from tkinter import messagebox
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from io import StringIO
import pandas as pd
from datetime import datetime

# Try import reportlab for PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

from PHREIS_config import load_toml, apply_headless_config

initial_permeability_value = None

def notify(kind, title, msg):
    if HEADLESS:
        print(f"[{kind.upper()}] {title}: {msg}")
    else:
        if kind == "info":
            messagebox.showinfo(title, msg)
        elif kind == "warning":
            messagebox.showwarning(title, msg)
        else:
            messagebox.showerror(title, msg)

def safe_close_tk(win):
    """Cancel pending Tk 'after' callbacks and then close the window safely."""
    if win is None:
        return
    try:
        # Cancel all scheduled "after" callbacks for this Tcl interpreter
        for job in win.tk.call("after", "info"):
            try:
                win.after_cancel(job)
            except Exception:
                pass
    except Exception:
        pass

    # Quit the event loop (if running) then destroy
    try:
        win.quit()
    except Exception:
        pass
    try:
        win.destroy()
    except Exception:
        pass


import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--nogui", action="store_true", help="Run in headless mode")
parser.add_argument("--config", type=str, default="config.toml",
                    help="Path to TOML config file (used in --nogui mode)")

args = parser.parse_args()

HEADLESS = args.nogui
CONFIG_PATH = args.config

# Appearance
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

ENABLED_BG = None
DISABLED_BG = "#2f2f2f"

# ------------------------ Supported minerals defaults (M fixed, rho editable) ------------------------
SUPPORTED_DEFAULTS = {
    "Calcite":              {"M": 100.09, "rho": 2.71},
    "Fe(OH)3(a)":           {"M": 106.87, "rho": 3.40},
    "Gypsum":               {"M": 172.178, "rho": 2.317},
    "Barite":               {"M": 233.426, "rho": 4.480},
    "Halite":               {"M": 58.448,  "rho": 2.163},
    "Quartz":               {"M": 60.09,  "rho": 2.648},
    "Siderite":             {"M": 115.86, "rho": 3.96},
    "Dolomite":             {"M": 184.40, "rho": 2.85},
    "Aragonite":            {"M": 100.09, "rho": 2.93},
    "Fluorite":             {"M": 78.08,  "rho": 3.181},
    "Celestite":            {"M": 183.693, "rho": 3.972},
    "Hematite":             {"M": 159.70, "rho": 5.274},
    "Magnetite":            {"M": 231.55, "rho": 5.200},
    "Pyrite":               {"M": 120.082, "rho": 5.016},
    "Chalcedony":           {"M": 60.08,  "rho": 2.60},
    "SiO2(a)":              {"M": 60.08,  "rho": 2.196},
    "Anhydrite":            {"M": 136.146, "rho": 2.963},
}


from tkinter import filedialog

# --- Mineral defaults (single source of truth) ---
# SUPPORTED_DEFAULTS = {
    # # (M in g/mol) , (rho in g/cm^3)
    # "Calcite":    {"M": 100.0869, "rho": 2.71},
    # "Fe(OH)3(a)": {"M": 106.867,  "rho": 3.40},
    # # add more if you want them to appear in the dropdown:
    # # "Gypsum":     {"M": 172.171,  "rho": 2.32},
    # # "Barite":     {"M": 233.39,   "rho": 4.48},
# }

if not HEADLESS:


    precip_gui = customtkinter.CTk()
    precip_gui.title("Precipitating minerals & PHREEQC paths")
    precip_gui.geometry("760x600")

    wrap = customtkinter.CTkScrollableFrame(precip_gui, width=740, height=550)
    wrap.pack(fill="both", expand=True, padx=10, pady=10)

    # PHREEQC executable path
    customtkinter.CTkLabel(wrap, text="PHREEQC executable path:").grid(row=0, column=0, sticky="w", padx=6, pady=(6,4))
    exe_entry = customtkinter.CTkEntry(wrap, width=520)
    exe_entry.grid(row=0, column=1, columnspan=3, sticky="w", padx=6, pady=(6,4))
    exe_entry.insert(0, r"C:/phreeqc/phreeqc.exe")
    customtkinter.CTkButton(wrap, text="Browse…",
                            command=lambda: (lambda p=filedialog.askopenfilename(title="Select phreeqc.exe",
                                                                                filetypes=[("Executable","*.exe"),("All files","*.*")]):
                                             (exe_entry.delete(0,"end"), exe_entry.insert(0,p)) if p else None)()
                            ).grid(row=0, column=4, padx=6, pady=(6,4), sticky="w")

    # Database path
    customtkinter.CTkLabel(wrap, text="Database file path:").grid(row=1, column=0, sticky="w", padx=6, pady=(4,8))
    db_entry = customtkinter.CTkEntry(wrap, width=520)
    db_entry.grid(row=1, column=1, columnspan=3, sticky="w", padx=6, pady=(4,8))
    db_entry.insert(0, r"C:/phreeqc/database/PHREEQC.DAT")
    customtkinter.CTkButton(wrap, text="Browse…",
                            command=lambda: (lambda p=filedialog.askopenfilename(title="Select PHREEQC database",
                                                                                filetypes=[("PHREEQC databases","*.dat;*.DAT"),("All files","*.*")]):
                                             (db_entry.delete(0,"end"), db_entry.insert(0,p)) if p else None)()
                            ).grid(row=1, column=4, padx=6, pady=(4,8), sticky="w")

    # Info
    customtkinter.CTkLabel(
        wrap,
        text="Pick up to three minerals to precipitate. If none selected, Calcite and Fe(OH)3(a) are used by default."
    ).grid(row=2, column=0, columnspan=5, sticky="w", padx=6, pady=(2,10))
    customtkinter.CTkLabel(
        wrap,
        text="Molar masses are fixed (Robie & Bethke, 1983). Densities (g/cm³) are user-editable."
    ).grid(row=3, column=0, columnspan=5, sticky="w", padx=6, pady=(0,10))

    # ---- Mineral table in its own frame so headers always align and stay visible
    table = customtkinter.CTkFrame(wrap)
    table.grid(row=4, column=0, columnspan=5, sticky="we", padx=6, pady=(4,6))
    table.grid_columnconfigure(0, weight=1)
    table.grid_columnconfigure(1, weight=0)
    table.grid_columnconfigure(2, weight=0)

    # Headers (bold)
    header_font = ("TkDefaultFont", 11, "bold")
    customtkinter.CTkLabel(table, text="Mineral", font=header_font).grid(row=0, column=0, padx=(6,10), pady=(4,6), sticky="w")
    customtkinter.CTkLabel(table, text="Molar weight (g/mol)", font=header_font).grid(row=0, column=1, padx=(6,10), pady=(4,6), sticky="w")
    customtkinter.CTkLabel(table, text="Density (g/cm³)", font=header_font).grid(row=0, column=2, padx=(6,10), pady=(4,6), sticky="w")

    # Options and selectors
    opt_values = ["(none)"] + sorted(list(SUPPORTED_DEFAULTS.keys()))
    selectors = []
    for r in range(3):
        row = r + 1
        default_name = "Calcite" if r == 0 else ("Fe(OH)3(a)" if r == 1 else "(none)")

        # Mineral dropdown
        sel_var = StringVar(value=default_name)
        menu = customtkinter.CTkOptionMenu(table, variable=sel_var, values=opt_values, width=220)
        menu.grid(row=row, column=0, padx=(6,10), pady=6, sticky="w")

        # Molar weight (read-only)
        m_entry = customtkinter.CTkEntry(table, width=150, state="disabled")
        if default_name in SUPPORTED_DEFAULTS:
            m_entry.configure(state="normal")
            m_entry.insert(0, str(SUPPORTED_DEFAULTS[default_name]["M"]))
            m_entry.configure(state="disabled")
        m_entry.grid(row=row, column=1, padx=(6,10), pady=6, sticky="w")

        # Density (editable)
        rho_entry = customtkinter.CTkEntry(table, width=150)
        if default_name in SUPPORTED_DEFAULTS:
            rho_entry.insert(0, str(SUPPORTED_DEFAULTS[default_name]["rho"]))
        rho_entry.grid(row=row, column=2, padx=(6,10), pady=6, sticky="w")

        # Update fields when mineral changes
        def _on_change(_=None, sv=sel_var, me=m_entry, re=rho_entry):
            name = sv.get()
            me.configure(state="normal"); me.delete(0, "end")
            re.delete(0, "end")
            if name in SUPPORTED_DEFAULTS:
                me.insert(0, str(SUPPORTED_DEFAULTS[name]["M"]))
                me.configure(state="disabled")
                re.insert(0, str(SUPPORTED_DEFAULTS[name]["rho"]))
            else:
                me.insert(0, ""); me.configure(state="disabled")
                re.insert(0, "")
        menu.configure(command=_on_change)

        selectors.append({"sel": sel_var, "M": m_entry, "rho": rho_entry})

    # Save button (bottom, with a bit more space)
    def save_precip_paths():
        import os
        global mineral_props, selout_names, minerals_title, PHREEQC_PATH, DATABASE

        PHREEQC_PATH = exe_entry.get().strip()
        DATABASE     = db_entry.get().strip()

        if not os.path.isfile(PHREEQC_PATH):
            notify("PHREEQC path", f"Executable not found:\n{PHREEQC_PATH}")
            return
        if not os.path.isfile(DATABASE):
            notify("Database path", f"Database file not found:\n{DATABASE}")
            return

        mineral_props = {}
        selout_names = []
        for s in selectors:
            name = s["sel"].get()
            if name and name != "(none)":
                try:
                    rho = float(s["rho"].get())
                except Exception:
                    rho = SUPPORTED_DEFAULTS[name]["rho"]
                mineral_props[name] = {"M": SUPPORTED_DEFAULTS[name]["M"], "rho": rho}
                selout_names.append(name)

        if not selout_names:
            mineral_props = {
                "Calcite":    {"M": SUPPORTED_DEFAULTS["Calcite"]["M"],    "rho": SUPPORTED_DEFAULTS["Calcite"]["rho"]},
                "Fe(OH)3(a)": {"M": SUPPORTED_DEFAULTS["Fe(OH)3(a)"]["M"], "rho": SUPPORTED_DEFAULTS["Fe(OH)3(a)"]["rho"]},
            }
            selout_names = ["Calcite", "Fe(OH)3(a)"]

        minerals_title = ", ".join(selout_names)
        notify("info","Saved","Settings saved.\n\n"
        f"PHREEQC: {PHREEQC_PATH}\n"
        f"Database: {DATABASE}\n"
        f"Minerals: {minerals_title}"
        )
        safe_close_tk(precip_gui)

    customtkinter.CTkButton(wrap, text="Save", command=save_precip_paths)\
        .grid(row=5, column=0, columnspan=5, pady=(10,6))
    precip_gui.mainloop()


else:
    
    
    # defaults that GUI would have set:
    PHREEQC_PATH = r"C:\Program Files\USGS\phreeqc-3.8.8-17347-x64\bin\Release\phreeqc.exe"
    DATABASE     = r"C:\Program Files\USGS\phreeqc-3.8.8-17347-x64\database\phreeqc.dat"

    mineral_props = {
        "Calcite":    {"M": SUPPORTED_DEFAULTS["Calcite"]["M"],    "rho": SUPPORTED_DEFAULTS["Calcite"]["rho"]},
        "Fe(OH)3(a)": {"M": SUPPORTED_DEFAULTS["Fe(OH)3(a)"]["M"], "rho": SUPPORTED_DEFAULTS["Fe(OH)3(a)"]["rho"]},
    }
    selout_names = list(mineral_props.keys())
    minerals_title = ", ".join(selout_names)
    

# ------------------------ Production Well GUI (scrollable) ------------------------


prod_labels = [
    "ID: ", "Production temperature (°C):", "pH: ", "Ca²⁺: ", "Na⁺: ", "K⁺: ",
    "S²⁻: ", "S⁶⁺ as SO₄²⁻: ", "F⁻: ", "Cl⁻: ", "Br⁻: ", "Li⁺: ", "Mg²⁺: ",
    "Fe²⁺: ", "Fe³⁺: ", "Mn: ", "Si as H₂SiO₃: ", "Zn: ", "Ba: ", "Pb: ", "Alkalinity as HCO₃⁻: "
]
prod_keys = [
    "IDP","TP","pHP","CaP","NaP","KP","S2P","S6P","FP","ClP","BrP","LiP",
    "MgP","Fe2P","Fe3P","MnP","SiP","ZnP","BaP","PbP","AlkP"
]

# Defaults (your requested values)
prod_defaults = {
    "IDP": "Production_well",
    "TP":  "76.9",
    "pHP": "7.5",
    "S2P": "0.03",
    "S6P": "20.0",
    "FP":  "1.7",
    "ClP": "268.0",
    "BrP": "2.2",
    "LiP": "0.55",
    "NaP": "1860.0",
    "KP":  "30.0",
    "CaP": "13.7",
    "MgP": "3.7",
    "Fe3P":"0.0",
    "Fe2P":"7.5",
    "MnP": "0.1",
    "SiP": "79.0",
    "ZnP": "0.059",
    "BaP": "1.98",
    "PbP": "0.0",
    "AlkP":"4470.0"
}

if not HEADLESS:

    compositionP = customtkinter.CTk()
    compositionP.title("Composition of Production well fluid")
    compositionP.geometry("520x560")

    scrollP = customtkinter.CTkScrollableFrame(compositionP, width=500, height=510)
    scrollP.pack(fill="both", expand=True, padx=10, pady=10)

    # Units
    customtkinter.CTkLabel(scrollP, text="Units:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
    units_var_prod = StringVar(value="mg/L")
    units_menu_prod = customtkinter.CTkOptionMenu(
        scrollP, variable=units_var_prod,
        values=["mg/L","g/L","ppm","ppb","mol/L","mmol/L","mol/kgs","mmol/kgs"]
    )
    units_menu_prod.grid(row=0, column=1, padx=6, pady=6, sticky="w")

    # Build entries and load defaults
    prod_entries = {}
    for i, text in enumerate(prod_labels):
        customtkinter.CTkLabel(scrollP, text=text).grid(row=i+1, column=0, padx=6, pady=3, sticky="w")
        entry = Entry(scrollP, width=28, borderwidth=3)
        entry.grid(row=i+1, column=1, padx=6, pady=3, sticky="w")
        entry.insert(0, prod_defaults.get(prod_keys[i], "0"))
        prod_entries[prod_keys[i]] = entry

    def _set_prod_defaults():
        """Reload default values into the Production form."""
        for k, entry in prod_entries.items():
            entry.delete(0, END)
            entry.insert(0, prod_defaults.get(k, "0"))

    def clearprod():
        """Clear all Production entry fields."""
        for entry in prod_entries.values():
            entry.delete(0, END)

    def regcompprod():
        """Save Production values to globals and close the window."""
        global IDP, CaP, NaP, KP, pHP, TP, S2P, S6P, FP, ClP, BrP, LiP, MgP, Fe2P, Fe3P, MnP, SiP, ZnP, BaP, PbP, AlkP, unit_selected_prod
        for name in prod_entries:
            globals()[name] = prod_entries[name].get()
        unit_selected_prod = units_var_prod.get()
        notify("info","Success",f"Production well ({IDP}) fluid composition saved")
        safe_close_tk(compositionP)

    # Buttons (Save / Clear / Reset)
    btn_frameP = customtkinter.CTkFrame(scrollP)
    btn_frameP.grid(row=len(prod_labels)+2, column=0, columnspan=2, pady=(10, 16))

    customtkinter.CTkButton(btn_frameP, text="Save", command=regcompprod).pack(side="left", padx=6)
    customtkinter.CTkButton(btn_frameP, text="Clear", command=clearprod).pack(side="left", padx=6)
    customtkinter.CTkButton(btn_frameP, text="Reset defaults", command=_set_prod_defaults).pack(side="left", padx=6)

    compositionP.mainloop()
else:
    unit_selected_prod = "mg/L"
    for k, v in prod_defaults.items():
        globals()[k] = v


# ------------------------ Injection Well GUI (scrollable) ------------------------

inj_labels = [
    "ID: ", "Reservoir temperature (°C):", "pH: ", "Ca²⁺: ", "Na⁺: ","K⁺: ",
    "S²⁻: ", "S⁶⁺ as SO₄²⁻:", "F⁻: ", "Cl⁻: ", "Br⁻: ", "Li⁺: ", "Mg²⁺: ",
    "Fe²⁺: ", "Fe³⁺: ", "Mn: ", "Si as H₂SiO₃: ", "Zn: ", "Ba²⁺: ", "Pb: ", "Alkalinity as HCO₃⁻:"
]
inj_keys = [
    "IDI","RT","pHI","CaI","NaI","KI","S2I","S6I","FI","ClI","BrI","LiI",
    "MgI","Fe2I","Fe3I","MnI","SiI","ZnI","BaI","PbI","AlkI"
]

# Defaults from PHREEQC block (units mg/L)
inj_defaults = {
    "IDI":  "Injection_well",
    "RT":   "100",
    "pHI":  "7.5",
    "CaI":  "17.2",
    "NaI":  "1770",
    "KI":   "28",
    "S2I":  "0.0001",
    "S6I":  "19",
    "FI":   "1.56",
    "ClI":  "148",
    "BrI":  "2.6",
    "LiI":  "0.49",
    "MgI":  "5.9",
    "Fe2I": "4.8",
    "Fe3I": "0",
    "MnI":  "0.09",
    "SiI":  "79",
    "ZnI":  "0.2",
    "BaI":  "1.99",
    "PbI":  "0",
    "AlkI": "4570"
}


if not HEADLESS:

    compositionI = customtkinter.CTk()
    compositionI.title("Composition of Injection well (reservoir) fluid")
    compositionI.geometry("520x560")

    scrollI = customtkinter.CTkScrollableFrame(compositionI, width=500, height=510)
    scrollI.pack(fill="both", expand=True, padx=10, pady=10)

    # Units
    customtkinter.CTkLabel(scrollI, text="Units:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
    units_var_inj = StringVar(value="mg/L")
    units_menu_inj = customtkinter.CTkOptionMenu(
        scrollI, variable=units_var_inj,
        values=["mg/L","g/L","ppm","ppb","mol/L","mmol/L","mol/kgs","mmol/kgs"]
    )
    units_menu_inj.grid(row=0, column=1, padx=6, pady=6, sticky="w")


    # Build entries and load defaults
    inj_entries = {}
    for i, text in enumerate(inj_labels):
        customtkinter.CTkLabel(scrollI, text=text).grid(row=i+1, column=0, padx=6, pady=3, sticky="w")
        entry = Entry(scrollI, width=28, borderwidth=3)
        entry.grid(row=i+1, column=1, padx=6, pady=3, sticky="w")
        entry.insert(0, inj_defaults.get(inj_keys[i], "0"))
        inj_entries[inj_keys[i]] = entry

    def _set_inj_defaults():
        """Reload default values into the form."""
        for k, entry in inj_entries.items():
            entry.delete(0, END)
            entry.insert(0, inj_defaults.get(k, "0"))

    def regcompinj():
        """Save values to globals and close the window."""
        global IDI, CaI, NaI, KI, pHI, RT, S2I, S6I, FI, ClI, BrI, LiI, MgI, Fe2I, Fe3I, MnI, SiI, ZnI, BaI, PbI, AlkI, unit_selected_inj
        for name in inj_entries:
            globals()[name] = inj_entries[name].get()
        unit_selected_inj = units_var_inj.get()
        notify("info","Success",f"Injection well ({IDI}) fluid composition saved")
        safe_close_tk(compositionI)
        

    def clearinj():
        """Clear all entry fields."""
        for entry in inj_entries.values():
            entry.delete(0, END)

    # Buttons (Save / Clear / Reset)
    btn_frame = customtkinter.CTkFrame(scrollI)
    btn_frame.grid(row=len(inj_labels)+2, column=0, columnspan=2, pady=(10, 16))

    customtkinter.CTkButton(btn_frame, text="Save", command=regcompinj).pack(side="left", padx=6)
    customtkinter.CTkButton(btn_frame, text="Clear", command=clearinj).pack(side="left", padx=6)
    customtkinter.CTkButton(btn_frame, text="Reset defaults", command=_set_inj_defaults).pack(side="left", padx=6)

    compositionI.mainloop()
else:
    unit_selected_inj = "mg/L"
    for k, v in inj_defaults.items():
        globals()[k] = v


# ------------------------ Gas Composition GUI (scrollable) ------------------------


# Default values (typical air + 0 CH4)
gas_defaults = {
    "O2":  0.73,   # %
    "N2":  3.373,   # %
    "CH4": 82.72,    # %
    "CO2": 14.47    # %
}

gas_labels = [
    ("Oxygen (%): ", "O2"),
    ("Nitrogen (%): ", "N2"),
    ("Methane (%): ", "CH4"),
    ("Carbon-dioxide (%): ", "CO2")
]

if not HEADLESS:
    
    composition_gas = customtkinter.CTk()
    composition_gas.title("Composition of Reservoir Gas - Separated Gas in %")
    composition_gas.geometry("460x300")

    scrollG = customtkinter.CTkScrollableFrame(composition_gas, width=440, height=240)
    scrollG.pack(fill="both", expand=True, padx=10, pady=10)

    gas_entries = {}
    for i, (label, key) in enumerate(gas_labels):
        customtkinter.CTkLabel(scrollG, text=label).grid(row=i, column=0, padx=6, pady=6, sticky="w")
        entry = Entry(scrollG, width=28, borderwidth=3)
        entry.grid(row=i, column=1, padx=6, pady=6, sticky="w")
        entry.insert(0, str(gas_defaults[key]))
        gas_entries[key] = entry

    def clear_fields():
        """Clear all gas composition fields."""
        for e in gas_entries.values():
            e.delete(0, END)

    def reset_defaults():
        """Reset fields to the default percentages."""
        for key, e in gas_entries.items():
            e.delete(0, END)
            e.insert(0, str(gas_defaults[key]))

    def regcompgas():
        """Save values to globals and close window."""
        global O2, N2, CH4, CO2
        O2  = gas_entries["O2"].get()
        N2  = gas_entries["N2"].get()
        CH4 = gas_entries["CH4"].get()
        CO2 = gas_entries["CO2"].get()
        notify("info","Success",f"Reservoir gas composition saved")
        safe_close_tk(composition_gas)
else:
    O2  = gas_defaults["O2"]
    N2  = gas_defaults["N2"]
    CH4 = gas_defaults["CH4"]
    CO2 = gas_defaults["CO2"]
    
# ------------------------ Mineral Selector GUI (multi-select with scrollbar) ------------------------

minerals = [
"Al(OH)3(a)", "Albite", "Alunite", "Anhydrite", "Anglesite", "Anorthite",
"Aragonite", "Barite", "Calcite", "Ca-Montmorillonite", "Celestite", "Cerussite",
"Chalcedony", "Chlorite(14A)", "Chrysotile", "Cd(OH)2", "CdSiO3", "CdSO4",
"Dolomite", "Fe(OH)3(a)", "FeS(ppt)", "Fluorite", "Gibbsite", "Gypsum",
"Halite", "Hausmannite", "Hematite", "Hydroxyapatite", "Illite", "Jarosite-K",
"K-feldspar", "K-mica", "Kaolinite", "Magnetite", "Mackinawite", "Melanterite",
"Manganite", "Otavite", "Pyrite", "Pyrochroite", "Pyrolusite", "Quartz",
"Rhodochrosite", "Sepiolite", "Sepiolite(d)", "Siderite", "SiO2(a)",
"Smithsonite", "Sphalerite", "Strontianite", "Sulfur", "Sylvite", "Talc",
"Vivianite", "Willemite", "Witherite", "Zn(OH)2(e)"
]

# --- Default selected minerals ---
default_minerals =  ["Quartz", "Calcite", "Albite", "Illite", "Chlorite(14A)", "K-mica", "Dolomite"]

def kozeny_carman_perm(phi, d, sphericity):
    """
    Permeability k [m^2] via Kozeny–Carman:
        k = (s^2 / 180) * (phi^3 * d^2) / (1 - phi)^2
    where s = sphericity (-), d = grain size [m], phi = porosity [-].
    """
    phi = max(1e-8, min(0.999999, float(phi)))
    C = (sphericity**2) / 180.0
    return C * (phi**3) * (d**2) / (1.0 - phi)**2

def invert_porosity_from_perm(k_target, d, sphericity, tol=1e-10, maxit=200):
    """
    Solve for porosity phi in (0,1) such that kozeny_carman_perm(phi, d, s) = k_target.
    Bisection with clamping if out of range.
    """
    k_target = max(1e-22, float(k_target))
    lo, hi = 1e-8, 0.999999
    f_lo = kozeny_carman_perm(lo, d, sphericity) - k_target
    f_hi = kozeny_carman_perm(hi, d, sphericity) - k_target
    if f_lo >= 0:
        return lo
    if f_hi <= 0:
        return hi
    for _ in range(maxit):
        mid = 0.5*(lo+hi)
        f_mid = kozeny_carman_perm(mid, d, sphericity) - k_target
        if abs(f_mid) < tol or (hi-lo) < 1e-12:
            return mid
        if f_mid > 0:
            hi = mid
        else:
            lo = mid
    return 0.5*(lo+hi)


if not HEADLESS:
    
    # Buttons row
    btn_row = len(gas_labels) + 1
    customtkinter.CTkButton(scrollG, text="Clear", command=clear_fields).grid(row=btn_row, column=0, padx=6, pady=(10, 12), sticky="w")
    customtkinter.CTkButton(scrollG, text="Reset defaults", command=reset_defaults).grid(row=btn_row, column=1, padx=6, pady=(10, 12), sticky="w")
    customtkinter.CTkButton(scrollG, text="Save", command=regcompgas).grid(row=btn_row+1, column=0, columnspan=2, pady=(4, 12))
    composition_gas.mainloop()
    reservoir = customtkinter.CTk()
    reservoir.title("Mineral Selector")
    reservoir.geometry("480x560")
    customtkinter.CTkLabel(reservoir, text="Select up to 8 minerals for reservoir composition").pack(pady=(10, 6))
    list_wrap = customtkinter.CTkFrame(reservoir)
    list_wrap.pack(fill="both", expand=True, padx=10, pady=8)
    listbox = Listbox(list_wrap, selectmode="multiple", height=18, width=34)
    listbox.grid(row=0, column=0, sticky="nsew")
    ysb = Scrollbar(list_wrap, orient="vertical", command=listbox.yview)
    ysb.grid(row=0, column=1, sticky="ns")
    listbox.configure(yscrollcommand=ysb.set)
    list_wrap.grid_columnconfigure(0, weight=1)
    list_wrap.grid_rowconfigure(0, weight=1)

    # --- Available minerals ---
    for m in minerals:
        listbox.insert(END, m)

    def set_default_selection():
        listbox.selection_clear(0, END)
        for dm in default_minerals:
            if dm in minerals:
                idx = minerals.index(dm)
                listbox.selection_set(idx)

    # init default selection
    set_default_selection()

    def get_selected_minerals():
        selected_indices = listbox.curselection()
        selected_minerals = [minerals[i] for i in selected_indices]
        while len(selected_minerals) < 8:
            selected_minerals.append('#')
        for i, mineral in enumerate(selected_minerals[:8], start=1):
            globals()[f'reservoir_mineral_{i}'] = mineral
        notify("info","Success",f"Minerals for reservoir composition saved")
        safe_close_tk(reservoir)

    def clear_selection():
        listbox.selection_clear(0, END)

    # --- Buttons ---
    btn_frame = customtkinter.CTkFrame(reservoir)
    btn_frame.pack(pady=(10, 12))

    customtkinter.CTkButton(btn_frame, text="Clear", command=clear_selection).pack(side="left", padx=6)
    customtkinter.CTkButton(btn_frame, text="Reset defaults", command=set_default_selection).pack(side="left", padx=6)
    customtkinter.CTkButton(btn_frame, text="Save selection", command=get_selected_minerals).pack(side="left", padx=6)

    reservoir.mainloop()

    # Guarantee all 8 slots exist

    for i in range(1,9):
        if f'reservoir_mineral_{i}' not in globals():
            globals()[f'reservoir_mineral_{i}'] = '#'
else:
    selected = list(default_minerals)[:8]
    while len(selected) < 8:
        selected.append("#")
    for i, mineral in enumerate(selected, start=1):
        globals()[f"reservoir_mineral_{i}"] = mineral


#======================== PARAMETERS & MODEL SETUP (with locked stochastic panel) ========================
# Defaults
    # flowrate         = float(defaults[0])
    # nw_diameter_out  = float(defaults[1])
    # wb_diameter_out  = float(defaults[2])
    # sphericity       = float(defaults[3])
    # grainsize        = float(defaults[4])
    # screened_length  = float(defaults[5])
    # reinjection_temp = float(defaults[6])
    # reservoir_temp   = float(defaults[7])
defaults = ["350", "0.22", "0.114", "1.0", "0.0015", "75.5", "50", "100"]


if not  HEADLESS:
    

    window = customtkinter.CTk()
    window.title("Parameters & Model setup")
    window.geometry("1000x820")

    scroll_frame = customtkinter.CTkScrollableFrame(window, width=880, height=620)
    scroll_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    footer = customtkinter.CTkFrame(window)
    footer.pack(fill="x", padx=10, pady=(6, 10))

    # ---------- Helpers: physics + inversion ----------
 
    # ---------- Single source of truth inputs (shared) ----------
    params_labels = [
        "Flow rate (l/min):",
        "Near-wellbore zone outer diameter (m):",
        "Wellbore outer diameter (m):",
        "Sphericity:",
        "Average grain size of gravel pack (m):",
        "Screened length (m):",
        "Reinjection temperature (°C):",
        "Reservoir temperature (°C):"
    ]
    params_entries = {}
    for i, text in enumerate(params_labels):
        customtkinter.CTkLabel(scroll_frame, text=text).grid(row=i, column=0, sticky="w", padx=6, pady=6)
        e = customtkinter.CTkEntry(scroll_frame, width=260)
        e.grid(row=i, column=1, sticky="w", padx=6, pady=6)
        params_entries[text] = e

    # Defaults
    defaults = ["350", "0.22", "0.114", "1.0", "0.0015", "75.5", "25", "100"]


    for (key, val) in zip(params_entries, defaults):
        params_entries[key].insert(0, val)

    # ---------- Choice: user provides initial Porosity OR initial Permeability ----------
    row0 = len(params_labels)
    customtkinter.CTkLabel(scroll_frame, text="Initial state input mode:").grid(
        row=row0, column=0, sticky="w", padx=6, pady=(12,6)
    )
    mode_var = StringVar(value="porosity")  # "porosity" or "permeability"
    rb_mode_phi = customtkinter.CTkRadioButton(scroll_frame, text="Give initial porosity (%)", variable=mode_var, value="porosity")
    rb_mode_k   = customtkinter.CTkRadioButton(scroll_frame, text="Give initial permeability (m²)", variable=mode_var, value="permeability")
    rb_mode_phi.grid(row=row0, column=1, sticky="w", padx=6, pady=(12,6))
    rb_mode_k.grid(  row=row0, column=2, sticky="w", padx=6, pady=(12,6))

    # Entries for the two alternative inputs
    customtkinter.CTkLabel(scroll_frame, text="Initial porosity (%):").grid(
        row=row0+1, column=0, sticky="w", padx=6, pady=6
    )
    e_phi_input = customtkinter.CTkEntry(scroll_frame, width=260)
    e_phi_input.grid(row=row0+1, column=1, sticky="w", padx=6, pady=6)
    e_phi_input.insert(0, "30")  # default when in porosity mode

    customtkinter.CTkLabel(scroll_frame, text="Initial permeability (m²):").grid(
        row=row0+2, column=0, sticky="w", padx=6, pady=6
    )
    e_k_input = customtkinter.CTkEntry(scroll_frame, width=260)
    e_k_input.grid(row=row0+2, column=1, sticky="w", padx=6, pady=6)
    e_k_input.insert(0, "1e-9")  # typical order

    def _update_initial_permeability(event=None):
        global initial_permeability_value
        try:
            initial_permeability_value = float(e_k_input.get())
        except (ValueError, TypeError):
            initial_permeability_value = None

    e_k_input.bind("<KeyRelease>", _update_initial_permeability)


    def _toggle_initial_mode(*_):
        m = mode_var.get()
        e_phi_input.configure(state="normal" if m=="porosity" else "disabled")
        e_k_input.configure(state="normal" if m=="permeability" else "disabled")
    mode_var.trace_add("write", _toggle_initial_mode)
    _toggle_initial_mode()

    # ---------- Air contact checkbox ----------
    checkbox_var = IntVar(value=0)
    fluid_air_contact = "#"
    def update_fluid_air_contact():
        global fluid_air_contact
        if checkbox_var.get():
            fluid_air_contact = """
    use solution 1

    GAS_PHASE 1
    -fixed pressure
    -pressure    1.013
    -temperature 20
    O2(g) 0.21224
    CO2(g) 0.0004052
    N2(g) 0.7904

    end
    Save solution 1
    """
        else:
            fluid_air_contact = "#"

    customtkinter.CTkCheckBox(
        scroll_frame, text="System is open to air",
        variable=checkbox_var, command=update_fluid_air_contact
    ).grid(row=row0+3, column=0, columnspan=2, pady=(8, 14), sticky="w")

    # ---------- Model type ----------
    model_row = row0 + 4
    customtkinter.CTkLabel(scroll_frame, text="Model type:").grid(row=model_row, column=0, padx=6, pady=6, sticky="w")
    model_var = StringVar(value="deterministic")
    rb_det = customtkinter.CTkRadioButton(scroll_frame, text="Deterministic", variable=model_var, value="deterministic")
    rb_sto = customtkinter.CTkRadioButton(scroll_frame, text="Stochastic",   variable=model_var, value="stochastic")
    rb_det.grid(row=model_row, column=1, padx=6, pady=6, sticky="w")
    rb_sto.grid(row=model_row, column=2, padx=6, pady=6, sticky="w")

    # ---------- Stochastic panel (means read-only; everything locked unless 'Stochastic') ----------
    sto_frame = customtkinter.CTkFrame(scroll_frame)
    sto_frame.grid(row=model_row+1, column=0, columnspan=4, sticky="we", padx=6, pady=(4,12))
    sto_frame.grid_columnconfigure(5, weight=1)

    customtkinter.CTkLabel(sto_frame, text="Stochastic parameters (enable + choose distribution):").grid(
        row=0, column=0, columnspan=6, sticky="w", padx=6, pady=(10,6)
    )
    customtkinter.CTkLabel(sto_frame, text="Enable").grid(row=1, column=0, padx=6, pady=(0,4))
    customtkinter.CTkLabel(sto_frame, text="Distribution").grid(row=1, column=1, padx=6, pady=(0,4))
    customtkinter.CTkLabel(sto_frame, text="Mean (auto, read-only)").grid(row=1, column=2, padx=6, pady=(0,4))
    customtkinter.CTkLabel(sto_frame, text="Std").grid(row=1, column=3, padx=6, pady=(0,4))
    customtkinter.CTkLabel(sto_frame, text="Min").grid(row=1, column=4, padx=6, pady=(0,4))
    customtkinter.CTkLabel(sto_frame, text="Max").grid(row=1, column=5, padx=6, pady=(0,4))

    ENABLED_BG = None
    DISABLED_BG = "#2f2f2f"

    def _set_widget_enabled(w, enabled: bool):
        st = "normal" if enabled else "disabled"
        try: w.configure(state=st)
        except Exception: pass
        try: w.configure(fg_color=(ENABLED_BG if enabled else DISABLED_BG))
        except Exception: pass
        try:
            if not enabled:
                w.configure(button_color=DISABLED_BG, button_hover_color=DISABLED_BG)
            else:
                w.configure(button_color=None, button_hover_color=None)
        except Exception: pass

    def make_sto_row_linked(row, label_text, link_entry, default_std=0, default_min=0, default_max=0, default_dist="normal"):
        """Mean mirrors a top entry; read-only; auto-updates on change."""
        active = IntVar(value=0)
        chk = customtkinter.CTkCheckBox(sto_frame, text=label_text, variable=active)
        chk.grid(row=row, column=0, sticky="w", padx=6, pady=4)

        dist = StringVar(value=default_dist)
        menu = customtkinter.CTkOptionMenu(sto_frame, variable=dist, values=["normal","lognormal","uniform"])
        menu.grid(row=row, column=1, padx=6, pady=4)

        e_mean = customtkinter.CTkEntry(sto_frame, width=100, state="disabled")
        e_mean.grid(row=row, column=2, padx=4)

        def refresh():
            e_mean.configure(state="normal")
            e_mean.delete(0, END)
            e_mean.insert(0, link_entry.get())
            e_mean.configure(state="disabled")

        for ev in ("<KeyRelease>", "<FocusOut>"):
            try: link_entry.bind(ev, lambda *_: refresh())
            except Exception: pass
        refresh()

        e_std  = customtkinter.CTkEntry(sto_frame, width=90); e_std.insert(0, str(default_std)); e_std.grid(row=row, column=3, padx=4)
        e_min  = customtkinter.CTkEntry(sto_frame, width=90); e_min.insert(0, str(default_min)); e_min.grid(row=row, column=4, padx=4)
        e_max  = customtkinter.CTkEntry(sto_frame, width=90); e_max.insert(0, str(default_max)); e_max.grid(row=row, column=5, padx=4)

        return {"active": active, "chk": chk, "dist": dist, "menu": menu, "mean": e_mean, "std": e_std, "min": e_min, "max": e_max, "refresh": refresh}

    def make_sto_row_callable(row, label_text, mean_source_callable, default_std=0, default_min=0, default_max=0, default_dist="normal"):
        """Mean comes from a callable (used for Porosity that may derive from permeability)."""
        active = IntVar(value=0)
        chk = customtkinter.CTkCheckBox(sto_frame, text=label_text, variable=active)
        chk.grid(row=row, column=0, sticky="w", padx=6, pady=4)

        dist = StringVar(value=default_dist)
        menu = customtkinter.CTkOptionMenu(sto_frame, variable=dist, values=["normal","lognormal","uniform"])
        menu.grid(row=row, column=1, padx=6, pady=4)

        e_mean = customtkinter.CTkEntry(sto_frame, width=100, state="disabled")
        e_mean.grid(row=row, column=2, padx=4)

        def refresh():
            try:
                val = mean_source_callable()
            except Exception:
                val = ""
            e_mean.configure(state="normal")
            e_mean.delete(0, END)
            e_mean.insert(0, f"{val:.6g}" if isinstance(val, (int,float)) else str(val))
            e_mean.configure(state="disabled")

        refresh()

        e_std  = customtkinter.CTkEntry(sto_frame, width=90); e_std.insert(0, str(default_std)); e_std.grid(row=row, column=3, padx=4)
        e_min  = customtkinter.CTkEntry(sto_frame, width=90); e_min.insert(0, str(default_min)); e_min.grid(row=row, column=4, padx=4)
        e_max  = customtkinter.CTkEntry(sto_frame, width=90); e_max.insert(0, str(default_max)); e_max.grid(row=row, column=5, padx=4)

        return {"active": active, "chk": chk, "dist": dist, "menu": menu, "mean": e_mean, "std": e_std, "min": e_min, "max": e_max, "refresh": refresh}

    # mean provider for Porosity (handles mode + KC inversion)
    def current_porosity_percent():
        sphericity_val = float(params_entries["Sphericity:"].get())
        d_val = float(params_entries["Average grain size of gravel pack (m):"].get())
        if mode_var.get() == "porosity":
            return float(e_phi_input.get())
        else:
            k_perm = float(e_k_input.get())
            phi = invert_porosity_from_perm(k_perm, d_val, sphericity_val)
            return 100.0 * phi

    # --- Stochastic rows ---
    sto_porosity = make_sto_row_callable(
        2, "Porosity (%)",
        mean_source_callable=current_porosity_percent,
        default_std=5, default_min=10, default_max=50, default_dist="lognormal"
    )

    sto_permeability = make_sto_row_linked(
        3, "Permeability (m²)",
        e_k_input,
        default_std=5e-10, default_min=1e-16, default_max=1e-7, default_dist="lognormal"
    )

    sto_grainsize  = make_sto_row_linked(
        4, "Grain size (m)",
        params_entries["Average grain size of gravel pack (m):"],
        default_std=0.0002, default_min=0.0008, default_max=0.003, default_dist="normal"
    )
    sto_flowrate   = make_sto_row_linked(
        5, "Flow rate (l/min)",
        params_entries["Flow rate (l/min):"],
        default_std=50, default_min=100, default_max=600, default_dist="normal"
    )
    sto_sphericity = make_sto_row_linked(
        6, "Sphericity (-)",
        params_entries["Sphericity:"],
        default_std=0.10, default_min=0.6, default_max=1.5, default_dist="normal"
    )
    sto_screened   = make_sto_row_linked(
        7, "Screened length (m)",
        params_entries["Screened length (m):"],
        default_std=10.0, default_min=20.0, default_max=150.0, default_dist="uniform"
    )

    # Live mean refresh for Porosity
    def _bind_refresh(widget, fn):
        for ev in ("<KeyRelease>", "<FocusOut>"):
            try: widget.bind(ev, lambda *_: fn())
            except Exception: pass

    _bind_refresh(params_entries["Sphericity:"], sto_porosity["refresh"])
    _bind_refresh(params_entries["Average grain size of gravel pack (m):"], sto_porosity["refresh"])
    _bind_refresh(e_phi_input, sto_porosity["refresh"])
    _bind_refresh(e_k_input,   sto_porosity["refresh"])
    mode_var.trace_add("write", lambda *_: sto_porosity["refresh"]())

    # Seed & number of simulations
    customtkinter.CTkLabel(sto_frame, text="Random seed:").grid(row=8, column=0, sticky="e", padx=6)
    e_seed = customtkinter.CTkEntry(sto_frame, width=120); e_seed.insert(0, "42"); e_seed.grid(row=8, column=1, sticky="w", padx=6, pady=4)
    customtkinter.CTkLabel(sto_frame, text="Number of simulations:").grid(row=8, column=2, sticky="e", padx=6)
    e_nsims = customtkinter.CTkEntry(sto_frame, width=120); e_nsims.insert(0, "20"); e_nsims.grid(row=8, column=3, sticky="w", padx=6, pady=4)

    # --- Optional overlay (visual cue when locked) ---
    overlay = customtkinter.CTkFrame(sto_frame, corner_radius=0)
    # Attempt a semi-transparent overlay; if unsupported, use an opaque fallback color (e.g., "#2f2f2f").
    try:
        overlay.configure(fg_color="#00000055")
    except Exception:
        overlay.configure(fg_color="#2f2f2f")
    overlay_lbl = customtkinter.CTkLabel(overlay, text="Switch to Stochastic to edit", font=("TkDefaultFont", 14, "bold"))
    overlay_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def set_sto_state():
        """Enable/disable stochastic controls based on model selection and enforce initial-mode constraints.

        Rule:
          - In stochastic model, if Porosity is selected as stochastic, initial input mode is forced to Porosity.
          - In stochastic model, if Permeability is selected as stochastic, initial input mode is forced to Permeability.
          - Porosity vs Permeability stochastic selection is treated as mutually exclusive.
        """
        det = (model_var.get() == "deterministic")
        is_sto = (model_var.get() == "stochastic")

        def _set_radio(rb, enabled: bool):
            try:
                rb.configure(state=("normal" if enabled else "disabled"))
            except Exception:
                pass

        # Enable/disable stochastic rows
        base_rows = [sto_porosity, sto_grainsize, sto_flowrate, sto_sphericity, sto_screened]
        for r in base_rows:
            _set_widget_enabled(r["chk"],  not det)
            _set_widget_enabled(r["menu"], not det)
            _set_widget_enabled(r["std"],  not det)
            _set_widget_enabled(r["min"],  not det)
            _set_widget_enabled(r["max"],  not det)

        _set_widget_enabled(sto_permeability["chk"],  not det)
        _set_widget_enabled(sto_permeability["menu"], not det)
        _set_widget_enabled(sto_permeability["std"],  not det)
        _set_widget_enabled(sto_permeability["min"],  not det)
        _set_widget_enabled(sto_permeability["max"],  not det)

        _set_widget_enabled(e_seed,  not det)
        _set_widget_enabled(e_nsims, not det)

        # Enforce initial-mode constraints in stochastic model
        if not is_sto:
            # Deterministic: both modes selectable
            _set_radio(rb_mode_phi, True)
            _set_radio(rb_mode_k, True)
            # Allow both stochastic checkboxes to be toggled (they are disabled anyway in deterministic mode)
            try:
                sto_porosity["chk"].configure(state=("normal" if not det else "disabled"))
                sto_permeability["chk"].configure(state=("normal" if not det else "disabled"))
            except Exception:
                pass
        else:
            por_act  = bool(sto_porosity["active"].get())
            perm_act = bool(sto_permeability["active"].get())

            # Mutual exclusivity guard
            if por_act and perm_act:
                # Prefer the mode currently selected; otherwise prefer Porosity
                if mode_var.get() == "permeability":
                    sto_porosity["active"].set(0)
                    por_act = False
                else:
                    sto_permeability["active"].set(0)
                    perm_act = False

            if por_act and not perm_act:
                mode_var.set("porosity")
                _set_radio(rb_mode_phi, True)
                _set_radio(rb_mode_k, False)
                # Make the alternative stochastic checkbox visibly disabled
                _set_widget_enabled(sto_permeability["chk"], False)
            elif perm_act and not por_act:
                mode_var.set("permeability")
                _set_radio(rb_mode_phi, False)
                _set_radio(rb_mode_k, True)
                _set_widget_enabled(sto_porosity["chk"], False)
            else:
                # No stochastic initial-state parameter selected -> allow both modes
                _set_radio(rb_mode_phi, True)
                _set_radio(rb_mode_k, True)
                _set_widget_enabled(sto_porosity["chk"], True)
                _set_widget_enabled(sto_permeability["chk"], True)

        # Keep the initial input entry widgets consistent with mode_var
        _toggle_initial_mode()

        # Overlay visibility
        if det:
            overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            overlay.lift()
        else:
            overlay.place_forget()

    model_var.trace_add("write", lambda *_: set_sto_state())
    mode_var.trace_add("write",  lambda *_: set_sto_state())
    sto_porosity["active"].trace_add("write",  lambda *_: set_sto_state())
    sto_permeability["active"].trace_add("write", lambda *_: set_sto_state())
    set_sto_state()

    def register():
        """
        Collect inputs. If user gave initial permeability, compute initial porosity from it (Kozeny–Carman).
        Degradation then uses porosity as before.
        """
        global flowrate, porosity, nw_diameter_out, wb_diameter_out, sphericity, grainsize, screened_length, reinjection_temp, reservoir_temp
        global model_type, stochastic_params, stochastic_settings, fluid_air_contact

        flowrate         = float(params_entries["Flow rate (l/min):"].get())
        nw_diameter_out  = float(params_entries["Near-wellbore zone outer diameter (m):"].get())
        wb_diameter_out  = float(params_entries["Wellbore outer diameter (m):"].get())
        sphericity       = float(params_entries["Sphericity:"].get())
        grainsize        = float(params_entries["Average grain size of gravel pack (m):"].get())
        screened_length  = float(params_entries["Screened length (m):"].get())
        reinjection_temp = float(params_entries["Reinjection temperature (°C):"].get())
        reservoir_temp   = float(params_entries["Reservoir temperature (°C):"].get())

        # Resolve initial porosity (from chosen mode)
        if mode_var.get() == "porosity":
            porosity = float(e_phi_input.get()) / 100.0
        else:
            k_perm = float(e_k_input.get())
            porosity = invert_porosity_from_perm(k_perm, grainsize, sphericity)

        model_type = model_var.get()
        stochastic_params = []

        if model_type == "deterministic":
            stochastic_settings = {}
        else:
            def pack_row(name, row_obj, is_percent=False):
                if row_obj["active"].get():
                    mean_val = float(row_obj["mean"].get())  # Porosity mean is % if is_percent=True
                    return {
                        "param": name,
                        "dist": row_obj["dist"].get(),
                        "mean": mean_val,
                        "std":  float(row_obj["std"].get()),
                        "min":  float(row_obj["min"].get()),
                        "max":  float(row_obj["max"].get()),
                        "percent": is_percent
                    }

            if mode_var.get() == "porosity": 
                packed = pack_row("porosity", sto_porosity, True)
                if packed: 
                    stochastic_params.append(packed)

            # Only allow permeability row when initial mode is permeability
            if mode_var.get() == "permeability":
                packed = pack_row("permeability", sto_permeability, False)
                if packed: 
                    stochastic_params.append(packed)

            # Other rows
            for name, row, perc in [
                ("grainsize",  sto_grainsize,  False),
                ("flowrate",   sto_flowrate,   False),
                ("sphericity", sto_sphericity, False),
                ("screened",   sto_screened,   False),
            ]:
                packed = pack_row(name, row, perc)
                if packed:
                    stochastic_params.append(packed)

            stochastic_settings = {"seed": int(e_seed.get()), "num_sim": int(e_nsims.get())}

        notify("info","Success",f"Operational parameters saved")
        safe_close_tk(window)

    customtkinter.CTkButton(footer, text="Submit", command=register).pack(side="right", padx=8, pady=8)
    window.mainloop()
    
else:
    # ---------------- HEADLESS CONFIG MODE ----------------

    print(f"[HEADLESS] Loading configuration from: {CONFIG_PATH}")

    cfg = load_toml(CONFIG_PATH)

    defaults_bundle = {
        "prod_defaults": prod_defaults,
        "inj_defaults": inj_defaults,
        "gas_defaults": gas_defaults,
        "default_minerals": default_minerals,
        "SUPPORTED_DEFAULTS": SUPPORTED_DEFAULTS,
    }

    values = apply_headless_config(cfg, defaults_bundle)

    globals().update(values)

    # Resolve initial porosity
    if mode_var == "porosity":
        porosity = float(initial_porosity_pct) / 100.0
    else:
        porosity = invert_porosity_from_perm(
            float(initial_permeability_value),
            grainsize,
            sphericity
        )

    
# ======================== /PARAMETERS & MODEL SETUP ========================




# ------------------------ Post-GUI Processing ------------------------
# Convert chemistry inputs to float
for vname in ["CaP","NaP","KP","pHP","TP","S2P","S6P","FP","ClP","BrP","LiP","MgP","Fe2P","Fe3P","MnP","SiP","ZnP","BaP","PbP","AlkP"]:
    globals()[vname] = float(globals()[vname])
for vname in ["CaI","NaI","KI","pHI","RT","S2I","S6I","FI","ClI","BrI","LiI","MgI","Fe2I","Fe3I","MnI","SiI","ZnI","BaI","PbI","AlkI"]:
    globals()[vname] = float(globals()[vname])

# Convert gas % to PHREEQC inputs
O2  = 1013/100.0 * float(O2)/1000.0
N2  = 1013/100.0 * float(N2)/1000.0
CO2 = 1013/100.0 * float(CO2)/1000.0
CH4 = 1013/100.0 * float(CH4)/1000.0

# Build dynamic PHREEQC block for EQUILIBRIUM_PHASES 3 and SELECTED_OUTPUT from selected minerals
phases3_lines = []
def add_phase_line(name):
    if name and name != "(none)":
        phases3_lines.append(f"   {name} 0 0 precipitate_only")

for nm in mineral_props.keys():
    add_phase_line(nm)

if not phases3_lines:
    phases3_lines = ["   Calcite 0 0 precipitate_only"]

phases3_block = "\n".join(phases3_lines)
selout_items = "  ".join(mineral_props.keys()) if mineral_props else "Calcite"

# Build PHREEQC input
phreeqc_input = f"""
SOLUTION 1 #production well fluid (surface) (MODEL STEP 1)
pH {pHP}
temp {TP}
units {unit_selected_prod}
redox S(-2)/S(6)
S(-2) {S2P}
S(6) {S6P}
F  {FP}
Cl {ClP}
Br {BrP}
Li {LiP}
Na {NaP}
K  {KP}
Ca {CaP}
Mg {MgP}
Fe(3) {Fe3P}
Fe(2) {Fe2P}
Mn {MnP}
Si {SiP} as H2SiO3
Zn {ZnP}
Ba {BaP}
Pb {PbP}
Alkalinity {AlkP} as HCO3-

end
save solution 1

{fluid_air_contact}

Use solution 1

EQUILIBRIUM_PHASES 1
    Fe(OH)3(a)  0 0 precipitate_only
    Calcite     0 0 precipitate_only
save solution 1

end

use solution 1 
REACTION_TEMPERATURE 1
    {TP}  {reinjection_temp}

save solution 1
end

SOLUTION 2
pH {pHI}
temp {RT}
units {unit_selected_inj}
redox S(-2)/S(6)
S(-2) {S2I}
S(6) {S6I}
F    {FI}
Cl   {ClI}
Br   {BrI}
Li   {LiI}
Na   {NaI}
K    {KI}
Ca   {CaI}
Mg   {MgI}
Fe(3) {Fe3I}
Fe(2) {Fe2I}
Mn   {MnI}
Si   {SiI} as H2SiO3
Zn   {ZnI}
Ba   {BaI}
Pb   {PbI}
Alkalinity {AlkI} as HCO3-


GAS_PHASE 2
-fixed pressure
-pressure 1.013
O2(g)  {O2}
CO2(g) {CO2}
N2(g)  {N2}
CH4(g) {CH4}

EQUILIBRIUM_PHASES 2
   {globals().get('reservoir_mineral_1', '#')}    0 10
   {globals().get('reservoir_mineral_2', '#')}    0 10
   {globals().get('reservoir_mineral_3', '#')}    0 10
   {globals().get('reservoir_mineral_4', '#')}    0 10
   {globals().get('reservoir_mineral_5', '#')}    0 10
   {globals().get('reservoir_mineral_6', '#')}    0 10
   {globals().get('reservoir_mineral_7', '#')}    0 10
   {globals().get('reservoir_mineral_8', '#')}    0 10
end

Save solution 2
end

MIX 1 ;1 0.1 ;2 0.9 ;SAVE SOLUTION 3 ;END
MIX 2 ;1 0.2 ;3 0.8 ;SAVE SOLUTION 4 ;END
MIX 3 ;1 0.3 ;4 0.7 ;SAVE SOLUTION 5 ;END
MIX 4 ;1 0.4 ;5 0.6 ;SAVE SOLUTION 6 ;END
MIX 5 ;1 0.5 ;6 0.5 ;SAVE SOLUTION 7 ;END

use Solution 7

EQUILIBRIUM_PHASES 3
{phases3_block}

SELECTED_OUTPUT 1
    -file                 output.sel
    -reset                false
    -equilibrium_phases   {selout_items}
"""

# Write PHREEQC input (raw text)
inputname = f"{IDP}_{IDI}.dat"
with open(inputname, "w", encoding="utf-8", newline="\n") as f:
    f.write(phreeqc_input)

    
# PHREEQC execution using user-provided paths (with fallbacks)
if 'PHREEQC_PATH' not in globals() or not PHREEQC_PATH:
    PHREEQC_PATH = r"C:/phreeqc/phreeqc.exe"
if 'DATABASE' not in globals() or not DATABASE:
    DATABASE = "C:/phreeqc/database/PHREEQC.DAT"

import subprocess

try:
    result = subprocess.run(
        [PHREEQC_PATH, inputname, "output.dat", DATABASE],
        check=True,
        capture_output=True,
        text=True
    )
    # Optional: print PHREEQC output for debugging
    if result.stdout:
        print("[PHREEQC stdout]\n", result.stdout)
    if result.stderr:
        print("[PHREEQC stderr]\n", result.stderr)

except FileNotFoundError:
    notify(
        "PHREEQC execution error",
        f"PHREEQC executable not found:\n{PHREEQC_PATH}"
    )
    notify("error","PHREEQC path",f"Executable not found:\n{PHREEQC_PATH}")

    raise

except subprocess.CalledProcessError as e:
    # PHREEQC ran but returned non-zero exit code
    err = e.stderr or e.stdout or str(e)
    notify("error","PHREEQC path",f"PHREEQC returned an error.\n\nCommand:\n{PHREEQC_PATH} {inputname} output.dat {DATABASE}\n\nDetails:\n{err}")
    raise

# Parse output for chosen minerals
molL_map = {name: 0.0 for name in (list(mineral_props.keys()) if 'mineral_props' in globals() else [])}

if os.path.exists("output.sel"):
    try:
        out = pd.read_csv(
            "output.sel",
            sep=r"\s+",
            comment="#",
            engine="python"
        )

        if out.empty:
            raise ValueError("output.sel exists but contains no data rows.")

        last = out.iloc[-1]

        for name in molL_map.keys():
            if name in out.columns:
                try:
                    molL_map[name] = float(last[name])
                except Exception:
                    molL_map[name] = 0.0
            else:
                molL_map[name] = 0.0

    except Exception as e:
        notify("error","PHREEQC output parse error",f"Could not parse output.sel reliably.\n\nReason:\n{e}\n\nUsing fallback zeros.")
else:
    notify("error","PHREEQC output parse error",f"PHREEQC output.sel not found. Using fallback zeros.")


# Convert to daily deposition volumes (m^3/day) per mineral using user density (M fixed from defaults)
def mineral_volume_per_day(name, mol_per_L, flowrate_Lmin):
    props = mineral_props.get(name)
    if props is None:
        return None
    M = props["M"]      # g/mol (fixed)
    rho = props["rho"]  # g/cm3 (editable)
    flowrate_day_L = flowrate_Lmin * 60 * 24
    vol_m3_day = mol_per_L * (M / rho) * flowrate_day_L * 1e-6
    return vol_m3_day

# Use actual flowrate if already captured, otherwise default from GUI default
current_flowrate = None
try:
    current_flowrate = float(params_entries["Flow rate (l/min):"].get())
except Exception:
    pass

if 'flowrate' in globals():
    fr_use = flowrate
elif current_flowrate is not None:
    fr_use = current_flowrate
else:
    fr_use = float(defaults[0]) if 'defaults' in globals() else 350.0

volumes = {}
for name, molL in molL_map.items():
    v = mineral_volume_per_day(name, molL, flowrate_Lmin=fr_use)
    volumes[name] = v

# Sum known volumes; numerical guard
vld_total = sum([v for v in volumes.values() if v is not None]) if volumes else 0.0
vld_total = max(vld_total, 1e-20)

# ------------------------ Simulation core ------------------------
def run_one_sim(flowrate_Lmin, porosity_frac, grainsize_m, sphericity_local, screened_len_m, vld_override=None):
    ringv = (nw_diameter_out/2)**2*np.pi*screened_len_m - (wb_diameter_out/2)**2*np.pi*screened_len_m
    vld = vld_total if vld_override is None else vld_override
    iniporvol = ringv * porosity_frac
    endtime = max(iniporvol / vld, 1.0)
    steps = max(120, int(np.clip(endtime / 5, 60, 2000)))
    T = np.linspace(0, endtime, num=steps)
    por_vol = np.maximum(iniporvol - vld * T, 0.0)
    newporosity = np.maximum(por_vol / ringv, 1e-8)
    perm = (sphericity_local**2) * ((newporosity**3) * (grainsize_m**2)) / (180.0 * (1.0 - newporosity)**2)
    return T, newporosity, perm, endtime

def find_half_zero_times(T, P):
    P0 = P[0]
    half_val = 0.5 * P0
    half_idx = np.where(P <= half_val)[0]
    zero_idx = np.where(P <= 0.0 + 1e-12)[0]
    t_half = float(T[half_idx[0]]) if half_idx.size > 0 else np.nan
    t_zero = float(T[zero_idx[0]]) if zero_idx.size > 0 else np.nan
    return t_half, t_zero

def interval_text(sp):
    return f"[{sp['min']:.3g}, {sp['max']:.3g}]"

name_map = {"porosity":"Porosity (%)","permeability":"Permeability (m²)","grainsize":"Grain size (m)", "flowrate":"Flow rate (l/min)",
            "sphericity":"Sphericity (-)", "screened":"Screened length (m)"}

def draw_value(rng, spec):
    """
    Draw a random value according to spec["dist"] and then clip it to [min, max].

    Notes:
    - For percent-based parameters (e.g., porosity in %), min/max are assumed to be in percent
      as well, so clipping happens BEFORE converting to fraction.
    """
    dist = spec["dist"]
    mean = float(spec["mean"])
    std  = float(spec["std"])
    vmin = float(spec.get("min", -np.inf))
    vmax = float(spec.get("max",  np.inf))

    if dist == "normal":
        x = rng.normal(mean, std)

    elif dist == "lognormal":
        # Convert mean/std of a lognormal to underlying normal parameters
        m = max(mean, 1e-30)
        s = max(std,  1e-30)
        mu  = np.log(m**2 / np.sqrt(m**2 + s**2))
        sig = np.sqrt(np.log(1.0 + (s**2) / (m**2)))
        x = rng.lognormal(mu, sig)

    elif dist == "uniform":
        x = rng.uniform(vmin, vmax)

    else:
        x = mean

    # Apply bounds for all distributions
    x = float(np.clip(x, vmin, vmax))

    # Convert percent-based values to fractions after clipping
    if spec.get("percent", False):
        x = x / 100.0

    return x

if 'model_type' not in globals():
    model_type = "deterministic"

def plot_half_zero(ax_time, T, P):
    t_half, t_zero = find_half_zero_times(T, P)
    h = ax_time.axvline(t_half, linestyle="--", color="darkorange") if np.isfinite(t_half) else None
    z = ax_time.axvline(t_zero, linestyle="--", color="red")        if np.isfinite(t_zero) else None
    return h, z, t_half, t_zero
# --- helper: append average (over sims) to summary + return the means
def append_summary_avg(label, t_half_vals, t_zero_vals):
    import numpy as np
    mhalf = np.nanmean(t_half_vals) if len(t_half_vals) else np.nan
    mzero = np.nanmean(t_zero_vals) if len(t_zero_vals) else np.nan
    summary_rows.append([f"{label} (avg over sims)", fmt_day(mhalf), fmt_day(mzero)])
    return mhalf, mzero

# ------------------------ Plotting + Title with minerals ------------------------
def title_with_minerals(base):
    return f"{base}\nby precipitating: {minerals_title}"  # two-line title

def fmt_day(x):
    import numpy as np
    return "—" if (x is None or (isinstance(x, float) and not np.isfinite(x))) else f"{x:.2f} d"

def permeability_limits(ax):
    """Clamp the permeability axis to a practical log range."""
    ax.set_yscale('log')
    ax.set_ylim(1e-17, 1e-9)

def compute_half_zero_times(T, P):
    """Return (t_half, t_zero) where porosity reaches 50% and ~0% of its initial value."""
    P0 = P[0]
    half_val = 0.5 * P0
    zero_val = 0.001 * P0  # consider zero if below 0.1%
    half_idx = np.where(P <= half_val)[0]
    zero_idx = np.where(P <= zero_val)[0]
    t_half = float(T[half_idx[0]]) if half_idx.size > 0 else np.nan
    t_zero = float(T[zero_idx[0]]) if zero_idx.size > 0 else np.nan
    return t_half, t_zero

def draw_time_markers(ax, t_half, t_zero):
    """Draw vertical markers at t_half (darkorange, dashed) and t_zero (red, dashed)."""
    h = ax.axvline(t_half, linestyle="--", color="darkorange") if np.isfinite(t_half) else None
    z = ax.axvline(t_zero, linestyle="--", color="red")        if np.isfinite(t_zero) else None
    return h, z

def legend_below(fig, entries):
    handles = [h for h, _ in entries if h is not None]
    labels  = [l for _, l in entries if l is not None]
    fig.legend(
        handles, labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=3,
        fontsize=9,
        frameon=False,
        handlelength=2.0,
        handletextpad=0.8,
        columnspacing=1.2
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])  # adds some bottom margin



def resample_with_tail_to_zero(T_src, P_src, K_src, T_common):
    """
    Resample P, K onto T_common. For t > T_src[-1], hold P=0 and K~0 (tiny).
    This guarantees that every run reaches porosity zero on the common grid.
    """
    # Interpolate within the original range
    P_interp = np.interp(T_common, T_src, P_src, left=P_src[0], right=P_src[-1])
    K_interp = np.interp(T_common, T_src, K_src, left=K_src[0], right=K_src[-1])

    # After the run ended, enforce P=0 and near-zero K
    ended_mask = T_common > T_src[-1]
    if np.any(ended_mask):
        P_interp[ended_mask] = 0.0
        # Kozeny–Carman tends to 0 as phi->0; clip to tiny positive to stay on log scale
        K_interp[ended_mask] = 1e-22
    return P_interp, K_interp

png_out_all = "avg_all_active.png"
png_out_oat_prefix = "avg_oat_"

summary_rows = []  # rows for the PDF: [Case, t50, t0]

def save_png_and_svg(fig, base_name, dpi=300):
    """
    Save figure as:
      - PNG at `dpi`
      - SVG (vector)
    """
    fig.savefig(f"{base_name}.png", dpi=dpi, bbox_inches="tight")
    fig.savefig(f"{base_name}.svg", bbox_inches="tight")


def save_plot_data_txt(df: pd.DataFrame, base_name: str, folder: str = None):
    """
    Save plot data (DataFrame) to a human-readable text file (TSV).
    - base_name: filename without extension
    - folder: optional output folder
    """
    if folder:
        os.makedirs(folder, exist_ok=True)
        out_path = os.path.join(folder, f"{base_name}.txt")
    else:
        out_path = f"{base_name}.txt"

    # TSV is robust for decimals and easy to open in Excel
    df.to_csv(out_path, sep="\t", index=False, encoding="utf-8")
    print(f"[EXPORT] Plot data saved: {out_path}")
    return out_path
   
     
if model_type == "deterministic":
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    T_det, P_det, K_det, t_end_det = run_one_sim(flowrate, porosity, grainsize, sphericity, screened_length)

    t_half, t_zero = compute_half_zero_times(T_det, P_det)
    half_line, zero_line = draw_time_markers(ax1, t_half, t_zero)
    summary_rows.append(["Deterministic", fmt_day(t_half), fmt_day(t_zero)])

    p_line, = ax1.plot(T_det, P_det, linewidth=2.0, label="Porosity")
    k_line, = ax2.plot(T_det, K_det, linewidth=2.0, linestyle="--", label="Permeability")

    ax1.set_xlabel("Time (days)")
    ax1.set_ylabel("Porosity ϕ [-]")
    ax2.set_ylabel("Permeability k [m²]")
    permeability_limits(ax2)

    x_right = t_zero if np.isfinite(t_zero) else T_det[-1]
    ax1.set_xlim(0.0, x_right)

    entries = [(p_line, "Porosity"), (k_line, "Permeability")]
    if half_line is not None:
        entries.append((half_line, f"Porosity 50% time = {fmt_day(t_half)}"))
    if zero_line is not None:
        entries.append((zero_line, f"Porosity 0% time = {fmt_day(t_zero)}"))
    legend_below(fig, entries)

    plt.title(title_with_minerals("Porosity & permeability degradation"))
    plt.tight_layout(rect=[0, 0.1, 1, 0.9])
    save_png_and_svg(fig, png_out_all.replace(".png", ""), dpi=300)
    plt.close(fig)
    
    # EXPORT (inside deterministic block)
    df_det = pd.DataFrame({
        "time_days": T_det,
        "porosity": P_det,
        "permeability_m2": K_det
    })
    save_plot_data_txt(df_det, base_name="deterministic_timeseries")


else:
    # --- Stochastic: all-active average plot ---
    rng = np.random.default_rng(int(stochastic_settings.get("seed", 42)))
    nsims = int(stochastic_settings.get("num_sim", 20))

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    runs_T, runs_P, runs_K, endtimes = [], [], [], []

    # ---- Stochastic export (wide time series table, written after common-grid resampling) ----
    import re as _re

    def _sanitize_filename(_s: str) -> str:
        _s = "" if _s is None else str(_s)
        _s = _re.sub(r"[^A-Za-z0-9_.-]+", "_", _s).strip("_")
        return _s[:120] if len(_s) > 120 else _s

    def _fmt_for_tag(param: str, value: float) -> str:
        # Compact formatting for filenames/column names
        if param == "porosity":
            return f"{value:.3g}pct"
        if param == "permeability":
            return f"{value:.3e}"
        return f"{value:.4g}"

    def _make_case_tag(active_param_values: dict) -> str:
        # active_param_values: {param_name: numeric_value_in_display_units}
        if not active_param_values:
            return "baseline"
        parts = []
        for k in sorted(active_param_values.keys()):
            parts.append(f"{k}={_fmt_for_tag(k, float(active_param_values[k]))}")
        tag = "__".join(parts)
        tag = _re.sub(r"[^A-Za-z0-9_.=+-]+", "_", tag)
        return tag[:180] if len(tag) > 180 else tag

    export_dir = os.getcwd()
    
    # Include which parameters were selected as stochastic in the filename
    _params_used = sorted({sp.get("param", "") for sp in (stochastic_params or []) if sp.get("param")})
    _param_tag = "-".join(_params_used) if _params_used else "none"

    export_prefix = (
        f"{_sanitize_filename(IDP)}_{_sanitize_filename(IDI)}_stochastic_"
        f"{_sanitize_filename(_param_tag)}"
    )

    # Per-simulation metadata for column naming
    run_case_tags = []
# list of per-simulation DataFrames (one per run)

    # Generate nsims runs with the selected distributions
    for i in range(nsims):
        # Start from deterministic baseline values
        f = flowrate
        p = porosity
        g = grainsize
        s = sphericity
        L = screened_length

        # First, sample all stochastic parameters
        samples = {}
        display_vals = {}
        for sp in (stochastic_params or []):
            v = draw_value(rng, sp)
            samples[sp["param"]] = v

            # Store values for tagging (in display units)
            if sp["param"] == "porosity":
                display_vals["porosity"] = 100.0 * float(v)  # percent
            elif sp["param"] == "permeability":
                display_vals["permeability"] = float(v)
            else:
                display_vals[sp["param"]] = float(v)

        # Apply sampled values (if present)
        if "flowrate" in samples:    f = float(samples["flowrate"])
        if "grainsize" in samples:   g = float(samples["grainsize"])
        if "sphericity" in samples:  s = float(samples["sphericity"])
        if "screened" in samples:    L = float(samples["screened"])

        # Resolve porosity from either direct porosity sampling or permeability sampling
        if "porosity" in samples:
            p = float(samples["porosity"])
        elif "permeability" in samples:
            p = invert_porosity_from_perm(float(samples["permeability"]), g, s)

        # Create a run-specific tag used in column names
        run_case_tags.append(_make_case_tag(display_vals))

        # Run the simulation
        T_i, P_i, K_i, end_i = run_one_sim(f, p, g, s, L)

        runs_T.append(T_i)
        runs_P.append(P_i)
        runs_K.append(K_i)
        endtimes.append(end_i)

    # Export is written after common-grid resampling (see below)
    T_common = np.linspace(0.0, float(np.max(endtimes)), 1000)

    # Resample all runs onto T_common and extend tails to zero
    P_stack, K_stack = [], []
    t_half_list, t_zero_list = [], []
    for T_i, P_i, K_i in zip(runs_T, runs_P, runs_K):
        # Individual times on native grid (for stats)
        th_i, tz_i = compute_half_zero_times(T_i, P_i)
        t_half_list.append(th_i); t_zero_list.append(tz_i)

        P_c, K_c = resample_with_tail_to_zero(T_i, P_i, K_i, T_common)
        P_stack.append(P_c); K_stack.append(K_c)

    P_stack = np.vstack(P_stack)
    K_stack = np.vstack(K_stack)

    # Quantiles over the extended grid (P10/P50/P90)
    P_p10, P_p50, P_p90 = np.percentile(P_stack, [10, 50, 90], axis=0)
    K_p10, K_p50, K_p90 = np.percentile(K_stack, [10, 50, 90], axis=0)

    # ---- Export: wide table with one column pair (porosity, permeability) per stochastic run ----
    
    txt_base_name = f"{IDP}_{IDI}_stochastic_{_param_tag}"

    try:
        # Base DataFrame (percentiles)
        df_wide = pd.DataFrame({
            "time_days": T_common,
            "P10_porosity": P_p10,
            "P50_porosity": P_p50,
            "P90_porosity": P_p90,
            "P10_permeability_m2": K_p10,
            "P50_permeability_m2": K_p50,
            "P90_permeability_m2": K_p90,
        })

        # Collect simulation columns first
        sim_cols = {}

        for _j, _tag in enumerate(run_case_tags):
            _sim = _j + 1
            _pcol = f"sim{_sim:03d}_porosity_{_tag}"
            _kcol = f"sim{_sim:03d}_permeability_m2_{_tag}"

            sim_cols[_pcol] = P_stack[_j, :]
            sim_cols[_kcol] = K_stack[_j, :]

        # Concatenate all at once (fast + no fragmentation)
        df_wide = pd.concat([df_wide, pd.DataFrame(sim_cols)], axis=1)

        xlsx_path = os.path.join(export_dir, f"{export_prefix}_timeseries.xlsx")
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as _writer:
            df_wide.to_excel(_writer, sheet_name="timeseries", index=False)
        print(f"[EXPORT] Stochastic time series (wide) saved: {xlsx_path}")
        save_plot_data_txt(
        df_wide,
        base_name=txt_base_name,
        folder=export_dir
        )
        
    except Exception as _ex:
        print(f"[EXPORT] WARNING: could not write stochastic time series (wide): {_ex}")


    # Averages over the extended grid (kept for reference)
    P_mean = np.mean(P_stack, axis=0)
    K_mean = np.mean(K_stack, axis=0)

    # Times on quantile curves
    t_half_p10, t_zero_p10 = compute_half_zero_times(T_common, P_p10)
    t_half_p50, t_zero_p50 = compute_half_zero_times(T_common, P_p50)
    t_half_p90, t_zero_p90 = compute_half_zero_times(T_common, P_p90)

    # Summary rows for stochastic quantiles
    summary_rows.append(["Stochastic P10", fmt_day(t_half_p10), fmt_day(t_zero_p10)])
    summary_rows.append(["Stochastic P50", fmt_day(t_half_p50), fmt_day(t_zero_p50)])
    summary_rows.append(["Stochastic P90", fmt_day(t_half_p90), fmt_day(t_zero_p90)])


    # Draw cloud (light) + P10/P50/P90 summary
    runP = Line2D([0],[0], linewidth=1.5, alpha=0.25, label="Porosity runs")
    runK = Line2D([0],[0], linewidth=1.5, alpha=0.25, label="Permeability runs")

    # # Individual stochastic runs (kept light to avoid overplot dominance)
    # for arr in P_stack:
    #     ax1.plot(T_common, arr, alpha=0.15)
    # for arr in K_stack:
    #     ax2.plot(T_common, arr, alpha=0.15)

    # Quantile envelopes and median curves
    p_band = ax1.fill_between(T_common, P_p10, P_p90, alpha=0.25, label="Porosity P10–P90")
    k_band = ax2.fill_between(T_common, K_p10, K_p90, alpha=0.25, label="Permeability P10–P90")

    p50_line, = ax1.plot(T_common, P_p50, linewidth=3.0, label="Porosity P50 (median)")
    k50_line, = ax2.plot(T_common, K_p50, linestyle="--", linewidth=3.0, label="Permeability P50 (median)")

    # Optional: mean curves for reference (not emphasized)
    mean_P_line, = ax1.plot(T_common, P_mean, linewidth=1.8, alpha=0.65, label="Porosity mean")
    mean_K_line, = ax2.plot(T_common, K_mean, linestyle=":", linewidth=1.8, alpha=0.65, label="Permeability mean")

    # Markers on the P50 (median) curve
    half_line, zero_line = draw_time_markers(ax1, t_half_p50, t_zero_p50)

    # Axes and limits
    ax1.set_xlabel('Time (days)')
    ax1.set_ylabel('Porosity ϕ [-]')
    ax2.set_ylabel('Permeability k [m²]')
    # Permeability axis (log scale) and limits based on all stochastic cases
    ax2.set_yscale('log')
    _k_pos = K_stack[K_stack > 0.0]
    _kmin = float(np.nanmin(_k_pos)) if _k_pos.size else 1e-22
    _kmax = float(np.nanmax(K_stack)) if np.isfinite(np.nanmax(K_stack)) else 1e-9
    _kmin = max(_kmin, 1e-22)
    _kmax = max(_kmax, _kmin * 10.0)
    ax2.set_ylim(_kmin / 10.0, _kmax * 10.0)

    # X-axis: include the full common grid so all stochastic cases fit
    ax1.set_xlim(0.0, T_common[-1])

    # Porosity axis limits
    _pmax = float(np.nanmax(P_stack)) if np.isfinite(np.nanmax(P_stack)) else 1.0
    ax1.set_ylim(0.0, min(1.0, _pmax * 1.05))

    # Legend (include exact times on the P50 curve)
    entries = [
        (p_band, "Porosity P10–P90"), (k_band, "Permeability P10–P90"),
        (p50_line, "Porosity P50 (median)"), (k50_line, "Permeability P50 (median)"),
        (mean_P_line, "Porosity mean"), (mean_K_line, "Permeability mean"),
    ]
    if half_line is not None:
        entries.append((half_line, f"P50 porosity 50% time = {fmt_day(t_half_p50)}"))
    if zero_line is not None:
        entries.append((zero_line, f"P50 porosity 0% time = {fmt_day(t_zero_p50)}"))

    # Also list active stochastic ranges in legend (as text-only rows)
    for sp in stochastic_params:
        entries.append((Line2D([0],[0], linewidth=0), f"{name_map.get(sp['param'], sp['param'])} ∈ {interval_text(sp)}"))

    legend_below(fig, entries)
    plt.title(title_with_minerals("Porosity & permeability degradation (stochastic)"))
    plt.tight_layout(rect=[0,0.1,1,0.9])
    save_png_and_svg(fig, png_out_all.replace(".png", ""), dpi=300)
    plt.close(fig)
    
    # --- One-at-a-time (OAT) figures ---
    base_specs = {"flowrate": flowrate, "porosity": porosity, "grainsize": grainsize, "sphericity": sphericity, "screened": screened_length}

    for sp in stochastic_params:
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()

        runs_T, runs_P, runs_K, endtimes = [], [], [], []
        for _ in range(nsims):
            f = base_specs["flowrate"]
            p = base_specs["porosity"]
            g = base_specs["grainsize"]
            s = base_specs["sphericity"]
            L = base_specs["screened"]

            val = draw_value(rng, sp)
            if sp["param"] == "flowrate":   f = val
            elif sp["param"] == "porosity": p = val
            elif sp["param"] == "grainsize":g = val
            elif sp["param"] == "sphericity": s = val
            elif sp["param"] == "screened":  L = val
            elif sp["param"] == "permeability":
                p = invert_porosity_from_perm(val, g, s)
            T_i, P_i, K_i, end_i = run_one_sim(f, p, g, s, L)
            runs_T.append(T_i); runs_P.append(P_i); runs_K.append(K_i); endtimes.append(end_i)

        T_common = np.linspace(0.0, float(np.max(endtimes)), 1000)

        P_stack, K_stack = [], []
        t_half_list, t_zero_list = [], []
        for T_i, P_i, K_i in zip(runs_T, runs_P, runs_K):
            th_i, tz_i = compute_half_zero_times(T_i, P_i)
            t_half_list.append(th_i); t_zero_list.append(tz_i)
            P_c, K_c = resample_with_tail_to_zero(T_i, P_i, K_i, T_common)
            P_stack.append(P_c); K_stack.append(K_c)

        P_stack = np.vstack(P_stack)
        K_stack = np.vstack(K_stack)

        # Quantiles over the extended grid (P10/P50/P90)
        P_p10, P_p50, P_p90 = np.percentile(P_stack, [10, 50, 90], axis=0)
        K_p10, K_p50, K_p90 = np.percentile(K_stack, [10, 50, 90], axis=0)

        # Averages (kept for reference)
        P_mean = np.mean(P_stack, axis=0)
        K_mean = np.mean(K_stack, axis=0)

        # Times on quantile curves
        t_half_p10, t_zero_p10 = compute_half_zero_times(T_common, P_p10)
        t_half_p50, t_zero_p50 = compute_half_zero_times(T_common, P_p50)
        t_half_p90, t_zero_p90 = compute_half_zero_times(T_common, P_p90)

        _lbl = f"One at a time: {name_map.get(sp['param'], 'param')}"
        summary_rows.append([f"{_lbl} P10", fmt_day(t_half_p10), fmt_day(t_zero_p10)])
        summary_rows.append([f"{_lbl} P50", fmt_day(t_half_p50), fmt_day(t_zero_p50)])
        summary_rows.append([f"{_lbl} P90", fmt_day(t_half_p90), fmt_day(t_zero_p90)])

        # Draw cloud (light) + P10/P50/P90
        runP = Line2D([0],[0], linewidth=1.5, alpha=0.25, label="Porosity runs")
        runK = Line2D([0],[0], linewidth=1.5, alpha=0.25, label="Permeability runs")
        for arr in P_stack:
            ax1.plot(T_common, arr, alpha=0.15)
        for arr in K_stack:
            ax2.plot(T_common, arr, alpha=0.15)

        p_band = ax1.fill_between(T_common, P_p10, P_p90, alpha=0.25, label="Porosity P10–P90")
        k_band = ax2.fill_between(T_common, K_p10, K_p90, alpha=0.25, label="Permeability P10–P90")

        p50_line, = ax1.plot(T_common, P_p50, linewidth=3.0, label="Porosity P50 (median)")
        k50_line, = ax2.plot(T_common, K_p50, linestyle="--", linewidth=3.0, label="Permeability P50 (median)")

        mean_P_line, = ax1.plot(T_common, P_mean, linewidth=1.8, alpha=0.65, label="Porosity mean")
        mean_K_line, = ax2.plot(T_common, K_mean, linestyle=":", linewidth=1.8, alpha=0.65, label="Permeability mean")

        # Markers on the P50 (median) curve
        half_line, zero_line = draw_time_markers(ax1, t_half_p50, t_zero_p50)

        # Axes and limits
        ax1.set_xlabel('Time (days)')
        ax1.set_ylabel('Porosity ϕ [-]')
        ax2.set_ylabel('Permeability k [m²]')

        # Permeability axis (log scale) and limits based on all cases
        ax2.set_yscale('log')
        _k_pos = K_stack[K_stack > 0.0]
        _kmin = float(np.nanmin(_k_pos)) if _k_pos.size else 1e-22
        _kmax = float(np.nanmax(K_stack)) if np.isfinite(np.nanmax(K_stack)) else 1e-9
        _kmin = max(_kmin, 1e-22)
        _kmax = max(_kmax, _kmin * 10.0)
        ax2.set_ylim(_kmin / 10.0, _kmax * 10.0)

        # X-axis: include the full common grid so all cases fit
        ax1.set_xlim(0.0, T_common[-1])

        # Porosity axis limits
        _pmax = float(np.nanmax(P_stack)) if np.isfinite(np.nanmax(P_stack)) else 1.0
        ax1.set_ylim(0.0, min(1.0, _pmax * 1.05))

        # Legend
        entries = [
            (runP, "Porosity runs"), (runK, "Permeability runs"),
            (p_band, "Porosity P10–P90"), (k_band, "Permeability P10–P90"),
            (p50_line, "Porosity P50 (median)"), (k50_line, "Permeability P50 (median)"),
            (mean_P_line, "Porosity mean"), (mean_K_line, "Permeability mean"),
        ]
        if half_line is not None:
            entries.append((half_line, f"P50 porosity 50% time = {fmt_day(t_half_p50)}"))
        if zero_line is not None:
            entries.append((zero_line, f"P50 porosity 0% time = {fmt_day(t_zero_p50)}"))
        entries.append((Line2D([0],[0], linewidth=0), f"{name_map.get(sp['param'], sp['param'])} ∈ {interval_text(sp)}"))

        legend_below(fig, entries)
        plt.title(title_with_minerals(f"Stochastic (One-at-a-time): {name_map.get(sp['param'], sp['param'])}"))
        plt.tight_layout(rect=[0,0.1,1,0.9])
        base_name = f"{png_out_oat_prefix}{sp['param']}"   # e.g., "avg_oat_porosity"
        save_png_and_svg(fig, base_name, dpi=300)
        plt.close(fig)

# ------------------------ PDF Summary Report ------------------------
def build_pdf_report(
    pdf_path: str,
    inputs: dict,
    model: str,
    stochastic_list: list,
    half_zero_table: list,
    main_png: str,
    oat_pngs: list
):
    if not REPORTLAB_OK:
        print("NOTE: reportlab not available -> skipping PDF.")
        return False

    # ---------- document ----------
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, title="PHREI Summary Report")
    styles = getSampleStyleSheet()
    flow = []

    # ---------- helpers ----------
    def _add_h(txt, style_key="Heading2", space_before=6, space_after=6):
        flow.append(Spacer(1, space_before))
        flow.append(Paragraph(f"<b>{txt}</b>", styles[style_key]))
        flow.append(Spacer(1, space_after))

    def _pairs_table(pairs, col_widths=(220, 300), header=None, grid_col=colors.grey):
        data = []
        if header:
            data.append(header)
        data.extend([[str(k), str(v)] for (k, v) in pairs])

        table = Table(data, colWidths=list(col_widths))
        ts = [('GRID', (0, 0), (-1, -1), 0.3, grid_col)]
        if header:
            ts += [
                ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]
        table.setStyle(TableStyle(ts))
        flow.append(table)
        return table

    def _list_table(items, ncols=2, col_width=250):
        if not items:
            items = ["—"]
        rows = []
        for i in range(0, len(items), ncols):
            row = []
            for j in range(ncols):
                idx = i + j
                row.append(items[idx] if idx < len(items) else "")
            rows.append(row)
        table = Table(rows, colWidths=[col_width]*ncols)
        table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey)]))
        flow.append(table)

    def _round(x, nd=6):
        try:
            xv = float(x)
            if abs(xv) >= 1e3 or (0 < abs(xv) < 1e-3):
                return f"{xv:.{nd}e}"
            return f"{xv:.{nd}g}"
        except Exception:
            return str(x)

    def _invert_gas_percent(p_g_val):
        try:
            p = float(p_g_val)
            return 1000.0 * p / (1013.0/100.0)
        except Exception:
            return None

    # ---------- content ----------
    flow.append(Paragraph("<b>PHREI Summary Report</b>", styles['Title']))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(f"<b>Precipitating minerals:</b> {globals().get('minerals_title','—')}", styles['Normal']))
    flow.append(Spacer(1, 6))

    _add_h("PHREEQC paths")
    _pairs_table([
        ("PHREEQC executable", globals().get("PHREEQC_PATH", "—")),
        ("Database file", globals().get("DATABASE", "—")),
        ("PHREEQC input file", globals().get("inputname", "—")),
    ], header=["Key", "Value"])
    _add_h("Inputs")
    _pairs_table(list(inputs.items()), header=["Parameter", "Value"])

    _add_h("Precipitating minerals (M, ρ)")
    mp = globals().get("mineral_props", {})
    rows = [["Mineral", "M (g/mol)", "ρ (g/cm³)"]]
    if mp:
        for name, props in mp.items():
            rows.append([name, _round(props.get("M","—")), _round(props.get("rho","—"))])
    else:
        rows.append(["—","—","—"])
    t = Table(rows, colWidths=[200, 140, 140])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    flow.append(t)

    _add_h("Reservoir minerals (selection)")
    rmins = []
    for i in range(1, 9):
        val = globals().get(f"reservoir_mineral_{i}", "#")
        if val and val != "#":
            rmins.append(val)
    _list_table(rmins, ncols=3, col_width=170)

    _add_h("Model")
    flow.append(Paragraph(str(model), styles['Normal']))

    if stochastic_list:
        _add_h("Stochastic settings", "Heading3")
        _pairs_table(stochastic_list, header=["Key", "Value"])

    _add_h("Half- and zero-porosity times")
    hz = [["Case", "t(50%) [days]", "t(0%) [days]"]] + (half_zero_table or [])
    hz_table = Table(hz, colWidths=[200, 160, 160])
    hz_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))
    flow.append(hz_table)

    _add_h("Figures")
    if main_png and os.path.exists(main_png):
        flow.append(RLImage(main_png, width=480, height=400))
    for p in (oat_pngs or []):
        if p and os.path.exists(p):
            flow.append(Spacer(1, 10))
            flow.append(RLImage(p, width=480, height=400))

    doc.build(flow)
    return True


# ---------- Generate the report ONLY if reportlab is available ----------

# ---------- Prepare sections for the report (ALWAYS define inputs_dict) ----------
inputs_dict = {
    "Flow rate (l/min)": globals().get("flowrate", "—"),
    "Initial porosity (%)": (globals().get("porosity", None) * 100.0) if isinstance(globals().get("porosity", None), (int, float)) else "—",
    "Near-wellbore zone outer diameter (m)": globals().get("nw_diameter_out", "—"),
    "Wellbore outer diameter (m)": globals().get("wb_diameter_out", "—"),
    "Sphericity (-)": globals().get("sphericity", "—"),
    "Average grain size of gravel pack (m)": globals().get("grainsize", "—"),
    "Screened length (m)": globals().get("screened_length", "—"),
    "Reinjection temperature (°C)": globals().get("reinjection_temp", "—"),
    "Reservoir temperature (°C)": globals().get("reservoir_temp", "—"),
    "Production units": globals().get("unit_selected_prod", "—"),
    "Injection units": globals().get("unit_selected_inj", "—"),
    "Initial permeability (m²)": globals().get("initial_permeability_value", "—") if globals().get("mode_var", "") == "permeability" else "—",
}

stoch_list = []
if globals().get("model_type") == "stochastic":
    stoch_settings = globals().get("stochastic_settings", {})
    stoch_list.append(("Seed", stoch_settings.get("seed", "—")))
    stoch_list.append(("Num simulations", stoch_settings.get("num_sim", "—")))

    for sp in globals().get("stochastic_params", []):
        stoch_list.append((
            name_map.get(sp.get("param"), sp.get("param")),
            f"dist={sp.get('dist')}, mean={sp.get('mean')}, "
            f"std={sp.get('std')}, range=[{sp.get('min')},{sp.get('max')}]"
        ))

oat_pngs = []
if globals().get("model_type") == "stochastic":
    for sp in globals().get("stochastic_params", []):
        oat_pngs.append(f"{png_out_oat_prefix}{sp['param']}.png")
        
pdf_name = f"PHREI_summary.pdf"
ok = build_pdf_report(
    pdf_name,
    inputs_dict,
    f"Mode: {model_type if 'model_type' in globals() else 'N/A'}",
    stoch_list,
    summary_rows,
    png_out_all,
    oat_pngs
)
if ok:
    print(f"Summary PDF generated: {pdf_name}")


if not REPORTLAB_OK:
    print("NOTE: reportlab not installed. Install with: pip install reportlab")
else:
    print(f"Summary PDF generated: {pdf_name}")
            
# ------------------------ Organize outputs into timestamped folder ------------------------
from datetime import datetime
import shutil
import glob

run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
run_folder = f"run_{run_timestamp}"

os.makedirs(run_folder, exist_ok=True)

# File patterns to move
patterns = [
    "*.dat",
    "*.sel",
    "*.png",
    "*.svg",
    "*.pdf",
    "*.xlsx",
    "*.txt",
    "*.toml",
]

moved_files = []

for pattern in patterns:
    for fname in glob.glob(pattern):
        try:
            shutil.move(fname, os.path.join(run_folder, fname))
            moved_files.append(fname)
        except Exception:
            pass  # ignore files that are already moved or locked

print(f"\nRun outputs moved to folder: {run_folder}")
if moved_files:
    print("Moved files:")
    for f in moved_files:
        print(" -", f)
