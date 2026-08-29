import struct
import can  # python-can library

# --- CONSTANTS (match your firmware) ---
BASE_CAN_ID   = 0xB000  # replace with your actual BASE_CAN_ID
TOTAL_AD68    = 2
TOTAL_CELL    = 14      # replace with your actual cells per IC
CHARGER_CONFIG_CAN_ID = 0x1806E5F4  # replace with your actual ID

# --- ID BOUNDARIES ---
# Per-cell messages:    BASE_CAN_ID + 0  to BASE_CAN_ID + (TOTAL_AD68 * TOTAL_CELL - 1)
# Pack voltage/current: BASE_CAN_ID + 7*TOTAL_CELL + 7
# AD29 status:          BASE_CAN_ID + 7*TOTAL_CELL + 7 + 1
# IC status messages:   BASE_CAN_ID + 7*TOTAL_CELL + ic  (for ic in 0..TOTAL_AD68-1)

IC_STATUS_BASE   = BASE_CAN_ID + TOTAL_AD68 * TOTAL_CELL
# AD29_STATUS_ID   = BASE_CAN_ID + 7 * TOTAL_CELL + 7 + 1

def decode_cell_message(can_id, data):
    """
    CAN ID: BASE_CAN_ID + ic * TOTAL_CELL + c
    Bytes 0-1: cell voltage (int16, x1000 -> V)
    Bytes 2-3: voltage diff (int16, x1000 -> V)
    Bytes 4-5: cell temp    (int16, x100  -> degC)
    Byte  6:   flags        (bit0=isDischarging, bit1=isCellFault)
    """
    (cell_voltage, voltage_diff, cell_temp, flags) = struct.unpack_from('<hhhB', data, 0)

    offset = can_id - BASE_CAN_ID
    ic = offset // TOTAL_CELL
    c  = offset %  TOTAL_CELL


    return {
        'type':           'cell',
        'ic':             ic,
        'cell':           c,
        'voltage_V':      cell_voltage / 1000.0,
        'voltage_diff_V': voltage_diff / 1000.0,
        'temp_C':         cell_temp    / 100.0,
        'is_discharging': bool(flags & 0x01),
        'cell_fault':     bool(flags & 0x02),
    }


def decode_ic_message(can_id, data):
    """
    CAN ID: BASE_CAN_ID + TOTAL_CELL + ic
    Bytes 0-3: segment voltage (int32, x1000 -> V)
    Bytes 4-5: IC temperature  (int16, x100  -> degC)
    Byte  6:   flags           (bit0=CommsError, bit1=FaultDetected)
    """
    (v_segment, temp_ic, flags) = struct.unpack_from('<fhB', data, 0)

    ic = can_id - IC_STATUS_BASE

    return {
        'type':         'ic_status',
        'ic':           ic,
        'v_segment_V':  v_segment,
        'temp_C':       temp_ic   / 100.0,
        'comms_error':  bool(flags & 0x01),
        'fault':        bool(flags & 0x02),
    }

def decode_ad29_status_message(data):
    """
    CAN ID: BASE_CAN_ID + 7*TOTAL_CELL + 7 + 1
    Byte 0: flags (bit0=CommsError, bit1=FaultDetected)
    """
    flags = data[0]

    return {
        'type':        'ad29_status',
        'comms_error': bool(flags & 0x01),
        'fault':       bool(flags & 0x02),
    }


def decode_message(can_id, data):
    # can_id = msg.arbitration_id
    # data   = msg.data

    # AD29 status (Don't have any)
    # if can_id == AD29_STATUS_ID:
        # return decode_ad29_status_message(data)

    # Charger config
    if can_id == CHARGER_CONFIG_CAN_ID:
        return {'type': 'charger_config', 'raw': list(data)}

    # IC messages
    if IC_STATUS_BASE <= can_id < IC_STATUS_BASE + TOTAL_AD68:
        return decode_ic_message(can_id, data)

    # Cell messages
    cell_id_max = BASE_CAN_ID + TOTAL_AD68 * TOTAL_CELL
    if BASE_CAN_ID <= can_id < cell_id_max:
        return decode_cell_message(can_id, data)

    return {'type': 'unknown', 'id': hex(can_id), 'raw': list(data)}

'''
# --- MAIN LOOP ---
if __name__ == '__main__':
    # Adjust interface/channel to your CAN adapter (e.g. 'socketcan', 'pcan', 'kvaser')
    bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)

    print("Listening on CAN bus...")
    for msg in bus:
        decoded = decode_message(msg)
        print(decoded)
'''

if __name__ == '__main__':
    print(decode_message(0xB01C, bytes([0xA9, 0xA4, 0xAE, 0x41, 0x00, 0x00, 0x00, 0x00])))
    
    print(decode_message(0xB000, bytes([0x1D, 0x06, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00])))