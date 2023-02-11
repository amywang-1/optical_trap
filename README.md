# optical_trap

We use the program from doi.org/10.1016/j.cpc.2004.02.012 for calibration, which returns a .mat file. matlab_to_npz.py takes this .mat file and converts it to an .npy file that is readable by npz_gui_dock_step_picker.py.

npz_gui_dock_step_picker.py takes in either npy or npz files.

force_lifetime_analysis.ipynb is a Jupyter Notebook that processes and extracts force and lifetimes from the annotated traces.

Included are sample data formatted as a npy (raw traces) and npz (annotated traces) file.
