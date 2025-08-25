# Synthetic Dataset Generation with Blender (Windows)

This guide explains how to generate your own **synthetic chess dataset** using Blender on **Windows**. Is based on this repository: 👉 [https://github.com/georg-wolflein/chesscog](https://github.com/georg-wolflein/chesscog)

---

## 🔹 Step 1. Install Blender
1. Download Blender (version ≥ 2.90 recommended) from:  
   👉 [https://www.blender.org/download/](https://www.blender.org/download/)
2. Install it (default path usually is:  
   `C:\Program Files\Blender Foundation\Blender <version>`).

---

## 🔹 Step 2. Install Python Packages in Blender’s Bundled Python
Blender comes with its own Python interpreter. You must install the `chess` library inside it.

1. Open **Command Prompt (cmd)** as an **Administrator**.
2. Navigate to Blender’s Python executable (adjust version if needed):
   ```powershell
   cd "C:\Program Files\Blender Foundation\Blender 4.4\4.4\python\bin"
   ```
3. Run the following commands:
   ```powershell
   .\python.exe -m ensurepip
   .\python.exe -m pip install --upgrade pip
   .\python.exe -m pip install python-chess
   ```

---

## 🔹 Step 3. Have a Look at the Chess Model
The `chess_model.blend` file (the Blender 3D model of the chess set) includes one piece of each type, along with a camera and three lights (one point light and two spotlights). The base chess model was sourced externally 👉 [https://www.turbosquid.com/3d-models/chessboard-with-pieces-2276883](https://www.turbosquid.com/3d-models/chessboard-with-pieces-2276883) and then customized to meet the application requirements. I recommend exploring the Blender file before running the data synthesis script to gain a better understanding of its structure and setup.

---

## 🔹 Step 4. Run the Data Synthesis Script
From the `synthetic_data_generation` project root directory, run:

```powershell
"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe" chess_model.blend --background --python scripts/synthesize_data.py
```

- `--background` → run Blender without GUI.  
- `--python scripts/synthesize_data.py` → runs the dataset generation script.

The output dataset will be created in the default path (`/render` or as configured in the script).

---

## 🔹 Step 5. (Optional) Create YOLO Dataset
To convert from `.json` to a YOLO-style dataset, an additional Jupyter Notebook is provided. It generates `labels` and `images` folders inside the `/dataset` directory.

✅ After completing these steps, you will have your own synthesized chess dataset generated with Blender!
