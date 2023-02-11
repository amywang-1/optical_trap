# optical_trap

We use the program from doi.org/10.1016/j.cpc.2004.02.012 for calibration, which returns a .mat file. matlab_to_npz.py takes this .mat file and converts it to an .npy file that is readable by npz_gui_dock_step_picker.py.

npz_gui_dock_step_picker.py takes in either npy or npz files.

Event picker describes the event bounds, e.g. the total duration when the signal deviates from baseline. Given an .npy or .npz file, you can select these by left clicking, which will cause a triangle to appear on the gui. A pair of triangles will demarcate the event bounds, indicated by the appearance of a purple block.
In our traces, we see substeps within the event bounds, in which the lifetimes can be extracted with the staircase picker. You can select these by right clicking, which will cause a circle to appear on the gui. If the bounds of the events are selected, various colored blocks will appear, indicating the lifetimes of each sub-step.

force_lifetime_analysis.ipynb is a Jupyter Notebook that processes and extracts force and lifetimes from the annotated traces.

Included are sample data formatted as a npy (raw traces) and npz (annotated traces) file.
