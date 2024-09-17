import sqlite3 as sql
import os
import datetime as dt
import time as tm

PATH = os.path.dirname(__file__)
DATA = os.path.join(PATH, 'data')
DB = os.path.join(DATA, 'data.db')

MAX_TEMPORARY_USE_TIME = 5 # maximum seconds for temporary use of a seat

SEAT_CONDITIONS = {
    3: '空位',
    4: '预约使用中',
    5: '预约未使用',
    6: '临时使用中'
}
SEAT_STATUS = {
    0: 'empty',
    1: 'sitting',
    2: 'occupied'
}


seats = [1, 2]

# record seat reservation
# - key: seat id
# - value: whether the seat is reserved
seat_reservation = {one: False for one in seats}

# record seats usage
# - key: seat id
# - value: [0] seat condition, [1] start time of using the seat
seats_usageRecord = {one: [None, None] for one in seats}

# record seat warnings
# - key: seat id
# - value: whether there is a warning
seats_warning = {one: False for one in seats}

def __check_db() -> int:
    """
    check if the database exists

    :return: database not exists: 0, database exists and correct: 1, database exists but incorrect: -1
    """
    if not os.path.exists(DATA):
        os.makedirs(DATA)
    if os.path.exists(DB): # if the database already exists
        # check database format
        expected_structure = {
            'log_id': 'INTEGER',
            'timestamp': 'INTEGER',
            'id': 'INTEGER',
            'status': 'INTEGER',
            'reservation': 'BOOLEAN'
        }

        conn = sql.connect(DB)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='seat_logs';")
        table_exists = cursor.fetchone()
        if not table_exists:
            conn.close()
            print("[ ERROR ] Table 'seat_logs' does not exist.")
            return 2

        # 检查表结构
        cursor.execute("PRAGMA table_info(seat_logs);")
        columns = cursor.fetchall()
        conn.close()

        actual_structure = {column[1]: column[2] for column in columns}

        for column_name, column_type in expected_structure.items():
            if column_name not in actual_structure:
                print(f"[ ERROR ] Column '{column_name}' does not exist in table 'seat_logs'.")
                return 2
            if actual_structure[column_name] != column_type:
                print(f"[ ERROR ] Column '{column_name}' has type '{actual_structure[column_name]}', expected '{column_type}'.")
                return 2

        return 1
    else:
        return 0


def get_seatCondition_code(seat_status: int, seat_reserved: bool) -> str:
    """
    get the information of the seat condition

    :param seat_condition: condition of the seat
    :param reserved: whether the seat is reserved
    :return: condition code of the seat condition
    """
    if seat_reserved:
        if seat_status == 0:
            return 5 # 预约未使用
        else:
            return 4 # 预约使用中
    else:
        if seat_status == 0:
            return 3 # 空位
        else:
            return 6 # 临时使用中

def get_seatWarnings() -> dict:
    """
    refresh all warning info and return the dict

    :param seat_id: id of the seat
    :return: True if there is a warning, False otherwise
    """
    for seat_id in seats:
        # if seat reservation is changed, change seat_usgaeRecord
        if is_reserved(seat_id): # reserved: 6 -> 4, 3 -> 5
            if seats_usageRecord[seat_id][0] == 6:
                seats_usageRecord[seat_id][0] = 4
            elif seats_usageRecord[seat_id][0] == 3:
                seats_usageRecord[seat_id][0] = 5
                seats_usageRecord[seat_id][1] = None
        else: # not reserved: 4 -> 6, 5 -> 3
            if seats_usageRecord[seat_id][0] == 4:
                seats_usageRecord[seat_id][0] = 6
                seats_usageRecord[seat_id][1] = tm.time()
            elif seats_usageRecord[seat_id][0] == 5:
                seats_usageRecord[seat_id][0] = 3
                seats_usageRecord[seat_id][1] = None


        if seats_usageRecord[seat_id][0] == 6:
            if tm.time() - seats_usageRecord[seat_id][1] > MAX_TEMPORARY_USE_TIME:
                seats_warning[seat_id] = True
            else:
                seats_warning[seat_id] = False
        else:
            seats_warning[seat_id] = False

    return seats_warning

def is_reserved(seat_id: int) -> bool:
    """
    check if a seat is reserved

    :param seat_id: id of the seat
    :return: True if the seat is reserved, False otherwise
    """
    return seat_reservation[seat_id]


def init_db():
    """
    initialize the database
    """
    db_state = __check_db()
    if db_state == 1:
        return # database is correct, no need to initialize
    elif db_state == 2:
        exit(1)
        
    conn = sql.connect(DB)
    cursor = conn.cursor()

    # seat logs table
    # - timestamp: timestamp of the log
    # - id: id of the seat
    # - status: info from device (0 empty, 1 sitting, 2 occupied)
    # - reservation: whether the seat is reserved
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seat_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER NOT NULL,
        id INTEGER NOT NULL,
        status INTEGER NOT NULL,
        reservation BOOLEAN NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

def read_seat_logs() -> tuple:
    """
    read all seat logs from the seat_logs table

    :return: tuple of seat logs
    (timestamp, seat_id, status, reservation, seat_condition_info)
    """
    if not os.path.exists(DB):
        print('Database does not exist. Please create it first.')
        return []

    conn = sql.connect(DB)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM seat_logs')
    logs = cursor.fetchall()

    conn.close()

    logs = ((log[1], log[2], log[3], log[4], get_seatCondition_code(log[3], log[4])) for log in logs)

    return logs

def add_seat_log(seat_id: int, seat_status: str):
    """
    add a new log to the seat_logs table

    :param seat_id: id of the seat
    :param status: status of the seat (0 empty, 1 sitting, 2 occupied)
    """
    if not os.path.exists(DB):
        print('Database does not exist. Please create it first.')
        return

    timestamp = tm.time()

    conn = sql.connect(DB)
    cursor = conn.cursor()

    cursor.execute('INSERT INTO seat_logs (timestamp, id, status, reservation) VALUES (?, ?, ?, ?)',
                   (timestamp, seat_id, seat_status, is_reserved(seat_id)))

    conn.commit()
    conn.close()

def seat_reserve(seat_id: int, reserve: bool):
    """
    reserve a seat or cancel a reservation

    :param seat_id: id of the seat
    :param reserve: True to reserve the seat, False to cancel the reservation
    """

    seat_reservation[seat_id] = reserve

def seat_use(seat_id: int, seat_status: int):
    """
    record the usage of a seat. If the seat is occupied for too long, set the warning info to `seats_warning`

    :param seat_id: id of the seat
    :param seat_status: status of the seat (0 empty, 1 sitting, 2 occupied)
    """
    seat_condition = get_seatCondition_code(seat_status, is_reserved(seat_id))
    # empty(3) and reserved-but-not-using(5): record condition code but not record the time
    # reserved-using(4) and temporary-using(6): record
    # if temporary-using is recorded, check if the time exceeds the maximum time
    if seat_condition == 3 or seat_condition == 5: # empty or reserved-but-not-using
        seats_usageRecord[seat_id][0] = seat_condition
        seats_usageRecord[seat_id][1] = None
    else:
        if seats_usageRecord[seat_id][0] != seat_condition: # condition changed
            seats_usageRecord[seat_id][0] = seat_condition
            seats_usageRecord[seat_id][1] = tm.time()
    get_seatWarnings()


def recieve_data(seat_id: int, seat_status: int):
    """
    recieve data from the device
    
    :param seat_id: id of the seat
    :param seat_status: status of the seat (0 empty, 1 sitting, 2 occupied)
    """
    add_seat_log(seat_id, seat_status)
    seat_use(seat_id, seat_status)


def __show_info():
    """
    show the information of the seats
    """
    get_seatWarnings()
    print('Seat Information:')
    for seat_id in seats:
        print(f' Seat {seat_id}:')
        print(f'   Reservation: {is_reserved(seat_id)}')
        print(f'   Condition: {SEAT_CONDITIONS[seats_usageRecord[seat_id][0]] if seats_usageRecord[seat_id][0] else None}')
        print(f'   Time: {tm.time() - seats_usageRecord[seat_id][1] if seats_usageRecord[seat_id][1] else None} s')
        print(f'   Warning: {seats_warning[seat_id]}')

    print('\nSeat Logs:')
    for log in read_seat_logs():
        print(f" time: {log[1]}, seat_id: {log[2]}, status: {SEAT_STATUS[log[3]]}, reservation: {log[4]}, condition: {SEAT_CONDITIONS[log[4]]}")

def second_format(seconds: int) -> str:
    """
    format seconds to "xx s" or "xx min"

    :param seconds: seconds
    :return: formatted string
    """
    if seconds < 60:
        return f"{seconds} s"
    else:
        return f"{seconds // 60} min"


if __name__ == '__main__':
    init_db()
    seat_reserve(1, False)
    recieve_data(1, 2)
    tm.sleep(3)
    recieve_data(1, 2)

    __show_info()
