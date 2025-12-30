# -*- coding: utf-8 -*-

"""
This file is part of the Superflat Evaluation Toolkit

This file provides an interface to the data structures of the Zygo.xyz file format
The XYZfile class stores the file metadata and provides a fast access to the stored phase image

"""

__author__ = "François Polack"
__copyright__ = "2022, Superflat-PCP project"
__email__ = "superflat-pcp@synchrotron-soleil.fr"
__version__ = "0.1.0"


import tkinter
from tkinter import filedialog
from pathlib import Path
import time
import numpy as np


class XYZfile(object):
    """This class wraps the structure of a Zygo data file stored in one of the two following  text formats of MX software,
         either the .xyz format either the ascii file format. These 2 formats share the same header structure.

    The `openFile` function only loads the measurement metadata from the file header into the object
    The phase data can be loaded in a user array by a subsequent call to `getPhase`
    """

    def __init__(self):
        # file variables
        self.filepath = ""
        """ full path to the file """
        self.Format = 0
        """  Format= 1 for XYZ files ; Format=2 for  Zygo ASCII files  """
        self.data = -1
        """ Pointer to the phase data when the file has been open """
        # variables read from the header
        self.CreatorSoft = 0
        """ Software which created the file.\n Possible values: unknown (0), MetroPro (1), MetroBASIC (2), and d2bug (3) """
        self.Version = [0, 0, 0]
        """ Version of the creator software """
        self.SoftDate = ""
        """ Date of issue of the creator software """
        self.IntensRect = [0, 0, 0, 0]
        """ (xpos,ypos,width, height)   The rectangle of intensity data in camera coordinates (pixels) """
        self.PhaseRect = [0, 0, 0, 0]
        """ (xpos,ypos,width, height)   The rectangle of phase data in camera coordinates (pixels) """
        self.NumBuckets = 0
        """ number of stacked intensity frame in the intensity data chunk """
        self.IntensRange = 0
        """ maximun intensity value """
        self.Comment = ""
        """ a user entered free comment """
        self.PartSerialNumber = ""
        """ user entered information on the measured object """
        self.PartNumber = ""
        """ user entered information on the measured object """
        self.Source = 0
        """ A value of 0 indicates the data is from an instrument; 1 indicates that the data was generated. """
        self.InterfScaleFactor = 0
        """ (float) Interferometric scaling factor. It is 1. if the part is measured in transmission 1/2. if measured in reflection """
        self.Wavelength = 0
        """ The wavelength the measurement was done at """
        self.NumericAperture = 0
        """" Numeric aperture of the measuring objective, if any """
        self.Obliquity = 1.0
        """Correction factor for Mirau objective 1.0 = no correction """
        self.PixelSize = 0
        """ pixel resolution (in m) """
        self.Timestamp = 0
        """ Time the measurement was done at. It is the number of seconds since 0:00:00 January 1, 1970 """
        self.CameraSize = [0, 0]
        """ CameraWidth CameraHeight """
        self.System = [0, 0, 0, 0]
        """ SystemType SystemBoard SystemSerial InstrumentId """
        self.ObjectiveName = ""
        """ objective name if any """
        self.AcquireMode = 0
        """ Acquisition Mode control. The settings are: phase (0), fringe (1), or scan (2). """
        self.IntensAvgs = 0
        """ Average number; 0 or 1 : no averaging """
        self.AGC = [0, 0, 0, 0, 0]
        """ AGC(on/off)  TargetRange LightLevel MinMod MinModPts """
        self.PZT = [0, 0, 0]
        """ PZTCal PZTGain PZTGainTolerance """
        self.PhaseRes = 0
        """ Resolution of the fringe interpolation.  It is 0 for LowRes, interpolation factor= 4096 and 1 fo HighRes, interpolation factor 32768 """
        self.PhaseAvgs = 0
        """ Average number; 0 or 1 : no averaging """
        self.ConnectionProc = [0, 0, 0, 0, 0]
        """ MinimumAreaSize DisconAction DisconFilter ConnectionOrder RemoveTiltBias  """
        self.DataSign = 0
        """ 0: normal mode, 1: inverted mode  (not used by these scripts)"""
        self.CodeVType = 0
        """ Whether the phase data represents a wavefront (0) or a surface (1). """
        self.SubtractSysErr = 0
        """ Indicates whether or not the system error was subtracted from the phase data. A value of 1 indicates that it was subtracted; a value of 0 indicates it was not """
        self.SysErrFile = ""
        """ A user-entered name of the file containing the system error data."""
        self.RefractiveIndex = 1.0
        """ user specified index of the part """
        self.PartThickness = 0
        """ User specified thickness of the part (in meter) """
        self.ZoomDesc = ""
        """ This 7-character string is the value of the image zoom used during data acquisition. """
        # Phase data

    ## This function reads the file metadata  of the header and get a pointer to the data
    ## The data can be obtain in a numpy ndarray with getPhase
    def openFile(self, filename=""):
        """Open, in read mode, a Zygo data  file in one of the available text format, '.xyz' or '.ascii' and load the data header in the `self.header` member

        The phase data are not loaded, and can be requested at any time by calling  the `getPhase` method\n
        **NB:** Import of '.ascii' files is not yetfully validated
        Parameters
        ---------------
        `filename` [optional] : the full qualified path of the file to open.\n
        if not given the user will be prompted a File-Open dialog\n
        Returns
        --------------
        **True** if the file was opened and the `header` was succesfully read; **False** otherwise
        """
        print("open:", filename)
        if Path(filename).is_file():
            self.filepath = filename
        else:
            tkinter.Tk().withdraw()
            self.filepath = filedialog.askopenfilename(
                title="open a Zygo.xyz data file",
                filetypes=(("Zygo XYZ", "*.xyz"), ("Zygo ascii", "*.ascii")),
            )
        print(self.filepath)

        acqMode = ("phase", "fringe", "scan")

        # 尝试不同的编码方式
        file_content = None
        for encoding in ["utf-8", "gbk", "latin-1"]:
            try:
                with open(self.filepath, "r", encoding=encoding) as file:
                    file_content = file.read()
                break
            except UnicodeDecodeError:
                if encoding == "latin-1":  # latin-1应该总是成功
                    # 如果还是失败，使用errors='ignore'
                    with open(
                        self.filepath, "r", encoding="utf-8", errors="ignore"
                    ) as file:
                        file_content = file.read()
                continue

        if file_content is None:
            print("Error: Unable to read file with any encoding")
            return False

        # 现在从文件内容中解析
        lines = file_content.splitlines()
        line_idx = 0

        # Line 1: Format
        line = lines[line_idx]
        line_idx += 1
        elem = line.partition(" - Format ")
        if len(elem) != 3:
            print("This file is not a valid Zygo text file : wrong file identifier")
            return False
        self.Format = int(elem[2])
        if self.Format < 1 or self.Format > 2:
            print(self.Format, " is an invalid format value")

        if self.Format == 1 and elem[0] != "Zygo XYZ Data File":
            print(
                "this file IS NOT a  valid Zygo XYZ Data File : wrong identification line"
            )
            return False
        if self.Format == 2:
            if elem[0] != "Zygo ASCII Data File":
                print(
                    "this file IS NOT a  valid Zygo ASCII Data File : wrong identification line"
                )

        # line 2 software
        elem = lines[line_idx].split()
        line_idx += 1
        self.CreatorSoft = int(elem[0])
        for i in range(3):
            self.Version[i] = int(elem[i + 1])
        self.SoftDate = elem[4].strip('"').rstrip('"')
        print("version", self.Version, "  date:", self.SoftDate)

        # line3 intensity image
        elem = lines[line_idx].split()
        line_idx += 1
        for i in range(4):
            self.IntensRect[i] = int(elem[i])
        self.NumBuckets = int(elem[4])
        self.IntensRange = int(elem[5])
        print(
            "intensity rect ",
            self.IntensRect,
            "  num buckets=",
            self.NumBuckets,
            "  intens max=",
            self.IntensRange,
        )

        # line4 phase image
        elem = lines[line_idx].split()
        line_idx += 1
        for i in range(4):
            self.PhaseRect[i] = int(elem[i])
        print("phase rect ", self.PhaseRect)

        # line 5 Comment
        self.Comment = lines[line_idx].strip('"').rstrip('"')
        line_idx += 1
        print("file comment:", self.Comment)

        # line 6 PartSerialNumber
        self.PartSerialNumber = lines[line_idx].strip('"').rstrip('"')
        line_idx += 1
        print("part serial number:", self.PartSerialNumber)

        # line 7 PartNumber
        self.PartNumber = lines[line_idx].strip('"').rstrip('"')
        line_idx += 1
        print("part  number:", self.PartNumber)

        # line 8 image parameters
        elem = lines[line_idx].split()
        line_idx += 1
        self.Source = int(elem[0])
        self.InterfScaleFactor = float(elem[1])
        self.Wavelength = float(elem[2])
        self.NumericAperture = float(elem[3])
        self.Obliquity = float(elem[4])  # elem[5] magnification is unused
        self.PixelSize = float(elem[6])
        self.Timestamp = int(elem[7])
        print(
            "interferometric scale factor ",
            self.InterfScaleFactor,
            "  wavelength ",
            self.Wavelength,
            " m",
        )
        print("pixel size ", 1000 * self.PixelSize, " mm")
        print("timestamp ", time.ctime(self.Timestamp))

        # line 9 camera and system
        elem = lines[line_idx].split()
        line_idx += 1
        for i in range(2):
            self.CameraSize[i] = int(elem[i])
        for i in range(4):
            self.System[i] = int(elem[i + 2])
        self.ObjectiveName = elem[6].strip('"').rstrip('"')
        print("camera field ", self.CameraSize)
        print("system ID:", self.System, "   objective name:", self.ObjectiveName)

        # line 10 Acquisition settings
        elem = lines[line_idx].split()
        line_idx += 1
        self.AcquireMode = int(elem[0])
        self.IntensAvgs = int(elem[1])
        for i in range(3):
            self.PZT[i] = int(elem[i + 2])
        self.AGC[0] = int(elem[5])
        for i in range(1, 3):
            self.AGC[i] = float(elem[i + 5])
        for i in range(3, 5):
            self.AGC[i] = int(elem[i + 5])
        print(
            "acquisition mode:",
            acqMode[self.AcquireMode],
            "  averaging=",
            self.IntensAvgs,
        )
        print("PZT settings ", self.PZT)
        print("AGC setting ", self.AGC)

        # line 11 phase processing
        elem = lines[line_idx].split()
        line_idx += 1
        self.PhaseRes = int(elem[0])
        self.PhaseAvgs = int(elem[1])
        for i in range(5):
            self.ConnectionProc[i] = int(elem[i + 2])
        self.DataSign = int(elem[0])
        self.CodeVType = int(elem[1])
        print(
            "phase resolution ",
            "High Res" if self.PhaseRes == 1 else "Low Res",
            " averaging=",
            self.PhaseAvgs,
        )
        print("connection processing  ", self.ConnectionProc)

        # line 12 System errors
        elem = lines[line_idx].split()
        line_idx += 1
        self.SubtractSysErr = int(elem[0])
        self.SysErrFile = elem[1].strip('"').rstrip('"')
        print(
            "system errors subtracted:",
            self.SubtractSysErr,
            "error file:",
            self.SysErrFile,
        )

        # line 13 Transmission data
        elem = lines[line_idx].split()
        line_idx += 1
        self.RefractiveIndex = float(elem[0])
        self.PartThickness = float(elem[1])
        print("index=", self.RefractiveIndex, "   part thickness=", self.PartThickness)

        if self.Format == 2:
            # line 14 zoom description
            self.ZoomDesc = lines[line_idx].strip('"').rstrip('"')
            line_idx += 1
            print("zoom description:", self.ZoomDesc, "\n")

        if lines[line_idx][0] != "#":
            print("FORMAT ERROR: expected '#' separator NOT FOUND")
            return False

        line_idx += 1

        # Calculate data position
        # 需要计算到data section的字节位置
        # 重新打开文件以获取正确的文件指针位置
        with open(self.filepath, "rb") as file:
            # 跳过已读取的行
            for _ in range(line_idx):
                file.readline()

            if self.Format == 1:  # xyz file
                self.data = file.tell()
            else:
                self.intens = file.tell()
                line = file.readline()
                while line and line[0:1] != b"#":  # skip intensity chunk
                    line = file.readline()
                self.data = file.tell()

        print("ASCII header succesfully read")
        return True

    def getHeight(self, multiplier=1.0):
        """Reads the phase data from thefile and returns it in a `numpy.array` \n
        Possible invalid data are replaced by NaN in the returned array\n
        Parameters:
        -----------
        `multiplier`: (**float**)  [optional] a multiplicative factor which will be applied to all read values.\n
        The default value is 1., and height values will be expressed in meters.\n
        Returns:
        -------------\n
        (`numpy.array`) The array of read values (in meters) , with invalid data replaced by NaNs, optionnally multiplied by `multiplier`.
        """
        if self.Format == 1:  # xyz file
            multiplier *= 1e-6  # XYZ file are defined in µm height unit
            with open(self.filepath) as file:
                file.seek(self.data)

                Data = np.ndarray(shape=(self.PhaseRect[3], self.PhaseRect[2]))
                # print(Data.shape)
                line = file.readline()
                if line[0] == "#":
                    print("No data")
                while line[0] != "#":
                    # skip empty line (anomalous lines in Alba data)
                    if line != "\n":
                        elem = line.rstrip("\n").split(None, 2)
                        if elem[2] == "No Data":
                            Data[
                                int(elem[1]) - self.PhaseRect[1],
                                int(elem[0]) - self.PhaseRect[0],
                            ] = np.nan
                        else:
                            Data[
                                int(elem[1]) - self.PhaseRect[1],
                                int(elem[0]) - self.PhaseRect[0],
                            ] = multiplier * float(elem[2])
                    line = file.readline()
            return Data
        else:  # ASCII file
            multiplier *= (
                self.Wavelength
                * self.InterfScaleFactor
                * self.Obliquity
                / (4096 if self.PhaseRes == 0 else 32768)
            )
            print("---WARNING---  reading ASCII format is not yet validated")
            with open(self.filepath) as file:
                file.seek(self.data)
                Data = np.ndarray(shape=(self.PhaseRect[3], self.PhaseRect[2]))
                items = file.readline().split()
                if items[0][0] == "#":
                    print("No data")
                n = 0
                while items[0][0] != "#":
                    print(n, len(items))
                    Data.ravel()[n : n + len(items)] = list(map(int, items))
                    n += len(items)
                    items = file.readline().split()
            Data[np.greater_equal(Data, 2147483640)] = (
                np.nan
            )  #  replace invalid data by nans
            return multiplier * Data

    # return pixel size in m
    def getPixel(self):
        """
        Return
        ------
        the pixel size in  \\(m^{-1}\\) (as a float)

        """
        return self.PixelSize

    def getOrigin(self):
        """
        Return
        ------
        X_origin, Y_origin : (int, in)
            the oordinates (in pixels) of the upper left corner of the phase array in the interferometer camera frame
        """
        return self.PhaseRect[0:2]
