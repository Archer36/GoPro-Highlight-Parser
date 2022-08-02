"""
GoPro Highlight Parser:  https://github.com/icegoogles/GoPro-Highlight-Parser

The code for extracting the mp4 boxes/atoms is from 'Human Analog' (https://www.kaggle.com/humananalog): 
https://www.kaggle.com/humananalog/examine-mp4-files-with-python-only

"""

import os
import sys
import struct
import argparse
import pathlib
import re
import json
import shutil
from copy import deepcopy
from math import floor
from time import sleep

import numpy as np

camtasia_edit_rate = 705600000

camtasia_template_json = pathlib.Path.cwd().joinpath("project-v6.tscproj").read_text()
camtasia_template = json.loads(camtasia_template_json)


def find_boxes(f, start_offset=0, end_offset=float("inf")):
    """Returns a dictionary of all the data boxes and their absolute starting
    and ending offsets inside the mp4 file.

    Specify a start_offset and end_offset to read sub-boxes.
    """
    s = struct.Struct("> I 4s") 
    boxes = {}
    offset = start_offset
    f.seek(offset, 0)
    while offset < end_offset:
        data = f.read(8)               # read box header
        if data == b"": break          # EOF
        length, text = s.unpack(data)
        f.seek(length - 8, 1)          # skip to next box
        boxes[text] = (offset, offset + length)
        offset += length
    return boxes


def parse_highlights(f, start_offset=0, end_offset=float("inf")):
    inHighlights = False
    inHLMT = False
    skipFirstMANL = True

    listOfHighlights = []

    offset = start_offset
    f.seek(offset, 0)

    def read_highlight_and_append(f, list):
        data = f.read(4)
        timestamp = int.from_bytes(data, "big")

        if timestamp != 0:
            list.append(timestamp)

    while offset < end_offset:
        data = f.read(4)               # read box header
        if data == b"": break          # EOF

        if data == b'High' and inHighlights == False:
            data = f.read(4)
            if data == b'ligh':
                inHighlights = True  # set flag, that highlights were reached

        if data == b'HLMT' and inHighlights == True and inHLMT == False:
            inHLMT = True  # set flag that HLMT was reached

        if data == b'MANL' and inHighlights == True and inHLMT == True:

            currPos = f.tell()  # remember current pointer/position
            f.seek(currPos - 20)  # go back to highlight timestamp

            data = f.read(4)  # readout highlight
            timestamp = int.from_bytes(data, "big")  #convert to integer

            if timestamp != 0:
                listOfHighlights.append(timestamp)  # append to highlightlist

            f.seek(currPos)  # go forward again (to the saved position)

    return np.array(listOfHighlights)/1000  # convert to seconds and return


def examine_mp4(filename):
    with open(filename, "rb") as f:
        boxes = find_boxes(f)

        # Sanity check that this really is a movie file.
        def fileerror():  # function to call if file is not a movie file
            print("")
            print("ERROR, file is not a mp4-video-file!")
            print(filename)

            os.system("pause")
            exit()

        try:
            if boxes[b"ftyp"][0] != 0:
                fileerror()
        except:
            fileerror()

        moov_boxes = find_boxes(f, boxes[b"moov"][0] + 8, boxes[b"moov"][1])
       
        udta_boxes = find_boxes(f, moov_boxes[b"udta"][0] + 8, moov_boxes[b"udta"][1])

        ### get GPMF Box
        highlights = parse_highlights(f, udta_boxes[b'GPMF'][0] + 8, udta_boxes[b'GPMF'][1])

        print("")
        print("Filename:", filename)
        print("Found", len(highlights), "Highlight(s)!")
        print('Here are all Highlights: ', highlights)

        return highlights


def parse_highlights(f, start_offset=0, end_offset=float("inf")):
    inHighlights = False
    inHLMT = False
    skipFirstMANL = True

    listOfHighlights = []

    offset = start_offset
    f.seek(offset, 0)

    def read_highlight_and_append(f, list):
        data = f.read(4)
        timestamp = int.from_bytes(data, "big")

        if timestamp != 0:
            list.append(timestamp)

    while offset < end_offset:
        data = f.read(4)               # read box header
        if data == b"":
            break          # EOF

        if data == b'High' and inHighlights is False:
            data = f.read(4)
            if data == b'ligh':
                inHighlights = True  # set flag, that highlights were reached

        if data == b'HLMT' and inHighlights is True and inHLMT is False:
            inHLMT = True  # set flag that HLMT was reached

        if data == b'MANL' and inHighlights is True and inHLMT is True:

            currPos = f.tell()  # remember current pointer/position
            f.seek(currPos - 20)  # go back to highlight timestamp

            data = f.read(4)  # readout highlight
            timestamp = int.from_bytes(data, "big")  #convert to integer

            if timestamp != 0:
                listOfHighlights.append(timestamp)  # append to highlightlist

            f.seek(currPos)  # go forward again (to the saved position)

    return np.array(listOfHighlights)/1000  # convert to seconds and return


def sec2dtime(secs):
    """converts seconds to datetimeformat"""
    milsec = (secs - floor(secs)) * 1000
    secs = secs % (24 * 3600) 
    hour = secs // 3600
    secs %= 3600
    min = secs // 60
    secs %= 60
      
    return "%d:%02d:%02d.%03d" % (hour, min, secs, milsec)


def modify_directory_m_time(dirs: list):
    for new_sub_dir in dirs:
        # Update the modified time of the new directory
        # to match the video time for easy sorting/grouping.
        try:
            shutil.copystat(new_sub_dir[0], new_sub_dir[1])
        except Exception as e:
            print(f"Caught exception: {e}")
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--filepath", type=str,
                        help="Complete path to a MP4 video")

    parser.add_argument("-d", "--directory", type=str,
                        help="Path to a directory containing MP4 videos")

    args = parser.parse_args()

    file_names = list()

    if args.filepath:
        filename = args.filepath
        file_names.append(filename)
    elif args.directory:
        directory = pathlib.Path(args.directory)
        for path in directory.glob("*"):
            if re.search("\.mp4", path.suffix, re.IGNORECASE):
                file_names.append(path)
    else:
        # //////////////
        filename = None  # You can enter a custom filename here istead of 'None'. Otherwise just drag and drop a file on this script
        # //////////////

        if filename is None:
            try:
                counter = 1
                while True:
                    try:
                        file_names.append(sys.argv[counter])
                    except IndexError:
                        if counter > 1:  # at least one file found
                            break
                        else:
                            _ = sys.argv[counter]  # no file found => create IndexError
                    counter += 1

            except IndexError:
                # Print error and exit after next userinput
                print(("\nERROR: No file selected. Please drag the chosen file onto this script to parse for highlights.\n" +
                    "\tOr change \"filename = None\" with the filename in the sourcecode."))
                os.system("pause")
                exit()
        else:
            file_names = [filename]

    # Remove hidden Mac files
    clean_file_names = [file_name for file_name in file_names if not file_name.stem.startswith("._")]
    new_sub_dirs = list()

    for file_name in clean_file_names:

        camtasia_markers = list()

        str2insert = ""

        str2insert += file_name.name + "\n"

        highlights = examine_mp4(file_name)  # examine each file

        highlights.sort()

        highlight_count = len(highlights)

        for i, highl in enumerate(highlights):
            frame_marker = floor(highl*camtasia_edit_rate)
            marker = {"endtime": frame_marker,
                      "time": frame_marker,
                      "value": "Marker",
                      "duration": 0}
            camtasia_markers.append(marker)
            str2insert += "(" + str(i+1) + "): "
            str2insert += sec2dtime(highl) + "\n"

        if highlight_count > 0:
            # Grab the date modified of the original video
            video_mod_time = file_name.stat().st_mtime

            new_dir = directory.joinpath(file_name.stem)

            new_dir.mkdir()

            new_camtasia_template = deepcopy(camtasia_template)
            # Create the TOC/Marker structure
            new_camtasia_template["timeline"]["parameters"] = {"toc": {"keyframes": []}}
            # Insert the list of markers into the new structure
            new_camtasia_template["timeline"]["parameters"]["toc"]["keyframes"] = camtasia_markers
            new_dir.joinpath(f"{file_name.stem}.tscproj").write_text(json.dumps(new_camtasia_template, indent=2))
            camtasia_marker_blob = json.dumps(camtasia_markers, indent=2)
            del new_camtasia_template

            str2insert += "\n"

            highlight_suffix = f"_GP-Highlights_{highlight_count}"
            highlight_file_type = ".txt"
            highlight_file_path = new_dir.joinpath(file_name.stem + highlight_suffix + highlight_file_type)

            highlight_file_path.write_text(str2insert)
            highlight_file_path.write_text(camtasia_marker_blob)

            # Move the video into the new subdirectory
            new_file_name = new_dir.joinpath(file_name.name)
            file_name.replace(new_file_name)
            new_sub_dirs.append((new_file_name, new_dir))

            # Update the modified time of the newly created txt file to
            # match the video time for easy sorting/grouping.
            try:
                pass
                os.utime(highlight_file_path, (video_mod_time, video_mod_time))
            except Exception as e:
                print(f"Caught exception: {e}")
                raise

            print(f"Saved Highlights under: {highlight_file_path}")
    # For some reason I need to wait 30 seconds between creating the
    # new subdirectory and updating its modification timestamp.
    sleep(30)
    modify_directory_m_time(new_sub_dirs)



