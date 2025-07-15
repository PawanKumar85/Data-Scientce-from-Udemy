import numpy as np
import os
import sys
import struct
from typing import Tuple, Optional, List
from dataclasses import dataclass
import platform

# Constants
FILE_NAME = "smartcard.bin"
FILE_SIZE = 32768
ROOT_OFFSET_PTR = 0x0000
MF_START_PTR = 0x0002
WRITE_CURSOR_END = FILE_SIZE - 2 * 2  # uint16_t is 2 bytes
READ_CURSOR_END = FILE_SIZE - 2
MAX_DATA_SIZE = 260
MAX_TLV_LEN = 256
MAX_TLVS = 10

# File Type Defines
IS_MF = 0xA0
IS_DF = 0xB0
IS_ADF = 0xC0
MF_FID = 0x3F00
C_NULL = 0xFFFF
ZERO = 0x0000

# Elementary File (EF) Types
EF_TRANSPARENT_UNSHAREABLE = 0x01
EF_LINEAN_UNSHAREABLE = 0x02
EF_CYCLIC_UNSHAREABLE = 0x06
EF_TRANSPARENT_SHAREABLE = 0x41
EF_LINEAR_SHAREABLE = 0x42
EF_CYCLIC_SHAREABLE = 0x46

# APDU Instructions
INS_SELECT_FILE = 0xA4
INS_CREATE_FILE = 0xE0
INS_READ_BINARY = 0xB0
INS_UPDATE_BINARY = 0xD6
INS_READ_RECORD = 0xB2
INS_UPDATE_RECORD = 0xDC

# Status Words
SW_SUCCESS = 0x9000
SW_WARNING_NV_UNCHANGED = 0x6200
SW_PART_CORRUPTED = 0x6281
SW_MEMORY_FAILURE = 0x6581
SW_WRONG_LENGTH = 0x6700
SW_COMMAND_IMCOMPATIBLE = 0x6981
SW_SECURITY_STATUS_NOT_SATISFIED = 0x6982
SW_FILE_INVALID = 0x6983
SW_DATA_INVALID = 0x6A80
SW_CONDITIONS_NOT_SATISFIED = 0x6985
SW_COMMAND_NOT_ALLOWED = 0x6986
SW_EXPECTED_SM_DATA_OBJECTS_MISSING = 0x6987
SW_SM_DATA_OBJECTS_INCORRECT = 0x6988
SW_TECHNICAL_PROBLEM = 0x6F00
SW_FUNC_NOT_SUPPORTED = 0x6A81
SW_FILE_NOT_FOUND = 0x6A82
SW_RECORD_NOT_FOUND = 0x6A83
SW_NOT_ENOUGH_MEMORY = 0x6A84
SW_NC_INCONSISTENT_WITH_TLV = 0x6A85
SW_INCORRECT_P1P2 = 0x6A86
SW_NC_INCONSISTENT_WITH_P1P2 = 0x6A87
SW_REFERENCED_DATA_NOT_FOUND = 0x6A88
SW_FILE_ALREADY_EXIST = 0x6A89
COMMAND_NOT_ALLOWED = 0x6900
PARAMETER_IN_DATA_FIELD = 0x6A80
WRONG_PARAMETER = 0x6B00
SW_INS_NOT_SUPPORTED = 0x6D00
SW_CLA_NOT_SUPPORTED = 0x6E00
BAD_LENGTH = 0x6C00

# Record Modes
NEXT = 0x02
PREVIOUS = 0x03
ABS_CURR = 0x04

# Data Structures
@dataclass
class MFNode:
    FID: np.uint16
    ChildFID: np.uint16
    ChildOffset: np.uint16
    Status: np.uint8
    Type: np.uint8
    FCPOffset: np.uint16
    FCP_total_size: np.uint8
    NextOffset: np.uint16

@dataclass
class NodeSecond:
    ParentOffset: np.uint16
    ChildFID: np.uint16
    ChildOffset: np.uint16
    NextOffset: np.uint16

@dataclass
class FileCursors:
    write_offset: np.uint16
    read_offset: np.uint16

@dataclass
class DFADFNode:
    FID: np.uint16
    ParentFID: np.uint16
    ParentOffset: np.uint16
    Type: np.uint8
    ChildFID: np.uint16
    ChildOffset: np.uint16
    FCPOffset: np.uint16
    FCP_total_size: np.uint8
    NextOffset: np.uint16

@dataclass
class EFNode:
    FID: np.uint16
    ParentOffset: np.uint16
    ParentFID: np.uint16
    Type: np.uint8
    FCPOffset: np.uint16
    FCP_total_size: np.uint8
    DataOffset: np.uint16

@dataclass
class TLV:
    tag: np.uint8
    len: np.uint8
    value: np.ndarray  # uint8 array of MAX_TLV_LEN

@dataclass
class APDU:
    cla: np.uint8
    ins: np.uint8
    p1: np.uint8
    p2: np.uint8
    lc: np.uint8
    data: np.ndarray  # uint8 array of MAX_DATA_SIZE
    data_len: np.uint8
    le: np.uint8
    type: np.uint8
    FID: np.uint16
    fileSize: np.uint16
    RecordSize: np.uint16
    NumberOfRecords: np.uint8
    sfi: np.uint8

@dataclass
class Result:
    value: np.uint16
    sw: np.uint16

@dataclass
class FileInfo:
    fid: np.uint16
    offset: np.uint16
    type: np.uint8

@dataclass
class TagCheck:
    present: bool
    message: str

# Global Variables
CurrentFID = np.uint16(C_NULL)
CurrentOffset = np.uint16(C_NULL)
CurrentFileType = np.uint8(0xFF)
ParentFID = np.uint16(C_NULL)
ParentOffset = np.uint16(C_NULL)
CurrentEF_FID = np.uint16(C_NULL)
CurrentEF_Offset = np.uint16(C_NULL)
CurrentEF_Type = np.uint8(0xFF)
gFID = np.uint16(C_NULL)
record_pointer = np.uint8(0xFF)

# Helper Functions
def print_colored_text(message: str, color: str, end: str = "\n"):
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'blue': '\033[94m',
        'yellow': '\033[93m',
        'white': '\033[97m',
        'cyan': '\033[96m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, colors['blue'])}{message}{colors['reset']}", end=end)

def print_infof(fmt: str, color: str, *args):
    message = fmt % args
    print_colored_text(message, color, end="")

def strcasecmp(s1: str, s2: str) -> int:
    s1_lower = s1.lower()
    s2_lower = s2.lower()
    return (s1_lower > s2_lower) - (s1_lower < s2_lower)

def is_record_ef(ef_type: np.uint8) -> bool:
    return ef_type in [EF_LINEAN_UNSHAREABLE, EF_LINEAR_SHAREABLE,
                      EF_CYCLIC_UNSHAREABLE, EF_CYCLIC_SHAREABLE]

def is_valid_ef_type(type: np.uint8) -> bool:
    return type in [EF_TRANSPARENT_SHAREABLE, EF_TRANSPARENT_UNSHAREABLE] or is_record_ef(type)

def is_valid_df(type: np.uint8) -> bool:
    return type in [IS_DF, IS_ADF]

def is_valid_file_type(type: np.uint8) -> bool:
    return is_valid_df(type) or is_valid_ef_type(type)

def get_root_offset(fp) -> Result:
    fp.seek(ROOT_OFFSET_PTR)
    try:
        value = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
        return Result(value=value, sw=SW_SUCCESS)
    except:
        print_colored_text("Failed to read root offset", "red")
        return Result(value=0, sw=SW_TECHNICAL_PROBLEM)

def check_required_tags(tags: List[TagCheck]) -> bool:
    all_present = True
    for tag in tags:
        if not tag.present:
            print_colored_text(tag.message, "red")
            all_present = False
    return all_present

def extract_file_size(fcp_data: np.ndarray, fcp_len: np.uint16) -> np.uint16:
    pos = 2
    while pos < fcp_len:
        if fcp_data[pos] == 0x80 and fcp_data[pos + 1] == 2:
            return np.uint16((fcp_data[pos + 2] << 8) | fcp_data[pos + 3])
        pos += 2 + fcp_data[pos + 1]
    return np.uint16(0)

def extract_fcp_info(fp, ef_node: EFNode, record_len: np.ndarray, file_size: np.ndarray) -> bool:
    fcp_data = np.zeros(ef_node.FCP_total_size, dtype=np.uint8)
    fp.seek(ef_node.FCPOffset)
    try:
        fcp_data[:] = np.frombuffer(fp.read(ef_node.FCP_total_size), dtype=np.uint8)
        pos = 2
        while pos < ef_node.FCP_total_size:
            tag = fcp_data[pos]
            len = fcp_data[pos + 1]
            if tag == 0x82 and len >= 4:
                record_len[0] = np.uint16((fcp_data[pos + 4] << 8) | fcp_data[pos + 5])
            elif tag == 0x80 and len >= 2:
                file_size[0] = np.uint16((fcp_data[pos + 2] << 8) | fcp_data[pos + 3])
            pos += 2 + len
        return True
    except:
        return False

def get_parent_info(fp, root_offset: np.uint16) -> FileInfo:
    parent = FileInfo(fid=MF_FID, offset=root_offset, type=IS_MF)
    if CurrentFID == MF_FID:
        return parent
    
    parent.fid = CurrentFID
    parent.offset = CurrentOffset
    parent.type = IS_DF
    try:
        fp.seek(parent.offset + 4)  # Offset to FCPOffset in DF_ADF_node
        fcp_offset = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
        fp.seek(parent.offset + 6)  # Offset to FCP_total_size
        fcp_size = np.frombuffer(fp.read(1), dtype=np.uint8)[0]
        
        if fcp_size > 0 and fcp_size <= MAX_TLV_LEN:
            fcp_data = np.zeros(fcp_size, dtype=np.uint8)
            fp.seek(fcp_offset)
            fcp_data[:] = np.frombuffer(fp.read(fcp_size), dtype=np.uint8)
            pos = 2
            while pos < fcp_size:
                if fcp_data[pos] == 0x84:
                    parent.type = IS_ADF
                    break
                if pos + 1 >= fcp_size:
                    break
                len = fcp_data[pos + 1]
                if pos + 2 + len > fcp_size:
                    break
                pos += 2 + len
    except:
        pass
    return parent

def validate_parent_type(parent_type: np.uint8) -> np.uint16:
    if parent_type not in [IS_MF, IS_DF, IS_ADF]:
        print(f"Cannot create child under EF node (parent type: {parent_type:02X})")
        return SW_INCORRECT_P1P2
    return SW_SUCCESS

def write_fcp_data(fp, fcp_offset: np.uint16, apdu: APDU) -> np.uint16:
    fp.seek(fcp_offset)
    try:
        fp.write(apdu.data[:apdu.lc].tobytes())
        fp.flush()
        return SW_SUCCESS
    except:
        print("Failed to write FCP data")
        return SW_MEMORY_FAILURE

def get_node_size(type: np.uint8) -> int:
    return struct.calcsize("<HHHHBHBH") if is_valid_ef_type(type) else struct.calcsize("<HHHHBHHBH")

def read_and_validate_node(fp, offset: np.uint16, target_fid: np.uint16, expected_type: np.uint8, node_type_name: str) -> Tuple[np.uint16, Optional[object]]:
    if offset == C_NULL:
        print(f"Invalid offset for {node_type_name}")
        return SW_FILE_NOT_FOUND, None
    
    try:
        fp.seek(offset)
        if expected_type == IS_MF:
            node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHBH")), dtype=np.uint8)
            node = MFNode(
                FID=np.uint16((node_data[0] << 8) | node_data[1]),
                ChildFID=np.uint16((node_data[2] << 8) | node_data[3]),
                ChildOffset=np.uint16((node_data[4] << 8) | node_data[5]),
                Status=node_data[6],
                Type=node_data[7],
                FCPOffset=np.uint16((node_data[8] << 8) | node_data[9]),
                FCP_total_size=node_data[10],
                NextOffset=np.uint16((node_data[11] << 8) | node_data[12])
            )
        elif expected_type in [IS_DF, IS_ADF]:
            node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
            node = DFADFNode(
                FID=np.uint16((node_data[0] << 8) | node_data[1]),
                ParentFID=np.uint16((node_data[2] << 8) | node_data[3]),
                ParentOffset=np.uint16((node_data[4] << 8) | node_data[5]),
                Type=node_data[6],
                ChildFID=np.uint16((node_data[7] << 8) | node_data[8]),
                ChildOffset=np.uint16((node_data[9] << 8) | node_data[10]),
                FCPOffset=np.uint16((node_data[11] << 8) | node_data[12]),
                FCP_total_size=node_data[13],
                NextOffset=np.uint16((node_data[14] << 8) | node_data[15])
            )
        else:
            node_data = np.frombuffer(fp.read(struct.calcsize("<HHHBHBH")), dtype=np.uint8)
            node = EFNode(
                FID=np.uint16((node_data[0] << 8) | node_data[1]),
                ParentOffset=np.uint16((node_data[2] << 8) | node_data[3]),
                ParentFID=np.uint16((node_data[4] << 8) | node_data[5]),
                Type=node_data[6],
                FCPOffset=np.uint16((node_data[7] << 8) | node_data[8]),
                FCP_total_size=node_data[9],
                DataOffset=np.uint16((node_data[10] << 8) | node_data[11])
            )
        
        node_fid = node.FID
        node_type = node.Type

        if node_fid != target_fid or (expected_type != IS_MF and node_type != expected_type):
            print(f"Invalid {node_type_name} node at {offset:04X} (FID: {node_fid:04X}, Type: {node_type:02X})")
            return SW_FILE_INVALID, None
        
        return SW_SUCCESS, node
    except:
        print(f"Failed to read {node_type_name} node at {offset:04X}")
        return SW_MEMORY_FAILURE, None

def save_cursors(fp, write_offset: np.uint16, read_offset: np.uint16):
    fp.seek(WRITE_CURSOR_END)
    fp.write(np.array([write_offset], dtype=np.uint16).tobytes())
    fp.seek(READ_CURSOR_END)
    fp.write(np.array([read_offset], dtype=np.uint16).tobytes())
    fp.flush()

def init_cursors(fp):
    try:
        fp.seek(WRITE_CURSOR_END)
        write_offset = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
        fp.seek(READ_CURSOR_END)
        read_offset = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
        
        if write_offset >= FILE_SIZE or write_offset == C_NULL:
            save_cursors(fp, np.uint16(0), np.uint16(0))
    except:
        print("Failed to read cursors")
        save_cursors(fp, np.uint16(0), np.uint16(0))

def load_cursors(fp) -> FileCursors:
    fp.seek(WRITE_CURSOR_END)
    write_offset = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
    fp.seek(READ_CURSOR_END)
    read_offset = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
    return FileCursors(write_offset=write_offset, read_offset=read_offset)

def calculate_available_memory(fp) -> np.uint16:
    cursors = load_cursors(fp)
    if cursors.write_offset > WRITE_CURSOR_END:
        return np.uint16(0)
    return np.uint16(WRITE_CURSOR_END - cursors.write_offset)

def print_fcp(apdu: APDU, fp, offset: np.uint16, file_type: np.uint8) -> np.uint16:
    fcp_data = np.zeros(MAX_TLV_LEN, dtype=np.uint8)
    
    # Read the correct node and extract FCP offset/size
    fp.seek(offset)
    if file_type == IS_MF:
        sw, node = read_and_validate_node(fp, offset, apdu.FID, IS_MF, "MF")
        if sw != SW_SUCCESS:
            return sw
        fcp_offset = node.FCPOffset
        fcp_size = node.FCP_total_size
    elif file_type in [IS_DF, IS_ADF]:
        sw, node = read_and_validate_node(fp, offset, apdu.FID, file_type, "DF/ADF")
        if sw != SW_SUCCESS:
            return sw
        fcp_offset = node.FCPOffset
        fcp_size = node.FCP_total_size
    elif is_valid_file_type(file_type):
        sw, node = read_and_validate_node(fp, offset, apdu.FID, file_type, "EF")
        if sw != SW_SUCCESS:
            return sw
        fcp_offset = node.FCPOffset
        fcp_size = node.FCP_total_size
    else:
        print(f"Invalid file type {file_type:02X} for FCP read")
        return SW_INCORRECT_P1P2

    # Read FCP data
    try:
        fp.seek(fcp_offset)
        fcp_data[:fcp_size] = np.frombuffer(fp.read(fcp_size), dtype=np.uint8)
    except:
        print(f"Failed to read FCP data at offset {fcp_offset:04X}")
        return SW_TECHNICAL_PROBLEM

    print_colored_text("Response: ", "blue", end="")
    
    if file_type == IS_MF:
        print_infof("62 %02X ", "green", fcp_size + 2)  # +2 for outer TLV
        i = 2
        has_a5_or_85 = False
        avail = calculate_available_memory(fp)
        
        while i < fcp_size:
            tag = fcp_data[i]
            len_ = fcp_data[i + 1]
            tlv_len = 2 + len_
            
            if tag in [0xA5, 0x85]:
                has_a5_or_85 = True
                print_infof("%02X 04 83 02 %02X %02X ", "green", tag, avail >> 8, avail & 0xFF)
            else:
                print_infof("%02X %02X ", "green", tag, len_)
                for j in range(len_):
                    print_infof("%02X ", "green", fcp_data[i + 2 + j])
            i += tlv_len
        
        if not has_a5_or_85:
            print_infof("A5 04 83 02 %02X %02X ", "green", avail >> 8, avail & 0xFF)
    
    elif is_record_ef(file_type):
        print_infof("62 %02X ", "green", fcp_size - 1)  # +1 for extra byte in 82
        i = 2
        
        while i < fcp_size:
            tag = fcp_data[i]
            len_ = fcp_data[i + 1]
            tlv_len = 2 + len_
            
            if tag == 0x82 and len_ == 4:
                print_infof("82 05 ", "green")
                for j in range(4):
                    print_infof("%02X ", "green", fcp_data[i + 2 + j])
                rec_size = (fcp_data[i + 4] << 8) | fcp_data[i + 5]
                
                file_size = 0
                temp = 2
                while temp < fcp_size:
                    if fcp_data[temp] == 0x80 and fcp_data[temp + 1] == 0x02:
                        file_size = (fcp_data[temp + 2] << 8) | fcp_data[temp + 3]
                        break
                    temp += 2 + fcp_data[temp + 1]
                
                record_count = np.uint8(0 if rec_size == 0 else file_size // rec_size)
                print_infof("%02X ", "green", record_count)
            else:
                print_infof("%02X %02X ", "green", tag, len_)
                for j in range(len_):
                    print_infof("%02X ", "green", fcp_data[i + 2 + j])
            i += tlv_len
    
    elif file_type in [IS_DF, IS_ADF]:
        for i in range(fcp_size):
            print_infof("%02X ", "green", fcp_data[i])
    else:
        print_infof("62 %02X ", "green", fcp_size)
        for i in range(fcp_size):
            print_infof("%02X ", "green", fcp_data[i])
    
    print()
    return SW_SUCCESS

def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def update_write_cursor(fp, new_offset: np.uint16):
    fp.seek(WRITE_CURSOR_END)
    fp.write(np.array([new_offset], dtype=np.uint16).tobytes())
    fp.flush()

def get_next_write_position(fp, required_size: np.uint16) -> np.uint16:
    cursors = load_cursors(fp)
    current_write_pos = cursors.write_offset
    new_write_pos = current_write_pos + required_size
    
    if new_write_pos > WRITE_CURSOR_END:
        print("Not enough memory available for write operation.")
        return SW_NOT_ENOUGH_MEMORY
    
    update_write_cursor(fp, new_write_pos)
    return current_write_pos

def create_empty_file(fp):
    buffer = np.full(FILE_SIZE, 0xFF, dtype=np.uint8)
    fp.seek(0)
    fp.write(buffer.tobytes())
    fp.flush()

def update_current_selection(fp, fid_selected: np.uint16, offset_selected: np.uint16, 
                           type_selected: np.uint8, parent_fid_of_sel: np.uint16, 
                           parent_off_of_sel: np.uint16, type_of_parent_dir: np.uint8):
    global CurrentFID, CurrentOffset, CurrentFileType, ParentFID, ParentOffset
    global CurrentEF_FID, CurrentEF_Offset, CurrentEF_Type, record_pointer
    
    if offset_selected >= FILE_SIZE:
        print(f"Invalid offset selected {offset_selected:04X}")
        return
    
    if is_valid_ef_type(type_selected):
        CurrentEF_FID = fid_selected
        CurrentEF_Offset = offset_selected
        CurrentEF_Type = type_selected
        
        if parent_fid_of_sel != C_NULL and parent_off_of_sel != C_NULL:
            CurrentFID = parent_fid_of_sel
            CurrentOffset = parent_off_of_sel
            if parent_fid_of_sel == MF_FID:
                CurrentFileType = IS_MF
            else:
                try:
                    fp.seek(parent_off_of_sel + 6)  # Offset to type in DF_ADF_node
                    parent_type = np.frombuffer(fp.read(1), dtype=np.uint8)[0]
                    CurrentFileType = parent_type
                except:
                    CurrentFileType = IS_DF
        else:
            print(f"Invalid parent info for EF selection (FID: {parent_fid_of_sel:04X}, Offset: {parent_off_of_sel:04X})")
            CurrentFID = C_NULL
            CurrentOffset = C_NULL
            CurrentFileType = np.uint8(0xFF)
    else:
        CurrentEF_FID = C_NULL
        CurrentEF_Offset = C_NULL
        CurrentEF_Type = np.uint8(0xFF)
        CurrentFID = fid_selected
        CurrentOffset = offset_selected
        CurrentFileType = type_selected
    
    if type_selected == IS_MF:
        ParentFID = C_NULL
        ParentOffset = C_NULL
    elif offset_selected != C_NULL:
        try:
            if type_selected in [IS_DF, IS_ADF]:
                fp.seek(offset_selected)
                node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
                node = DFADFNode(
                    FID=np.uint16((node_data[0] << 8) | node_data[1]),
                    ParentFID=np.uint16((node_data[2] << 8) | node_data[3]),
                    ParentOffset=np.uint16((node_data[4] << 8) | node_data[5]),
                    Type=node_data[6],
                    ChildFID=np.uint16((node_data[7] << 8) | node_data[8]),
                    ChildOffset=np.uint16((node_data[9] << 8) | node_data[10]),
                    FCPOffset=np.uint16((node_data[11] << 8) | node_data[12]),
                    FCP_total_size=node_data[13],
                    NextOffset=np.uint16((node_data[14] << 8) | node_data[15])
                )
                ParentFID = node.ParentFID
                ParentOffset = node.ParentOffset
            elif is_valid_ef_type(type_selected):
                fp.seek(offset_selected)
                node_data = np.frombuffer(fp.read(struct.calcsize("<HHHBHBH")), dtype=np.uint8)
                node = EFNode(
                    FID=np.uint16((node_data[0] << 8) | node_data[1]),
                    ParentOffset=np.uint16((node_data[2] << 8) | node_data[3]),
                    ParentFID=np.uint16((node_data[4] << 8) | node_data[5]),
                    Type=node_data[6],
                    FCPOffset=np.uint16((node_data[7] << 8) | node_data[8]),
                    FCP_total_size=node_data[9],
                    DataOffset=np.uint16((node_data[10] << 8) | node_data[11])
                )
                ParentFID = node.ParentFID
                ParentOffset = node.ParentOffset
        except:
            print(f"Failed to read node at {offset_selected:04X}")
            ParentFID = C_NULL
            ParentOffset = C_NULL
    
    record_pointer = np.uint8(0xFF)

def get_directory_type_string(type: np.uint8) -> str:
    return {
        IS_MF: "MF",
        IS_DF: "DF",
        IS_ADF: "ADF",
        0xFF: "None" if CurrentFID == C_NULL else "Unknown"
    }.get(type, "Unknown")

def get_ef_type_string(type: np.uint8) -> str:
    return {
        EF_TRANSPARENT_SHAREABLE: "EF-Transparent",
        EF_LINEAR_SHAREABLE: "EF-Linear",
        EF_CYCLIC_SHAREABLE: "EF-Cyclic",
        EF_TRANSPARENT_UNSHAREABLE: "EF-Transparent UnShareable",
        EF_LINEAN_UNSHAREABLE: "EF-Linear UnShareable",
        EF_CYCLIC_UNSHAREABLE: "EF-Cyclic UnShareable"
    }.get(type, "Unknown EF")

def get_tag_name(tag: np.uint8) -> str:
    return {
        0x82: "File Descriptor",
        0x83: "File Identifier",
        0x84: "DF Name (AID)",
        0x8A: "Life Cycle Status Byte",
        0x8B: "Security Attributes",
        0x81: "Total File Size",
        0xC6: "PIN Status Template DO",
        0xA5: "Proprietary Information",
        0x85: "File Label",
        0x80: "File Size",
        0x88: "Short File Identifier (SFI)"
    }.get(tag, "Unknown Tag")

def print_apdu(apdu: APDU):
    print_colored_text("\n========== APDU Contents ==========\n", "cyan")
    print_infof("  CLA : %02X\n", "yellow", apdu.cla)
    print_infof("  INS : %02X\n", "yellow", apdu.ins)
    print_infof("  P1  : %02X\n", "yellow", apdu.p1)
    print_infof("  P2  : %02X\n", "yellow", apdu.p2)
    print_infof("  Lc  : %02X (%d bytes)\n", "yellow", apdu.lc, apdu.lc)
    print_infof("  Le  : %02X \n", "yellow", apdu.le)
    
    if apdu.lc > 0:
        print_colored_text("  Data: ", "yellow", end="")
        for i in range(apdu.lc):
            print_infof("%02X ", "green", apdu.data[i])
        print()
    else:
        print_colored_text("  Data: None\n", "red")
    
    print_infof("  Type: %02X\n", "yellow", apdu.type)
    print_infof("  FID : %04X\n", "yellow", apdu.FID)
    print_infof("  SFI : %02X\n", "yellow", apdu.sfi)
    print_infof("  FILE SIZE : %04X\n", "yellow", apdu.fileSize)
    print_infof("  RECORD SIZE : %04X\n", "yellow", apdu.RecordSize)
    print_infof("  RECORD NUMBER : %04X\n", "yellow", apdu.NumberOfRecords)
    print_colored_text("==================================\n", "cyan")

def getFileTypeName(fileType: np.uint8) -> str:
    return {
        IS_MF: "MF",
        IS_DF: "DF",
        IS_ADF: "ADF",
        EF_TRANSPARENT_UNSHAREABLE: "EF Transparent",
        EF_TRANSPARENT_SHAREABLE: "EF Transparent",
        EF_LINEAN_UNSHAREABLE: "EF Linear",
        EF_LINEAR_SHAREABLE: "EF Linear",
        EF_CYCLIC_UNSHAREABLE: "EF Cyclic",
        EF_CYCLIC_SHAREABLE: "EF Cyclic"
    }.get(fileType, "Unknown")

def initialize_smartcard_file():
    try:
        fp = open(FILE_NAME, "rb+")
    except FileNotFoundError:
        fp = open(FILE_NAME, "wb+")
        create_empty_file(fp)
        init_cursors(fp)
    else:
        init_cursors(fp)
    return fp

def handle_power_up_selection(fp):
    global CurrentFID, CurrentOffset, CurrentFileType
    fp.seek(ROOT_OFFSET_PTR)
    root_offset = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
    
    if root_offset != 0xFFFF:
        fp.seek(root_offset)
        node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHBH")), dtype=np.uint8)
        node = MFNode(
            FID=np.uint16((node_data[0] << 8) | node_data[1]),
            ChildFID=np.uint16((node_data[2] << 8) | node_data[3]),
            ChildOffset=np.uint16((node_data[4] << 8) | node_data[5]),
            Status=node_data[6],
            Type=node_data[7],
            FCPOffset=np.uint16((node_data[8] << 8) | node_data[9]),
            FCP_total_size=node_data[10],
            NextOffset=np.uint16((node_data[11] << 8) | node_data[12])
        )
        if node.FID == MF_FID:
            update_current_selection(fp, MF_FID, root_offset, IS_MF, C_NULL, C_NULL, np.uint8(0xFF))
            print_colored_text("Power-up: MF automatically selected.\n", "blue")

def get_status_description(status_word: np.uint16) -> str:
    status_dict = {
        SW_SUCCESS: "Success",
        SW_WRONG_LENGTH: "Wrong length",
        SW_FILE_INVALID: "File invalid",
        SW_COMMAND_NOT_ALLOWED: "Command not allowed - no current EF",
        SW_FILE_NOT_FOUND: "File not found",
        SW_RECORD_NOT_FOUND: "Record not found",
        SW_NOT_ENOUGH_MEMORY: "Not enough memory",
        SW_INCORRECT_P1P2: "Incorrect P1-P2",
        SW_NC_INCONSISTENT_WITH_P1P2: "Nc inconsistent with P1-P2",
        SW_INS_NOT_SUPPORTED: "Instruction not supported",
        SW_CLA_NOT_SUPPORTED: "Class not supported",
        SW_FUNC_NOT_SUPPORTED: "Function not supported",
        COMMAND_NOT_ALLOWED: "No information given",
        SW_DATA_INVALID: "Incorrect parameters in the data field",
        SW_FILE_ALREADY_EXIST: "File Already Exists",
        WRONG_PARAMETER: "Wrong parameters (P1 or P2)",
        SW_COMMAND_IMCOMPATIBLE: "Command incompatible with file structure",
        ZERO: "Invalid Input Command (custom)"
    }
    if status_word & 0xFF00 == 0x6C00:
        return "bad length"
    return status_dict.get(status_word, f"Unknown status: {status_word:04X}")

def print_current_selection_state():
    print_colored_text("\n========== Current Selection State ==========\n", "cyan")
    dir_type = get_directory_type_string(CurrentFileType)
    print_infof("Current Directory: %s (FID: %04X)\n", "yellow", dir_type, CurrentFID)
    
    if CurrentEF_FID != C_NULL:
        ef_type = get_ef_type_string(CurrentEF_Type)
        print_infof("Current EF       : FID %04X (%s)\n", "yellow", CurrentEF_FID, ef_type)
    else:
        print_colored_text("Current EF       : None Selected\n", "red")
    
    print_colored_text("=============================================\n", "cyan")

def reset_global_state():
    global CurrentFID, CurrentOffset, CurrentFileType, ParentFID, ParentOffset
    global CurrentEF_FID, CurrentEF_Offset, CurrentEF_Type, gFID, record_pointer
    CurrentFID = C_NULL
    CurrentOffset = C_NULL
    CurrentFileType = np.uint8(0xFF)
    ParentFID = C_NULL
    ParentOffset = C_NULL
    CurrentEF_FID = C_NULL
    CurrentEF_Offset = C_NULL
    CurrentEF_Type = np.uint8(0xFF)
    gFID = C_NULL
    record_pointer = np.uint8(0xFF)

def handle_special_commands(input_str: str, fp, apdu: APDU) -> bool:
    input_str = input_str.lower()
    if input_str == "memory":
        avail = calculate_available_memory(fp)
        print_colored_text(f"Available Memory: {avail} bytes (4 Bytes for Cursor Pointer)\n", "green")
        return True
    elif input_str == "apdu":
        print_apdu(apdu)
        return True
    elif input_str == "clear":
        clear_screen()
        print_current_selection_state()
        return True
    elif input_str == "reset":
        clear_screen()
        reset_global_state()
        handle_power_up_selection(fp)
        print_current_selection_state()
        print_colored_text("Smartcard state reset to power-up condition\n", "green")
        return True
    return False

def parse_hex_string(hex_str: str, buffer: np.ndarray, buffer_size: int) -> int:
    hex_digits = ''.join(c for c in hex_str if c != ' ')
    if len(hex_digits) % 2 != 0:
        hex_digits += '0'
    
    len_ = 0
    for i in range(0, len(hex_digits), 2):
        if i // 2 >= buffer_size:
            return -1
        try:
            byte = int(hex_digits[i:i+2], 16)
            buffer[len_] = byte
            len_ += 1
        except ValueError:
            return -1
    return len_


def parse_tlv_list(buffer: np.ndarray, total_len: int, tlvs: List[TLV], max_tlvs: int) -> int:
    global gFID
    if buffer is None or total_len <= 0 or max_tlvs <= 0:
        return -1

    pos = 0
    count = 0
    while pos < total_len and count < max_tlvs:
        if pos + 2 > total_len:
            return -1

        tag = buffer[pos]
        pos += 1
        len_ = buffer[pos]
        pos += 1

        if pos + len_ > total_len or len_ > MAX_TLV_LEN:
            return -1

        tlvs[count] = TLV(tag=tag, len=len_, value=np.zeros(MAX_TLV_LEN, dtype=np.uint8))
        tlvs[count].value[:len_] = buffer[pos:pos + len_]

        if tag == 0x83:
            gFID = np.uint16((tlvs[count].value[0] << 8) | tlvs[count].value[1])

        pos += len_
        count += 1

    return count

def process_mf_df_ef(data: np.ndarray, len: int, apdu: APDU) -> np.uint16:
    print("Process MF/DF/ADF")
    tlvs = [TLV(tag=np.uint8(0), len=np.uint8(0), value=np.zeros(MAX_TLV_LEN, dtype=np.uint8)) for _ in range(MAX_TLVS)]
    count = parse_tlv_list(data, len, tlvs, MAX_TLVS)

    if count < 0:
        return SW_DATA_INVALID

    is_mf = False
    is_df = False
    is_ef = False
    is_adf = False
    ef_transparent = False
    ef_linear = False
    ef_cyclic = False
    has_82 = False
    has_83 = False
    has_8A = False
    has_8B = False
    has_81 = False
    has_C6 = False
    has_84 = False
    has_80 = False
    has_85 = False
    has_A5 = False
    has_88 = False
    is_sharable = False
    is_unsharable = False
    record_Size = np.uint16(0)
    fileSize = np.uint16(0)

    for i in range(count):
        tlv = tlvs[i]
        if tlv.tag == 0x82:
            has_82 = True
            if tlv.len == 2:
                if tlv.value[0] in [0x78, 0x38]:
                    if gFID != MF_FID:
                        is_mf = False
                        is_df = True
                    else:
                        is_mf = True
                        is_df = False
                elif tlv.value[0] in [0x41, 0x01]:
                    ef_transparent = True
                    is_ef = True
                    is_df = False
                    is_mf = False
                    is_sharable = tlv.value[0] == 0x41
                    is_unsharable = tlv.value[0] == 0x01
                else:
                    return SW_DATA_INVALID
            elif tlv.len == 4:
                if tlv.value[0] in [0x42, 0x46, 0x02, 0x06]:
                    ef_linear = tlv.value[0] in [0x42, 0x02]
                    ef_cyclic = tlv.value[0] in [0x46, 0x06]
                    is_sharable = tlv.value[0] in [0x42, 0x46]
                    is_unsharable = tlv.value[0] in [0x02, 0x06]
                    is_ef = True
                    is_df = False
                    is_mf = False
                    if (is_ef and (ef_linear or ef_cyclic)):
                        record_Size = np.uint16((tlv.value[2] << 8) | tlv.value[3])
                        apdu.RecordSize = record_Size
                else:
                    return SW_DATA_INVALID
            else:
                return SW_DATA_INVALID
            if tlv.value[1] != 0x21:
                return SW_DATA_INVALID

        if tlv.tag == 0x83:
            if tlv.len != 2:
                return SW_DATA_INVALID
            has_83 = True
            apdu.FID = gFID

        if tlv.tag == 0x84:
            has_84 = True
            if tlv.len < 5 or tlv.len > 16:
                return SW_DATA_INVALID
            if is_ef or is_mf:
                return SW_DATA_INVALID
            is_adf = True
            is_df = False

        if tlv.tag == 0x8A:
            has_8A = True
            if tlv.len != 1 or tlv.value[0] != 0x05:
                return SW_DATA_INVALID

        if tlv.tag == 0x8B:
            has_8B = True
            if tlv.len != 3:
                return SW_DATA_INVALID

        if tlv.tag == 0x80:
            if tlv.len != 2 or not is_ef:
                return SW_DATA_INVALID
            file_size = np.uint16((tlv.value[0] << 8) | tlv.value[1])
            if file_size == 0:
                print_colored_text("File size cannot be zero\n", "red")
                return SW_DATA_INVALID
            apdu.fileSize = file_size
            has_80 = True
            if (ef_linear or ef_cyclic) and record_Size > 0:
                print_infof("EF is record-based. Record size: %d, File size: %d\n", "blue", record_Size, file_size)
                if file_size % record_Size != 0:
                    print_infof("File size not divisible by record size. Invalid data.\n", "red")
                    return SW_DATA_INVALID
                apdu.NumberOfRecords = file_size // record_Size
                print_infof("Number of records calculated: %d\n", "green", apdu.NumberOfRecords)

        if tlv.tag == 0x81:
            if tlv.len != 2 or is_ef or ef_transparent or ef_linear or ef_cyclic:
                return SW_DATA_INVALID
            if tlv.value[0] != 0x00 or tlv.value[1] != 0x00:
                return SW_DATA_INVALID
            has_81 = True

        if tlv.tag == 0xC6:
            has_C6 = True
            if is_ef or ef_transparent or ef_linear or ef_cyclic or tlv.len > 9:
                return SW_DATA_INVALID

        if tlv.tag == 0x85:
            if has_A5:
                print_colored_text("A5 Tag is Already Present.... \n", "red")
                return SW_DATA_INVALID
            has_85 = True
        elif tlv.tag == 0xA5:
            if has_85:
                print_colored_text("85 Tag is Already Present.... \n", "red")
                return SW_DATA_INVALID
            has_A5 = True

        if tlv.tag == 0x88:
            if not is_ef:
                return SW_DATA_INVALID
            if tlv.len == 0:
                print_infof("SFI is present but unsupported (length 0)\n", "yellow")
                continue
            if tlv.len == 1:
                raw_sfi = tlv.value[0]
                if (raw_sfi & 0x07) != 0x00:
                    print_infof("Invalid SFI: last 3 bits must be 000 (got %02X)\n", "red", raw_sfi)
                    return SW_DATA_INVALID
                apdu.sfi = raw_sfi
            else:
                print_infof("Invalid SFI tag length: %d\n", "red", tlv.len)
                return SW_DATA_INVALID
            has_88 = True

    if is_ef and not has_88:
        apdu.sfi = apdu.FID & 0x1F

    if is_mf:
        for i in range(count):
            if tlvs[i].tag not in [0x82, 0x83, 0x8A, 0x8B, 0x81, 0xC6, 0x85, 0xA5]:
                print_infof("Invalid tag %02X for MF\n", "red", tlvs[i].tag)
                return SW_DATA_INVALID
        mf_required = [
            TagCheck(has_82, "Tag 82 not present\n"),
            TagCheck(has_83, "Tag 83 not present\n"),
            TagCheck(has_8A, "Tag 8A not present\n"),
            TagCheck(has_8B, "Tag 8B not present\n"),
            TagCheck(has_81, "Tag 81 not present\n"),
            TagCheck(has_C6, "Tag C6 not present\n")
        ]
        if not check_required_tags(mf_required):
            return SW_DATA_INVALID
        if has_A5 and has_85:
            print_colored_text("Tags A5 and 85 cannot both be present for MF\n", "red")
            return SW_DATA_INVALID
    elif is_df:
        for i in range(count):
            if tlvs[i].tag not in [0x82, 0x83, 0x8A, 0x8B, 0x81, 0xC6, 0x85, 0xA5]:
                print_infof("Invalid tag %02X for DF\n", "red", tlvs[i].tag)
                return SW_DATA_INVALID
        df_required = [
            TagCheck(has_82, "Tag 82 not present\n"),
            TagCheck(has_83, "Tag 83 not present\n"),
            TagCheck(has_8A, "Tag 8A not present\n"),
            TagCheck(has_8B, "Tag 8B not present\n"),
            TagCheck(has_81, "Tag 81 not present\n"),
            TagCheck(has_C6, "Tag C6 not present\n")
        ]
        if not check_required_tags(df_required):
            return SW_DATA_INVALID
        if has_A5 and has_85:
            print_colored_text("Tags A5 and 85 cannot both be present for DF\n", "red")
            return SW_DATA_INVALID
    elif is_adf:
        for i in range(count):
            if tlvs[i].tag not in [0x82, 0x83, 0x84, 0x8A, 0x8B, 0x81, 0xC6, 0x85, 0xA5]:
                print_infof("Invalid tag %02X for ADF\n", "red", tlvs[i].tag)
                return SW_DATA_INVALID
        adf_required = [
            TagCheck(has_82, "Tag 82 not present\n"),
            TagCheck(has_83, "Tag 83 not present\n"),
            TagCheck(has_84, "Tag 84 not present\n"),
            TagCheck(has_8A, "Tag 8A not present\n"),
            TagCheck(has_8B, "Tag 8B not present\n"),
            TagCheck(has_81, "Tag 81 not present\n"),
            TagCheck(has_C6, "Tag C6 not present\n")
        ]
        if not check_required_tags(adf_required):
            return SW_DATA_INVALID
        if has_A5 and has_85:
            print_colored_text("Tags A5 and 85 cannot both be present for ADF\n", "red")
            return SW_DATA_INVALID
    elif is_ef:
        for i in range(count):
            if tlvs[i].tag not in [0x82, 0x83, 0x8A, 0x8B, 0x80, 0x85, 0xA5, 0x88]:
                print_infof("Invalid tag %02X for EF\n", "red", tlvs[i].tag)
                return SW_DATA_INVALID
        ef_required = [
            TagCheck(has_82, "Tag 82 not present\n"),
            TagCheck(has_83, "Tag 83 not present\n"),
            TagCheck(has_8A, "Tag 8A not present\n"),
            TagCheck(has_8B, "Tag 8B not present\n"),
            TagCheck(has_80, "Tag 80 not present\n")
        ]
        if not check_required_tags(ef_required):
            return SW_DATA_INVALID
        if has_A5 and has_85:
            print_colored_text("Tags A5 and 85 cannot both be present for EF\n", "red")
            return SW_DATA_INVALID
    else:
        return SW_DATA_INVALID

    print_colored_text("Mandatory and allowed tags check passed.\n", "blue")

    if is_mf:
        apdu.type = np.uint8(0xA0)
    elif is_df:
        apdu.type = np.uint8(0xB0)
    elif is_adf:
        apdu.type = np.uint8(0xC0)
    elif is_ef:
        if ef_transparent:
            apdu.type = np.uint8(0x41 if is_sharable else 0x01)
        elif ef_linear:
            apdu.type = np.uint8(0x42 if is_sharable else 0x02)
        elif ef_cyclic:
            apdu.type = np.uint8(0x46 if is_sharable else 0x06)

    return SW_SUCCESS

def check_duplicate_sfi(fp, parent_offset: np.uint16, new_sfi: np.uint8, new_fid: np.uint16) -> np.uint16:
    try:
        fp.seek(parent_offset)
        parent_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
        
        fp.seek(parent_offset)
        mf_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHBH")), dtype=np.uint8)
        if len(mf_node_data) == struct.calcsize("<HHHHBHBH") and mf_node_data[7] == IS_MF:
            mf_node = MFNode(
                FID=np.uint16((mf_node_data[0] << 8) | mf_node_data[1]),
                ChildFID=np.uint16((mf_node_data[2] << 8) | mf_node_data[3]),
                ChildOffset=np.uint16((mf_node_data[4] << 8) | mf_node_data[5]),
                Status=mf_node_data[6],
                Type=mf_node_data[7],
                FCPOffset=np.uint16((mf_node_data[8] << 8) | mf_node_data[9]),
                FCP_total_size=mf_node_data[10],
                NextOffset=np.uint16((mf_node_data[11] << 8) | mf_node_data[12])
            )
            parent_type = mf_node.Type
            child_fid = mf_node.ChildFID
            child_offset = mf_node.ChildOffset
            next_offset = mf_node.NextOffset
        else:
            fp.seek(parent_offset)
            df_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
            if len(df_node_data) != struct.calcsize("<HHHHBHHBH"):
                return SW_MEMORY_FAILURE
            df_node = DFADFNode(
                FID=np.uint16((df_node_data[0] << 8) | df_node_data[1]),
                ParentFID=np.uint16((df_node_data[2] << 8) | df_node_data[3]),
                ParentOffset=np.uint16((df_node_data[4] << 8) | df_node_data[5]),
                Type=df_node_data[6],
                ChildFID=np.uint16((df_node_data[7] << 8) | df_node_data[8]),
                ChildOffset=np.uint16((df_node_data[9] << 8) | df_node_data[10]),
                FCPOffset=np.uint16((df_node_data[11] << 8) | df_node_data[12]),
                FCP_total_size=df_node_data[13],
                NextOffset=np.uint16((df_node_data[14] << 8) | df_node_data[15])
            )
            parent_type = df_node.Type
            child_fid = df_node.ChildFID
            child_offset = df_node.ChildOffset
            next_offset = df_node.NextOffset

        if parent_type not in [IS_MF, IS_DF, IS_ADF]:
            return SW_FILE_INVALID

        if child_fid == 0 and child_offset == ZERO and next_offset == ZERO:
            return SW_SUCCESS

        while child_fid != 0 and child_offset != C_NULL:
            fp.seek(child_offset)
            ef_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHBHBH")), dtype=np.uint8)
            if len(ef_node_data) != struct.calcsize("<HHHBHBH"):
                return SW_MEMORY_FAILURE
            ef_node = EFNode(
                FID=np.uint16((ef_node_data[0] << 8) | ef_node_data[1]),
                ParentOffset=np.uint16((ef_node_data[2] << 8) | ef_node_data[3]),
                ParentFID=np.uint16((ef_node_data[4] << 8) | ef_node_data[5]),
                Type=ef_node_data[6],
                FCPOffset=np.uint16((ef_node_data[7] << 8) | ef_node_data[8]),
                FCP_total_size=ef_node_data[9],
                DataOffset=np.uint16((ef_node_data[10] << 8) | ef_node_data[11])
            )

            if is_valid_ef_type(ef_node.Type) and child_fid != new_fid:
                if ef_node.FCP_total_size > MAX_TLV_LEN:
                    return SW_MEMORY_FAILURE
                fp.seek(ef_node.FCPOffset)
                fcp_data = np.frombuffer(fp.read(ef_node.FCP_total_size), dtype=np.uint8)
                pos = 2
                sfi_found = False
                while pos + 2 <= ef_node.FCP_total_size:
                    tag = fcp_data[pos]
                    length = fcp_data[pos + 1]
                    if length == 0 or pos + 2 + length > ef_node.FCP_total_size:
                        break
                    if tag == 0x88:
                        sfi_found = True
                        if fcp_data[pos + 2] == new_sfi:
                            return SW_FILE_ALREADY_EXIST
                    pos += 2 + length
                if not sfi_found and (child_fid & 0xFF) == new_sfi:
                    return SW_FILE_ALREADY_EXIST

            if next_offset == 0 or next_offset == C_NULL:
                break

            fp.seek(next_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )
            child_fid = node2.ChildFID
            child_offset = node2.ChildOffset
            next_offset = node2.NextOffset

        return SW_SUCCESS
    except:
        return SW_MEMORY_FAILURE

def check_fid_in_df_and_children(fp, df_offset: np.uint16, new_fid: np.uint16) -> np.uint16:
    print(f"Checking for duplicate FID {new_fid:04X} in DF/ADF at offset {df_offset:04X}")
    try:
        fp.seek(df_offset)
        df_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
        if len(df_node_data) != struct.calcsize("<HHHHBHHBH"):
            print(f"Failed to read DF/ADF node at offset {df_offset:04X}")
            return SW_MEMORY_FAILURE
        df_node = DFADFNode(
            FID=np.uint16((df_node_data[0] << 8) | df_node_data[1]),
            ParentFID=np.uint16((df_node_data[2] << 8) | df_node_data[3]),
            ParentOffset=np.uint16((df_node_data[4] << 8) | df_node_data[5]),
            Type=df_node_data[6],
            ChildFID=np.uint16((df_node_data[7] << 8) | df_node_data[8]),
            ChildOffset=np.uint16((df_node_data[9] << 8) | df_node_data[10]),
            FCPOffset=np.uint16((df_node_data[11] << 8) | df_node_data[12]),
            FCP_total_size=df_node_data[13],
            NextOffset=np.uint16((df_node_data[14] << 8) | df_node_data[15])
        )

        if df_node.FID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found as DF/ADF FID at {df_offset:04X}")
            return SW_FILE_ALREADY_EXIST

        if df_node.ChildFID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found as DF/ADF ChildFID at {df_offset:04X}")
            return SW_FILE_ALREADY_EXIST

        if df_node.ChildOffset != C_NULL and df_node.ChildOffset < FILE_SIZE:
            fp.seek(df_node.ChildOffset)
            child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
            fp.seek(df_node.ChildOffset + 6)  # Offset to type in DF_ADF_node
            child_type = np.frombuffer(fp.read(1), dtype=np.uint8)[0]
            
            if child_fid == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in child node at {df_node.ChildOffset:04X}")
                return SW_FILE_ALREADY_EXIST

            if child_type in [IS_DF, IS_ADF]:
                status = check_fid_in_df_and_children(fp, df_node.ChildOffset, new_fid)
                if status != SW_SUCCESS:
                    return status

        next_offset = df_node.NextOffset
        while next_offset != ZERO and next_offset != C_NULL and next_offset < FILE_SIZE:
            fp.seek(next_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                print(f"Failed to read NodeSecond at offset {next_offset:04X}")
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )

            if node2.ChildFID == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in NodeSecond ChildFID at {next_offset:04X}")
                return SW_FILE_ALREADY_EXIST

            if node2.ChildOffset != C_NULL and node2.ChildOffset < FILE_SIZE:
                fp.seek(node2.ChildOffset)
                child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
                fp.seek(node2.ChildOffset + 6)
                child_type = np.frombuffer(fp.read(1), dtype=np.uint8)[0]
                
                if child_fid == new_fid:
                    print(f"Error: Duplicate FID {new_fid:04X} found in child node at {node2.ChildOffset:04X}")
                    return SW_FILE_ALREADY_EXIST

                if child_type in [IS_DF, IS_ADF]:
                    status = check_fid_in_df_and_children(fp, node2.ChildOffset, new_fid)
                    if status != SW_SUCCESS:
                        return status

            next_offset = node2.NextOffset

        return SW_SUCCESS
    except:
        print(f"Failed to read DF/ADF node at offset {df_offset:04X}")
        return SW_MEMORY_FAILURE

def check_fid_in_mf_and_children(fp, mf_offset: np.uint32, new_fid: np.uint16) -> np.uint16:
    print(f"Checking for duplicate FID {new_fid:04X} starting at MF offset {mf_offset:04X}")
    try:
        fp.seek(mf_offset)
        mf_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHBH")), dtype=np.uint8)
        if len(mf_node_data) != struct.calcsize("<HHHHBHBH"):
            print(f"Failed to read MF node at offset {mf_offset:04X}")
            return SW_MEMORY_FAILURE
        mf_node = MFNode(
            FID=np.uint16((mf_node_data[0] << 8) | mf_node_data[1]),
            ChildFID=np.uint16((mf_node_data[2] << 8) | mf_node_data[3]),
            ChildOffset=np.uint16((mf_node_data[4] << 8) | mf_node_data[5]),
            Status=mf_node_data[6],
            Type=mf_node_data[7],
            FCPOffset=np.uint16((mf_node_data[8] << 8) | mf_node_data[9]),
            FCP_total_size=mf_node_data[10],
            NextOffset=np.uint16((mf_node_data[11] << 8) | mf_node_data[12])
        )

        if mf_node.FID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found as MF's FID")
            return SW_FILE_ALREADY_EXIST

        if mf_node.ChildFID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found as MF's ChildFID")
            return SW_FILE_ALREADY_EXIST

        if mf_node.ChildOffset != C_NULL and mf_node.ChildOffset < FILE_SIZE:
            fp.seek(mf_node.ChildOffset)
            child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
            if child_fid == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in MF's child node at {mf_node.ChildOffset:04X}")
                return SW_FILE_ALREADY_EXIST

        next_offset = mf_node.NextOffset
        while next_offset != ZERO and next_offset != C_NULL and next_offset < FILE_SIZE:
            fp.seek(next_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                print(f"Failed to read NodeSecond at offset {next_offset:04X}")
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )

            if node2.ChildFID == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in NodeSecond ChildFID at {next_offset:04X}")
                return SW_FILE_ALREADY_EXIST

            if node2.ChildOffset != C_NULL and node2.ChildOffset < FILE_SIZE:
                fp.seek(node2.ChildOffset)
                child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
                fp.seek(node2.ChildOffset + 6)
                child_type = np.frombuffer(fp.read(1), dtype=np.uint8)[0]
                
                if child_fid == new_fid:
                    print(f"Error: Duplicate FID {new_fid:04X} found in child node at {node2.ChildOffset:04X}")
                    return SW_FILE_ALREADY_EXIST

                if child_type in [IS_DF, IS_ADF]:
                    status = check_fid_in_df_and_children(fp, node2.ChildOffset, new_fid)
                    if status != SW_SUCCESS:
                        return status

            next_offset = node2.NextOffset

        return SW_SUCCESS
    except:
        print(f"Failed to read MF node at offset {mf_offset:04X}")
        return SW_MEMORY_FAILURE
    
def check_fid_in_parent_and_siblings(fp, parent_offset: np.uint16, new_fid: np.uint16) -> np.uint16:
    print(f"Checking for duplicate FID {new_fid:04X} in parent and siblings at offset {parent_offset:04X}")
    try:
        fp.seek(parent_offset)
        parent_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
        if len(parent_node_data) != struct.calcsize("<HHHHBHHBH"):
            print(f"Failed to read parent node at offset {parent_offset:04X}")
            return SW_MEMORY_FAILURE
        parent_node = DFADFNode(
            FID=np.uint16((parent_node_data[0] << 8) | parent_node_data[1]),
            ParentFID=np.uint16((parent_node_data[2] << 8) | parent_node_data[3]),
            ParentOffset=np.uint16((parent_node_data[4] << 8) | parent_node_data[5]),
            Type=parent_node_data[6],
            ChildFID=np.uint16((parent_node_data[7] << 8) | parent_node_data[8]),
            ChildOffset=np.uint16((parent_node_data[9] << 8) | parent_node_data[10]),
            FCPOffset=np.uint16((parent_node_data[11] << 8) | parent_node_data[12]),
            FCP_total_size=parent_node_data[13],
            NextOffset=np.uint16((parent_node_data[14] << 8) | parent_node_data[15])
        )

        if parent_node.FID == new_fid:
            print(f"Error: New FID {new_fid:04X} matches parent FID {parent_node.FID:04X}")
            return SW_FILE_ALREADY_EXIST

        if parent_node.ChildFID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found in parent's ChildFID at {parent_offset:04X}")
            return SW_FILE_ALREADY_EXIST

        if parent_node.ParentFID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found in parent's ParentFID at {parent_offset:04X}")
            return SW_FILE_ALREADY_EXIST

        if parent_node.ChildOffset != C_NULL and parent_node.ChildOffset < FILE_SIZE:
            fp.seek(parent_node.ChildOffset)
            child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
            fp.seek(parent_node.ChildOffset + 6)  # Offset to type in DF_ADF_node
            child_type = np.frombuffer(fp.read(1), dtype=np.uint8)[0]

            if child_fid == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in parent's child node at {parent_node.ChildOffset:04X}")
                return SW_FILE_ALREADY_EXIST

            if is_valid_df(child_type):
                status = check_fid_in_df_and_children(fp, parent_node.ChildOffset, new_fid)
                if status != SW_SUCCESS:
                    return status

        next_offset = parent_node.NextOffset
        while next_offset != ZERO and next_offset != C_NULL and next_offset < FILE_SIZE:
            fp.seek(next_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                print(f"Failed to read NodeSecond at offset {next_offset:04X}")
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )

            if node2.ChildFID == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in NodeSecond ChildFID at {next_offset:04X}")
                return SW_FILE_ALREADY_EXIST

            if node2.ChildOffset != C_NULL and node2.ChildOffset < FILE_SIZE:
                fp.seek(node2.ChildOffset)
                child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
                fp.seek(node2.ChildOffset + 6)
                child_type = np.frombuffer(fp.read(1), dtype=np.uint8)[0]

                if child_fid == new_fid:
                    print(f"Error: Duplicate FID {new_fid:04X} found in sibling child node at {node2.ChildOffset:04X}")
                    return SW_FILE_ALREADY_EXIST

                if is_valid_df(child_type):
                    status = check_fid_in_df_and_children(fp, node2.ChildOffset, new_fid)
                    if status != SW_SUCCESS:
                        return status

            next_offset = node2.NextOffset

        if parent_node.ParentFID == MF_FID and parent_node.ParentOffset != C_NULL:
            return check_fid_in_mf_and_children(fp, parent_node.ParentOffset, new_fid)

        return SW_SUCCESS
    except:
        print(f"Failed to read parent node at offset {parent_offset:04X}")
        return SW_MEMORY_FAILURE
    
def check_duplicate_fid_df(fp, parent_offset: np.uint16, new_fid: np.uint16) -> np.uint16:
    print(f"Checking for duplicate FID {new_fid:04X} under DF/ADF at offset {parent_offset:04X}")
    try:
        fp.seek(parent_offset)
        df_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
        if len(df_node_data) != struct.calcsize("<HHHHBHHBH"):
            print(f"Failed to read parent DF/ADF node at offset {parent_offset:04X}")
            return SW_MEMORY_FAILURE
        df_node = DFADFNode(
            FID=np.uint16((df_node_data[0] << 8) | df_node_data[1]),
            ParentFID=np.uint16((df_node_data[2] << 8) | df_node_data[3]),
            ParentOffset=np.uint16((df_node_data[4] << 8) | df_node_data[5]),
            Type=df_node_data[6],
            ChildFID=np.uint16((df_node_data[7] << 8) | df_node_data[8]),
            ChildOffset=np.uint16((df_node_data[9] << 8) | df_node_data[10]),
            FCPOffset=np.uint16((df_node_data[11] << 8) | df_node_data[12]),
            FCP_total_size=df_node_data[13],
            NextOffset=np.uint16((df_node_data[14] << 8) | df_node_data[15])
        )

        if df_node.FID == new_fid:
            print(f"Error: New FID {new_fid:04X} matches parent FID {df_node.FID:04X}")
            return SW_FILE_ALREADY_EXIST

        if df_node.ChildFID == new_fid:
            print(f"Error: Duplicate FID {new_fid:04X} found in parent's ChildFID at {parent_offset:04X}")
            return SW_FILE_ALREADY_EXIST

        if df_node.ChildOffset != C_NULL and df_node.ChildOffset < FILE_SIZE:
            fp.seek(df_node.ChildOffset)
            child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
            if child_fid == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in child node at {df_node.ChildOffset:04X}")
                return SW_FILE_ALREADY_EXIST

        next_offset = df_node.NextOffset
        while next_offset != ZERO and next_offset != C_NULL and next_offset < FILE_SIZE:
            fp.seek(next_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                print(f"Failed to read NodeSecond at offset {next_offset:04X}")
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )

            if node2.ChildFID == new_fid:
                print(f"Error: Duplicate FID {new_fid:04X} found in NodeSecond ChildFID at {next_offset:04X}")
                return SW_FILE_ALREADY_EXIST

            if node2.ChildOffset != C_NULL and node2.ChildOffset < FILE_SIZE:
                fp.seek(node2.ChildOffset)
                child_fid = np.frombuffer(fp.read(2), dtype=np.uint16)[0]
                if child_fid == new_fid:
                    print(f"Error: Duplicate FID {new_fid:04X} found in child node at {node2.ChildOffset:04X}")
                    return SW_FILE_ALREADY_EXIST

            next_offset = node2.NextOffset

        return SW_SUCCESS
    except:
        print(f"Failed to read parent DF/ADF node at offset {parent_offset:04X}")
        return SW_MEMORY_FAILURE


def add_to_mf_chain(fp, parent_offset: np.uint16, new_fid: np.uint16, new_node_offset: np.uint16) -> np.uint16:
    try:
        fp.seek(parent_offset)
        mf_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHBH")), dtype=np.uint8)
        if len(mf_node_data) != struct.calcsize("<HHHHBHBH"):
            print("Failed to read MF node")
            return SW_MEMORY_FAILURE
        mf_node = MFNode(
            FID=np.uint16((mf_node_data[0] << 8) | mf_node_data[1]),
            ChildFID=np.uint16((mf_node_data[2] << 8) | mf_node_data[3]),
            ChildOffset=np.uint16((mf_node_data[4] << 8) | mf_node_data[5]),
            Status=mf_node_data[6],
            Type=mf_node_data[7],
            FCPOffset=np.uint16((mf_node_data[8] << 8) | mf_node_data[9]),
            FCP_total_size=mf_node_data[10],
            NextOffset=np.uint16((mf_node_data[11] << 8) | mf_node_data[12])
        )

        if mf_node.ChildFID == ZERO:
            mf_node.ChildFID = new_fid
            mf_node.ChildOffset = new_node_offset
            fp.seek(parent_offset)
            fp.write(struct.pack("<HHHHBHBH", mf_node.FID, mf_node.ChildFID, mf_node.ChildOffset,
                                mf_node.Status, mf_node.Type, mf_node.FCPOffset,
                                mf_node.FCP_total_size, mf_node.NextOffset))
            fp.flush()
            return SW_SUCCESS

        current_offset = parent_offset
        last_offset = C_NULL

        if mf_node.NextOffset == ZERO:
            new_node2_offset = get_next_write_position(fp, struct.calcsize("<HHHH"))
            if new_node2_offset == SW_NOT_ENOUGH_MEMORY:
                return SW_NOT_ENOUGH_MEMORY

            node2 = NodeSecond(
                ParentOffset=parent_offset,
                ChildFID=new_fid,
                ChildOffset=new_node_offset,
                NextOffset=ZERO
            )
            fp.seek(new_node2_offset)
            fp.write(struct.pack("<HHHH", node2.ParentOffset, node2.ChildFID,
                                node2.ChildOffset, node2.NextOffset))
            fp.flush()

            mf_node.NextOffset = new_node2_offset
            fp.seek(parent_offset)
            fp.write(struct.pack("<HHHHBHBH", mf_node.FID, mf_node.ChildFID, mf_node.ChildOffset,
                                mf_node.Status, mf_node.Type, mf_node.FCPOffset,
                                mf_node.FCP_total_size, mf_node.NextOffset))
            fp.flush()
            return SW_SUCCESS

        current_offset = mf_node.NextOffset
        while True:
            fp.seek(current_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                print("Failed to read NodeSecond")
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )

            if node2.NextOffset == ZERO:
                last_offset = current_offset
                break
            current_offset = node2.NextOffset

        new_node2_offset = get_next_write_position(fp, struct.calcsize("<HHHH"))
        if new_node2_offset == SW_NOT_ENOUGH_MEMORY:
            return SW_NOT_ENOUGH_MEMORY

        node2 = NodeSecond(
            ParentOffset=parent_offset,
            ChildFID=new_fid,
            ChildOffset=new_node_offset,
            NextOffset=ZERO
        )
        fp.seek(new_node2_offset)
        fp.write(struct.pack("<HHHH", node2.ParentOffset, node2.ChildFID,
                            node2.ChildOffset, node2.NextOffset))
        fp.flush()

        fp.seek(last_offset)
        prev_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
        prev_node = NodeSecond(
            ParentOffset=np.uint16((prev_node_data[0] << 8) | prev_node_data[1]),
            ChildFID=np.uint16((prev_node_data[2] << 8) | prev_node_data[3]),
            ChildOffset=np.uint16((prev_node_data[4] << 8) | prev_node_data[5]),
            NextOffset=np.uint16((prev_node_data[6] << 8) | prev_node_data[7])
        )
        prev_node.NextOffset = new_node2_offset
        fp.seek(last_offset)
        fp.write(struct.pack("<HHHH", prev_node.ParentOffset, prev_node.ChildFID,
                            prev_node.ChildOffset, prev_node.NextOffset))
        fp.flush()

        return SW_SUCCESS
    except:
        print("Failed to add to MF chain")
        return SW_MEMORY_FAILURE


def add_to_df_chain(fp, parent_offset: np.uint16, new_fid: np.uint16, new_node_offset: np.uint16) -> np.uint16:
    try:
        fp.seek(parent_offset)
        df_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
        if len(df_node_data) != struct.calcsize("<HHHHBHHBH"):
            print("Failed to read DF/ADF node")
            return SW_MEMORY_FAILURE
        df_node = DFADFNode(
            FID=np.uint16((df_node_data[0] << 8) | df_node_data[1]),
            ParentFID=np.uint16((df_node_data[2] << 8) | df_node_data[3]),
            ParentOffset=np.uint16((df_node_data[4] << 8) | df_node_data[5]),
            Type=df_node_data[6],
            ChildFID=np.uint16((df_node_data[7] << 8) | df_node_data[8]),
            ChildOffset=np.uint16((df_node_data[9] << 8) | df_node_data[10]),
            FCPOffset=np.uint16((df_node_data[11] << 8) | df_node_data[12]),
            FCP_total_size=df_node_data[13],
            NextOffset=np.uint16((df_node_data[14] << 8) | df_node_data[15])
        )

        if df_node.ChildFID == ZERO:
            df_node.ChildFID = new_fid
            df_node.ChildOffset = new_node_offset
            fp.seek(parent_offset)
            fp.write(struct.pack("<HHHHBHHBH", df_node.FID, df_node.ParentFID, df_node.ParentOffset,
                                df_node.Type, df_node.ChildFID, df_node.ChildOffset,
                                df_node.FCPOffset, df_node.FCP_total_size, df_node.NextOffset))
            fp.flush()
            
            fp.seek(parent_offset)
            verify_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHHBHHBH")), dtype=np.uint8)
            return SW_SUCCESS

        current_offset = parent_offset
        last_offset = C_NULL

        if df_node.NextOffset == ZERO:
            new_node2_offset = get_next_write_position(fp, struct.calcsize("<HHHH"))
            if new_node2_offset == SW_NOT_ENOUGH_MEMORY:
                return SW_NOT_ENOUGH_MEMORY

            node2 = NodeSecond(
                ParentOffset=parent_offset,
                ChildFID=new_fid,
                ChildOffset=new_node_offset,
                NextOffset=ZERO
            )
            fp.seek(new_node2_offset)
            fp.write(struct.pack("<HHHH", node2.ParentOffset, node2.ChildFID,
                                node2.ChildOffset, node2.NextOffset))
            fp.flush()

            df_node.NextOffset = new_node2_offset
            fp.seek(parent_offset)
            fp.write(struct.pack("<HHHHBHHBH", df_node.FID, df_node.ParentFID, df_node.ParentOffset,
                                df_node.Type, df_node.ChildFID, df_node.ChildOffset,
                                df_node.FCPOffset, df_node.FCP_total_size, df_node.NextOffset))
            fp.flush()
            return SW_SUCCESS

        current_offset = df_node.NextOffset
        while True:
            fp.seek(current_offset)
            node2_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
            if len(node2_data) != struct.calcsize("<HHHH"):
                print("Failed to read NodeSecond")
                return SW_MEMORY_FAILURE
            node2 = NodeSecond(
                ParentOffset=np.uint16((node2_data[0] << 8) | node2_data[1]),
                ChildFID=np.uint16((node2_data[2] << 8) | node2_data[3]),
                ChildOffset=np.uint16((node2_data[4] << 8) | node2_data[5]),
                NextOffset=np.uint16((node2_data[6] << 8) | node2_data[7])
            )

            if node2.NextOffset == ZERO:
                last_offset = current_offset
                break
            current_offset = node2.NextOffset

        new_node2_offset = get_next_write_position(fp, struct.calcsize("<HHHH"))
        if new_node2_offset == SW_NOT_ENOUGH_MEMORY:
            return SW_NOT_ENOUGH_MEMORY

        node2 = NodeSecond(
            ParentOffset=parent_offset,
            ChildFID=new_fid,
            ChildOffset=new_node_offset,
            NextOffset=ZERO
        )
        fp.seek(new_node2_offset)
        fp.write(struct.pack("<HHHH", node2.ParentOffset, node2.ChildFID,
                            node2.ChildOffset, node2.NextOffset))
        fp.flush()

        fp.seek(last_offset)
        prev_node_data = np.frombuffer(fp.read(struct.calcsize("<HHHH")), dtype=np.uint8)
        prev_node = NodeSecond(
            ParentOffset=np.uint16((prev_node_data[0] << 8) | prev_node_data[1]),
            ChildFID=np.uint16((prev_node_data[2] << 8) | prev_node_data[3]),
            ChildOffset=np.uint16((prev_node_data[4] << 8) | prev_node_data[5]),
            NextOffset=np.uint16((prev_node_data[6] << 8) | prev_node_data[7])
        )
        prev_node.NextOffset = new_node2_offset
        fp.seek(last_offset)
        fp.write(struct.pack("<HHHH", prev_node.ParentOffset, prev_node.ChildFID,
                            prev_node.ChildOffset, prev_node.NextOffset))
        fp.flush()

        return SW_SUCCESS
    except:
        print("Failed to add to DF chain")
        return SW_MEMORY_FAILURE

def check_duplicate_fid(fp, parent_offset: np.uint16, parent_fid: np.uint16, fid: np.uint16, type: np.uint8) -> np.uint16:
    if fid == parent_fid:
        print(f"FID {fid:04X} cannot match parent FID {parent_fid:04X}")
        return SW_FILE_ALREADY_EXIST
    if parent_fid == MF_FID:
        return check_fid_in_mf_and_children(fp, parent_offset, fid)
    elif is_valid_df(type):
        return check_fid_in_parent_and_siblings(fp, parent_offset, fid)
    else:
        return check_duplicate_fid_df(fp, parent_offset, fid)

def write_mf_node(fp, apdu: APDU) -> np.uint16:
    if apdu.FID != MF_FID:
        print_infof("Invalid FID %04X for MF (must be 3F00)\n", "red", apdu.FID)
        return SW_DATA_INVALID

    mf_node = MFNode(
        FID=apdu.FID,
        ChildFID=ZERO,
        ChildOffset=ZERO,
        Status=np.uint8(0x01),
        Type=IS_MF,
        FCPOffset=MF_START_PTR + struct.calcsize("<HHHHBHBH"),
        FCP_total_size=apdu.lc,
        NextOffset=ZERO
    )
    try:
        fp.seek(MF_START_PTR)
        fp.write(struct.pack("<HHHHBHBH", mf_node.FID, mf_node.ChildFID, mf_node.ChildOffset,
                            mf_node.Status, mf_node.Type, mf_node.FCPOffset,
                            mf_node.FCP_total_size, mf_node.NextOffset))
        
        fp.seek(mf_node.FCPOffset)
        fp.write(apdu.data[:mf_node.FCP_total_size].tobytes())
        fp.flush()

        mf_offset = np.uint16(MF_START_PTR)
        fp.seek(ROOT_OFFSET_PTR)
        fp.write(np.array([mf_offset], dtype=np.uint16).tobytes())

        update_write_cursor(fp, mf_node.FCPOffset + mf_node.FCP_total_size)
        update_current_selection(fp, apdu.FID, MF_START_PTR, IS_MF, C_NULL, C_NULL, np.uint8(0xFF))
        print_colored_text("MF created and selected\n", "green")
        return SW_SUCCESS
    except:
        print_colored_text("Failed to write MF node or FCP data\n", "red")
        return SW_MEMORY_FAILURE

def write_df_adf_node(fp, apdu: APDU, new_file_offset: np.uint16, parent_offset: np.uint16, parent_fid: np.uint16) -> np.uint16:
    df_node = DFADFNode(
        FID=apdu.FID,
        ParentFID=parent_fid,
        ParentOffset=parent_offset,
        Type=apdu.type,
        ChildFID=ZERO,
        ChildOffset=ZERO,
        FCPOffset=new_file_offset + struct.calcsize("<HHHHBHHBH"),
        FCP_total_size=apdu.lc,
        NextOffset=ZERO
    )
    try:
        fp.seek(new_file_offset)
        fp.write(struct.pack("<HHHHBHHBH", df_node.FID, df_node.ParentFID, df_node.ParentOffset,
                            df_node.Type, df_node.ChildFID, df_node.ChildOffset,
                            df_node.FCPOffset, df_node.FCP_total_size, df_node.NextOffset))
        fp.flush()
        return SW_SUCCESS
    except:
        print("Failed to write DF/ADF node")
        return SW_MEMORY_FAILURE

def write_ef_node(fp, apdu: APDU, new_file_offset: np.uint16, parent_offset: np.uint16, parent_fid: np.uint16, data_offset: np.uint16) -> np.uint16:
    ef_node = EFNode(
        FID=apdu.FID,
        ParentOffset=parent_offset,
        ParentFID=parent_fid,
        Type=apdu.type,
        FCPOffset=new_file_offset + struct.calcsize("<HHHBHBH"),
        FCP_total_size=apdu.lc,
        DataOffset=data_offset if apdu.fileSize > 0 else C_NULL
    )
    try:
        fp.seek(new_file_offset)
        fp.write(struct.pack("<HHHBHBH", ef_node.FID, ef_node.ParentOffset, ef_node.ParentFID,
                            ef_node.Type, ef_node.FCPOffset, ef_node.FCP_total_size, ef_node.DataOffset))
        fp.flush()

        if apdu.fileSize > 0:
            record_buffer = np.full(apdu.fileSize, 0xFF, dtype=np.uint8)
            fp.seek(data_offset)
            fp.write(record_buffer.tobytes())
            fp.flush()

        return SW_SUCCESS
    except:
        print("Failed to write EF node or data")
        return SW_MEMORY_FAILURE

def create_file(apdu: APDU, fp) -> np.uint16:
    if apdu.type == IS_MF:
        root_res = get_root_offset(fp)
        if root_res.sw != SW_SUCCESS:
            return root_res.sw
        if root_res.value != C_NULL:
            print_infof("MF already present at offset %04X\n", "red", root_res.value)
            return SW_FILE_ALREADY_EXIST
        return write_mf_node(fp, apdu)

    if not is_valid_file_type(apdu.type):
        print_infof("Invalid file type %02X\n", "red", apdu.type)
        return SW_INCORRECT_P1P2

    root_res = get_root_offset(fp)
    if root_res.sw != SW_SUCCESS:
        return root_res.sw
    if root_res.value == C_NULL:
        print_colored_text("No MF found\n", "red")
        return SW_FILE_NOT_FOUND

    parent = get_parent_info(fp, root_res.value)
    status = validate_parent_type(parent.type)
    if status != SW_SUCCESS:
        return status

    status = check_duplicate_fid(fp, parent.offset, parent.fid, apdu.FID, apdu.type)
    if status != SW_SUCCESS:
        print(f"Duplicate FID {apdu.FID:04X} found or invalid. File creation rejected.")
        return status

    if is_valid_ef_type(apdu.type) and apdu.sfi != 0x00:
        status = check_duplicate_sfi(fp, parent.offset, apdu.sfi, apdu.FID)
        print(f"check_duplicate_sfi status: {status:04X}")
        if status != SW_SUCCESS:
            print(f"Duplicate SFI {apdu.sfi:02X} found. EF creation rejected.")
            return status

    node_size = get_node_size(apdu.type)
    total_size = np.uint16(node_size + apdu.lc)
    if is_valid_ef_type(apdu.type):
        total_size += apdu.fileSize

    new_file_offset = get_next_write_position(fp, total_size)
    if new_file_offset == SW_NOT_ENOUGH_MEMORY:
        print("Not enough memory for file creation")
        return SW_NOT_ENOUGH_MEMORY

    fcp_offset = np.uint16(new_file_offset + node_size)
    data_offset = fcp_offset + apdu.lc

    if is_valid_df(apdu.type):
        status = write_df_adf_node(fp, apdu, new_file_offset, parent.offset, parent.fid)
    else:
        status = write_ef_node(fp, apdu, new_file_offset, parent.offset, parent.fid, data_offset)
    if status != SW_SUCCESS:
        return status

    status = write_fcp_data(fp, fcp_offset, apdu)
    if status != SW_SUCCESS:
        return status

    status = add_to_mf_chain(fp, parent.offset, apdu.FID, new_file_offset) if parent.fid == MF_FID else add_to_df_chain(fp, parent.offset, apdu.FID, new_file_offset)
    if status != SW_SUCCESS:
        print(f"Failed to add file to parent chain: {status:04X}")
        return status

    if is_valid_df(apdu.type):
        update_current_selection(fp, apdu.FID, new_file_offset, apdu.type, parent.fid, parent.offset, np.uint8(0xFF))
        print(f"{'ADF' if apdu.type == IS_ADF else 'DF'} created and selected")
    else:
        update_current_selection(fp, apdu.FID, new_file_offset, apdu.type, parent.fid, parent.offset,
                                IS_MF if parent.fid == MF_FID else parent.type)
        print_infof("EF created under %s\n", "green", "MF" if parent.fid == MF_FID else ("ADF" if parent.type == IS_ADF else "DF"))

    return SW_SUCCESS





