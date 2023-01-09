import argparse
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.console
from PyQt5.QtGui import QKeySequence, QPalette, QColor, QRadioButton, QTextEdit, QMessageBox, QMainWindow, QApplication, QPushButton
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt
import numpy as np
import bisect
from pathlib import Path
from scipy.io import loadmat
from scipy import integrate, signal
from pathlib import Path


from pyqtgraph.dockarea import Dock, DockArea
from pyqtgraph.dockarea.Dock import DockLabel

import inspect

class MyDockLabel(DockLabel):

    def updateStyle(self):

        r = '3px'
        if self.dim:
            fg = '#aaa'
            bg = '#2d4358'
            border = '#2d4358'
        else:
            fg = '#fff'
            #bg = '#66c'
            bg = '#2d4358'
            border = '#2d4358'
        
        if self.orientation == 'vertical':
            self.vStyle = """DockLabel { 
                background-color : %s; 
                color : %s; 
                border-top-right-radius: 0px; 
                border-top-left-radius: %s; 
                border-bottom-right-radius: 0px; 
                border-bottom-left-radius: %s; 
                border-width: 0px; 
                border-right: 2px solid %s;
                padding-top: 3px;
                padding-bottom: 3px;
            }""" % (bg, fg, r, r, border)
            self.setStyleSheet(self.vStyle)
        else:
            self.hStyle = """DockLabel { 
                background-color : %s; 
                color : %s; 
                border-top-right-radius: %s; 
                border-top-left-radius: %s; 
                border-bottom-right-radius: 0px; 
                border-bottom-left-radius: 0px; 
                border-width: 0px; 
                border-bottom: 2px solid %s;
                padding-left: 3px;
                padding-right: 3px;
            }""" % (bg, fg, r, r, border)
            self.setStyleSheet(self.hStyle)

class StepPickerWindow(QMainWindow):  # QMainWindow is the parent class, StepPickerWindow is inherited / child class

    def __init__(self, file_path=None):  # when we call StepPickerWindow() we create an instance of the class and __init__ is used to initialize new instance
                         # it is called only once so all local variables are contained within the definition
        super().__init__()  # super runs init of the parent class -- super() gets the parent instance from QMainWindow, this init is the parent init

        self.event_list = []
        self.step_list = []
        
        self.event_mark_list = []
        self.step_mark_list = []
        self.color_regions = []
        

        # TODO try to place all GUI things together
        self.file_name = file_path
        if self.file_name is None:
            path_to_dir = '/Users/amywang/Desktop/trap-analysis/raw_npy'
            self.file_name, _ = QFileDialog.getOpenFileName(self, 'Open *.np[yz] File', directory=path_to_dir, filter='*.np[yz]')
            print(self.file_name)

        if self.file_name.endswith('.npy'):
            self.time, self.data1, self.data2, self.data3 = np.load(self.file_name, allow_pickle=True)
            self.dict_events, self.merged_events, self.invalid_points = None, None, None


        elif self.file_name.endswith('.npz'):
            npz_file = np.load(self.file_name, allow_pickle=True)
            self.time, self.data1, self.data2, self.data3 = npz_file['raw_data']
            self.dict_events = npz_file['dictionary'].tolist()
            self.merged_events = npz_file['merged'].tolist()
            self.invalid_points = npz_file['invalid_points'].tolist()

        area = DockArea()
        dock1 = Dock('Traces', size=(2000, 1000))
#        dock1.label = MyDockLabel(dock1._name, dock1, False)
        dock2 = Dock('Tracker', size=(100, 20))
        dock2.hideTitleBar()
        dock3 = Dock('Buttons', size=(20, 100))
        dock3.hideTitleBar()
        # dock2.label.setOrientation('vertical')
        # dock3.label = MyDockLabel(dock3._name, dock3, False)

        #print(QPalette.Window, QColor('gray'))

        area.addDock(dock1, 'left')      ## place dock1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        area.addDock(dock2, 'top')
        area.addDock(dock3, 'right', dock2)

        self.setCentralWidget(area)  # self is the instance
        self.resize(1000, 1000)
        self.setWindowTitle('Step Picker')
        self.text_edit = QTextEdit()
        #############################################################################################
        # DOCK1: TRACE VIEWING AND CLICKING

        window_1 = pg.GraphicsLayoutWidget()
        window_1.setBackground('#2d4358')
        self.label = pg.LabelItem(justify='left')
        window_1.addItem(self.label)
        dock1.addWidget(window_1)


        # TODO try to separate these out from GUI stuff
        # X_index_list are stored indices in the data which makes colorizing easier


        self.delete_point = False

        def subplots(data_array, row_number, label):
            p = window_1.addPlot(row=row_number, col=0)
            p.plot(self.time, data_array, pen='w')
            p.setLimits(xMin=np.amin(self.time), xMax=np.amax(self.time))
            p.showGrid(x=True, y=True, alpha=1)
            p.setLabel('left', label)
            p.setAutoVisible(x=True,y=True)
            p.setMouseEnabled(y=False)
            p.setMenuEnabled(False)
            return p

        self.main_trace = subplots(self.data1, row_number=1, label='Trap 1 Main (pN)')
        self.special_data_list = [self.data1, self.data2, self.data3]

        special_plot_names = ['Trap 1 (pN)', 'Trap 2  (pN)', 'Stage (nm)']
        self.special_plots = [subplots(data, row_number=(idx + 2), label=name)
                              for idx, (data, name) in enumerate(zip(self.special_data_list, special_plot_names))]

        def parse_npz_dict():
            npz_event_list, npz_step_list = [], []
            for event in self.dict_events:    
                npz_event_list = npz_event_list + event['bounds']
                npz_step_list = npz_step_list + event['steps']

            return npz_event_list, npz_step_list

        def load_npz_bound_marks(npz_event_list):
            timepoint_idx = np.searchsorted(self.time, npz_event_list)
            for t_val, t_val_idx in zip(npz_event_list, timepoint_idx):
                t_idx = (np.array([t_val_idx]),)  # store as same form as idx from pyqtgraph syntax 
                self.pick_event_bounds(t_val, t_idx)

        def load_npz_step_marks(npz_step_list):
            timepoint_idx = np.searchsorted(self.time, npz_step_list)
            for t_val, t_val_idx in zip(npz_step_list, timepoint_idx):
                t_idx = (np.array([t_val_idx]),)  # store as same form as idx from pyqtgraph syntax 
                self.pick_step_points(t_val, t_idx)        

        if self.file_name.endswith('.npz'):
            npz_event_list, npz_step_list = parse_npz_dict()
            load_npz_bound_marks(npz_event_list)
            load_npz_step_marks(npz_step_list)
            self.colorize(self.merged_events)

        def update():
            self.region.setZValue(10)
            self.move_plot_x_range()
            # min_x_value, max_x_value = self.region.getRegion()  # Return the values at the edges of the region.
            # for plot in self.special_plots:
            #     plot.setXRange(min_x_value, max_x_value, padding=0)

        self.region = pg.LinearRegionItem()  # marks region in plots

        self.main_trace.addItem(self.region)
        self.region.sigRegionChanged.connect(update)
        self.region.setRegion([0, 10])  # sets original range

        def update_region(window, view_range):
            rgn = view_range[0]  # Return a the view’s visible range as a list: [[xmin, xmax], [ymin, ymax]]
            self.region.setRegion(rgn)
            # self.display_event_regions()
            self._update_tracker(returned_merged_event=None, invalid_points=[])

        for plot in self.special_plots:
            plot.sigRangeChanged.connect(update_region)

        self.vlines = [pg.InfiniteLine(angle=90, movable=False) for _ in self.special_plots]
        for plot, vline in zip(self.special_plots, self.vlines):
            plot.addItem(vline, ignoreBounds=True)

        #############################################################################################
        
        # DOCK 2: Step Tracker

        dock2.addWidget(self.text_edit)


        #############################################################################################
        # DOCK 3: Widgets

        def save_button():
            self.save()


        window_3 = pg.LayoutWidget()
        #window_3 = QHBoxLayout()

        self.event_button = QRadioButton('Event Picker')
        self.save_button = QPushButton('Save')

        self.staircase_radio_button = QRadioButton('Staircase Picker')
        self.event_button.setChecked(True)
        self.save_button.setDefault(True)

        self.save_button.clicked.connect(save_button)
        # ColorCheckBox = QCheckBox('Bookkeeping')

        # ColorCheckBox.toggled.connect(bookkeeper)

        window_3.addWidget(self.event_button)
        window_3.addWidget(self.staircase_radio_button)
        window_3.addWidget(self.save_button)
        # window_3.addWidget(ColorCheckBox)

        dock3.addWidget(window_3)

        self.show()

        for plot in self.special_plots:
            plot.scene().sigMouseMoved.connect(self.update_vertical_line)
        self.main_trace.scene().sigMouseClicked.connect(self.mouse_clicked)



    ### END OF INITIALIZATION - CLASS LEVEL FUNCTIONS

    def save(self):
        start_char = self.file_name.rfind('/') + 1
        save_dir = 'npz_files/'

        if self.file_name.endswith('.npz'):
            save_name = self.file_name[start_char:-4] + '_revised'
        else:
            save_name = self.file_name[start_char:-4]

        save_dict = np.array(self.dict_events, dtype=object)
        save_merged = np.array(self.merged_events, dtype=object)
        save_invalid_pts = np.array(self.invalid_points, dtype=object)
        raw_data = [self.time, self.data1, self.data2, self.data3]

        np.savez(save_dir + save_name, dictionary=save_dict, merged=save_merged, invalid_points=save_invalid_pts, raw_data=raw_data)

    def move_plot_x_range(self, move_by=0):
        min_x_value, max_x_value = self.region.getRegion()  # Return the values at the edges of the region.
        for plot in self.special_plots:
            plot.setXRange(min_x_value + move_by, max_x_value + move_by, padding=0)

    def keyPressEvent(self, event):  # this is an attribute of the original QMainWindow, by defining it here we are overriding the original defenition
        if event.key() == Qt.Key_D or event.key() == Qt.Key_Backspace:
            self.text_edit.setHtml("Deleting points! Hover over desired point and hold 'D' or 'Backspace'. <br> Press left mouse button to delete event selection. Press right mouse button to delete a step selection.")
            self.delete_point = True
        elif event.key() == Qt.Key_Right:
            self.move_plot_x_range(0.2)
        elif event.key() == Qt.Key_Left:
            self.move_plot_x_range(-0.2)
        elif event.key() == Qt.Key_S:
            self.save()
            self.text_edit.append('Saved!')

            # TODO: scroll self.region to the right when the right arrow key is pressed

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_D or event.key() == Qt.Key_Backspace:
            self.delete_point = False

    def mouse_interaction_data(self, pos):

        mouse_point = self.special_plots[0].vb.mapSceneToView(pos)
        cursor_location = mouse_point.x()
        nearest_t = self.time.flat[np.abs(self.time - cursor_location).argmin()]  # find nearest t value in time array series to mouse_point
        data_index = np.where(self.time == nearest_t)

        return nearest_t, data_index, cursor_location

    def update_vertical_line(self, pos):     
        if any(plot.sceneBoundingRect().contains(pos) for plot in self.special_plots):
            _, index, cursor_location = self.mouse_interaction_data(pos)
            self.label.setText("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: white'> Trap1=%0.1f</span>, <span style='color: white'>Trap2=%0.1f</span>, <span style='color: white'>Stage=%0.1f</span>" % (cursor_location, *[data[index] for data in self.special_data_list]))
            for plot, vline in zip(self.special_plots, self.vlines):
                vline.setPos(plot.vb.mapSceneToView(pos).x())

    def mouse_toggle_step_event(self, evt):
        if evt.button() == 1:
            self.event_button.setChecked(True)
        else:
            self.staircase_radio_button.setChecked(True)

    def mouse_clicked(self, evt):
        pos = evt.scenePos()  ## using signal proxy turns original arguments into a tuple, need scenePos for clicking

        if any(plot.sceneBoundingRect().contains(pos) for plot in self.special_plots):

            nearest_t, index, _ = self.mouse_interaction_data(pos)
            event_index = None

            self.mouse_toggle_step_event(evt)

            if self.delete_point == False:  # left click:
                if self.event_button.isChecked():
                    self.pick_event_bounds(nearest_t, index)
                else:
                    self.pick_step_points(nearest_t, index)
            
            else:  # while 'D' or 'Backspace' button is pressed, delete points
                if self.event_button.isChecked():
                    self.delete_event_point(nearest_t, index)
                else:
                    self.delete_step_point(nearest_t, index)

            self.dict_events, self.merged_events, self.invalid_points = self.map_steps_to_event_bounds()
            self.colorize(self.merged_events)
            returned_merged_event = self._return_merged_event(self.merged_events, nearest_t)

            self._update_tracker(returned_merged_event, self.invalid_points)
            # self.calculate_baseline(5, 30, index)

    def _cursor_orientation(self):
        
        # TODO adjust_cursor_orientation
        start_marks, end_marks = self.event_mark_list[::2], self.event_mark_list[1::2]

        for marks in start_marks:
            for mark in marks:
                mark.setSymbol(['t2'])

        for marks in end_marks:
            for mark in marks:
                mark.setSymbol(['t3'])

        #[[SMark[0].setSymbol(['t2']), SMark[1].setSymbol(['t2']), SMark[2].setSymbol(['t2'])] for SMark in start]
        #[[EMark[0].setSymbol(['t3']), EMark[1].setSymbol(['t3']), EMark[2].setSymbol(['t3'])] for EMark in end]

    def colorize(self, merged_events):
                # TODO put here temporarily

        if len(self.color_regions) > 0: 
            for color_region in self.color_regions:
                for plot in self.special_plots:
                    plot.removeItem(color_region)

        colors = [(50, 50, 200, 100), (96, 128, 0, 100), (122, 0, 153, 100), (77, 77, 77, 100)]

        for event_region in merged_events:
            for n_step in range(0,len(event_region) - 1):
                
                n_rev = (len(event_region) - n_step - 2) % 4
                color_region = [event_region[n_step], event_region[n_step+1]]
                for plot in self.special_plots:
                    pyqt_region = pg.LinearRegionItem(values=color_region, movable=False, brush=colors[n_rev], pen=colors[n_rev])
                    self.color_regions.append(pyqt_region)
                    plot.addItem(pyqt_region)

    def _insort_data(self, nearest_t, event_or_step_list):

        # Use bisect insort to maintain the list in sorted order
        insorted_index = bisect.bisect_left(event_or_step_list, nearest_t)
        bisect.insort(event_or_step_list, nearest_t)

        return insorted_index    

    def pick_event_bounds(self, nearest_t, index):

        marks = [pg.PlotDataItem(x=np.array([nearest_t]), y=np.array(data[index])) for data in self.special_data_list]

        # print(f'EVENT BOUNDS: {[np.array(data[index]) for data in self.special_data_list]}')

        insorted_index = self._insort_data(nearest_t, self.event_list)

        self.event_mark_list.insert(insorted_index, marks)  # track cursor marks in a list

            # event_bound_region = np.split(self.data1, event_index_list)[1::2]  # splits data based on start/stop ends

        self._cursor_orientation()
        
        for plot, mark in zip(self.special_plots, marks):
            plot.addItem(mark, ignoreBounds=True)

        # self.colorize_event_bounds(insorted_index, index)
        

        # _ = color_events(nearest_t, index)


    def pick_step_points(self, nearest_t, index):

        insorted_index = self._insort_data(nearest_t, self.step_list)

        #for plot, mark in zip(self.special_plots, marks):
            #plot.addItem(mark, ignoreBounds=True)

        marks = []
        for plot, data in zip(self.special_plots, self.special_data_list):
            marks.append(plot.plot(x=np.array([nearest_t]), y=np.array(data[index]), symbol=['o']))
            #plot.plot(x=np.array([nearest_t]), y=np.array(data[index]), pen=(54,55,55), symbolBrush=(55,55,55), symbolPen='w', symbol='s', symbolSize=14, name="symbol='s'")
        self.step_mark_list.insert(insorted_index, marks)

    def _delete_point(self, nearest_t, event_or_step_list, mark_list):
        if len(event_or_step_list) == 0:
            return

        # Determine if point exists at click location
        distances = np.abs(event_or_step_list - nearest_t)
        min_x, max_x = self.region.getRegion()
        region_width = max_x - min_x
        if distances.min() > region_width / 50:
            return

        # Remove point
        delete_index = distances.argmin()
        event_or_step_list.pop(delete_index)
        
        # Remove mark for point
        marks = mark_list[delete_index]
        mark_list.pop(delete_index)
        for plot, mark in zip(self.special_plots, marks):
            plot.removeItem(mark)

    def delete_event_point(self, nearest_t, index):
        self._delete_point(nearest_t, self.event_list, self.event_mark_list)
        self._cursor_orientation()  # call this function after the event_mark_list is updated 

    def delete_step_point(self, nearest_t, index):
       self._delete_point(nearest_t, self.step_list, self.step_mark_list)

    # def calculate_baseline(self, offset, windowing_range, index):
    #     if len(self.event_list) % 2 == 0:
    #         # event_end_times = np.array(self.event_list[1:even_length:2])
    #         # event_end_idx = np.where(self.time == event_end_times[:, np.newaxis])[1]
    #         event_end_idx = int(index[0])
    #         baseline = [np.mean(data[(event_end_idx+offset):(event_end_idx+windowing_range)]) for data in self.special_data_list[:2]]
    #         # print(event_end_idx)
    #         # baseline = [np.mean(data[np.asarray(event_end_idx + offset)[:, np.newaxis] + np.arange(windowing_range)], axis=1) for data in self.special_data_list[:2]]
    #         baseline = np.array(baseline)
    #         self.text_edit.append(f"Baseline: {baseline}")

    def map_steps_to_event_bounds(self):

        even_length = 2 * (len(self.event_list) // 2)
        event_array, step_array = np.array(self.event_list[:even_length]), np.array(self.step_list)
        
        # Reshape event data to display event regions:
        event_regions = np.array(self.event_list[:even_length]).reshape(-1, 2)

        # assign multi-step picks to event
        bin_assign = np.digitize(step_array, event_array) - 1
        event_region_assign = bin_assign / 2  # / instead of // to get rid of non-integer values
        dict_events = [{'bounds': region.tolist(), 'steps': step_array[event_region_assign == idx].tolist()} for idx, region in enumerate(event_regions)]

        merged_events = [sorted(dict_events[n_event]['bounds'] + dict_events[n_event]['steps']) for n_event in range(len(dict_events))]

        invalid_indices, = np.where(bin_assign % 2)
        invalid_points = step_array[invalid_indices]

        for idx, mark in enumerate(self.step_mark_list):
            marks = self.step_mark_list[idx]
            color = 'r' if idx in invalid_indices else 'b'
            for mark in marks:
                mark.setSymbolBrush(color)

        return dict_events, merged_events, invalid_points

    def _return_merged_event(self, merged_events, nearest_t):

        even_length = 2 * (len(self.event_list) // 2)

        event_start_times = np.array(self.event_list[:even_length:2])
        event_end_times = np.array(self.event_list[1:even_length:2])
        in_range = np.logical_and(event_start_times <= nearest_t, event_end_times >= nearest_t)

        if np.any(in_range):
            event_indices, = np.where(in_range)
            event_idx = event_indices[0]
            returned_merged_event = merged_events[event_idx]
        else:
            return

        return returned_merged_event

    def _update_tracker(self, returned_merged_event, invalid_points):

        even_length = 2 * (len(self.event_list) // 2)
        event_regions = np.array(self.event_list[:even_length]).reshape(-1, 2)
        min_x, max_x = self.region.getRegion()
        in_range = np.logical_and(event_regions[:, 0] >= min_x, event_regions[:, 1] <= max_x)
        display_regions = event_regions[in_range]
        display_regions_str = map(lambda x: '[{:.3f}, {:.3f}]'.format(x[0], x[1]), display_regions)
        display_regions_str = ', '.join(display_regions_str)

        self.text_edit.setHtml(f"Events: {display_regions_str}")

        if returned_merged_event is not None:
            self.text_edit.append(f"Updated step list: {np.around(returned_merged_event,3)}")
        if len(invalid_points) > 0:
            invalid_points_str = ', '.join(['{:.3f}'.format(point) for point in invalid_points])
            self.text_edit.append(f"<span style='color: red'> <b> UNBOUND POINTS: </b> {invalid_points_str} </span>")
    
    # def split_data(self, insorted_index, index):

    #     idx = int(index[0])
    #     print(self.event_index_list)
    #     self.event_index_list.insert(insorted_index, idx)

    #     even_length = 2 * (len(self.event_index_list) // 2)

    #     split_time, split_data = None, None

    #     if even_length > 0:
    #         split_indices = self.event_index_list[:even_length]
    #         split_time = np.split(self.time, split_indices)[1::2]
    #         split_data = [np.split(data, split_indices)[1::2] for data in self.special_data_list]

    #     return split_time, split_data



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--file-path', default=None)
    #parser.add_argument('--file-path', default='/Volumes/AW_Drive/r551a_from_backup/2.)_25nM_R551A_alpha_11.mat')
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = StepPickerWindow(args.file_path)

 
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        app.exec_()
        if window.dict_events is not None:
            window.save()

