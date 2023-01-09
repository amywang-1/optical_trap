# Convert all matlab files to npz files containing proper data file formatting

import sys
import argparse
import numpy as np
import glob
from pathlib import Path
from scipy.io import loadmat
from scipy import integrate, signal
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtWidgets import QFileDialog


class FileSelection(QWidget):

    def __init__(self, file_path, file_type):
        super().__init__()

        path_to_dir = '../'
        self.file_names = file_path
        self.file_type = file_type

        if self.file_names == None:

            if self.file_type == 'Directory':
                self.path = QFileDialog.getExistingDirectory(self, "Select Directory")  # select the folder and get all .mat contents from directory
                mat_file_names = self.path + '/*.mat'
                self.file_names = glob.glob(mat_file_names)
            elif self.file_type == 'File':
                self.file_names, _ = QFileDialog.getOpenFileNames(self, 'Open *.mat File', directory=path_to_dir, filter='*.mat')  
                self.path = self.file_names[0].rsplit('/', 1)[-2]
            else:
                print('file_type should be either Directory or File')

        def decimate_stage_array(stage_array):
            decimate = -7e3 * signal.decimate(signal.decimate(stage_array, 5), 8)
            decimated_stage_array = integrate.cumtrapz(np.diff(decimate), initial=0)
            decimated_stage_array = np.append(decimated_stage_array, decimated_stage_array[-1])
            return decimated_stage_array

        def load_from_mat(loaded_data):
            time_array = np.array(loaded_data['ForceOne']['timeArray'][0,0][0])
            force_one_array = np.array(loaded_data['ForceOne']['decimatedArray'][0,0][0])
            force_two_array = np.array(loaded_data['ForceTwo']['decimatedArray'][0,0][0])
            stage_array = loaded_data['stageDecimatedArray'][0]
            decimated_stage_array = np.array(decimate_stage_array(stage_array))
            raw_data = [time_array, force_one_array, force_two_array, decimated_stage_array]
            return raw_data

        # def load_zero_force_data(loaded_data):
            
        
        def save(file_name, raw_data):
            folder_name = self.path.rsplit('/', 1)[-1]  # takes all elements after the last slash 
            save_dir = 'raw_npy/' + folder_name + '/'
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            
            mat_name = file_name.rsplit('/', 1)[-1]  # takes all elements after the last slash 
            save_name = mat_name[:-4] # + '_raw'

            np.save(save_dir + save_name, raw_data)


        for file_name in self.file_names:
            print(file_name)
            loaded_data = loadmat(file_name)
            if 'ForceOne' in loaded_data:  # if the mat file contains force and stage traces (i.e. not calibration files)
                print(loaded_data['ForceOne'].dtype)
                raw_data = load_from_mat(loaded_data)
                save(file_name, raw_data)
            else:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()  # without argparse, getopenfilenames does not close
    parser.add_argument('--file-path', default=None)
    parser.add_argument('--file-type', default='Directory')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    ex = FileSelection(args.file_path, args.file_type)
    

# path_to_dir = '/Desktop/analysis/'
# file_name, _ = QFileDialog.getOpenFileName('Open *.mat File', directory=path_to_dir, filter='*.mat')

# time, data1, data2, data3 = load_from_mat(file_name)


