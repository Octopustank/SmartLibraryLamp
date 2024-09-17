from flask import Flask, redirect, request, render_template
import sqlite3 as sql
import os
import datetime as dt
import time as tm

import timeView
import utils

PATH = os.path.dirname(__file__)

LIBRARY_IP = "110.242.68.66" # for example
IP_VIEW = timeView.IP_VIEW() # store ip_view objects

app = Flask(__name__)

@app.route('/')
def root():
    return redirect('/index')

@app.route('/index', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/dataAPI', methods=['GET'])
def data():
    seat_id = int(request.args.get('seat_id'))
    seat_status = int(request.args.get('seat_status'))
    utils.recieve_data(seat_id, seat_status)

    season = timeView.get_ChinaSeason()
    cal_res = IP_VIEW.refresh(LIBRARY_IP, season) # 进行计算
    if cal_res == None: # 计算失败
        print(f"[Warning] Faild to get addr: {LIBRARY_IP}. Use default condition instead")
        light = "noon" # 使用默认情况
    else:
        light = cal_res[1] # 获取光亮情况

    return {'light': not light, 'reserved': utils.is_reserved(seat_id)}

@app.route('/reserveAPI', methods=['GET'])
def reserve():
    seat_id = int(request.args.get('seat_id'))
    reserve = True if request.args.get('reserve') == '1' else False
    utils.seat_reserve(seat_id, reserve)
    return f"Seat {seat_id} {'reserved' if reserve else 'cancelled'}"

@app.route('/monitor', methods=['GET'])
def monitor():
    utils.get_seatWarnings()
    seat_conditions = []
    for seat_id in utils.seats:
        seat_conditions.append([seat_id,
                                utils.is_reserved(seat_id),

                                # '空位', '预约使用中', '预约未使用', '临时使用中', '无数据'
                                utils.SEAT_CONDITIONS[utils.seats_usageRecord[seat_id][0]] if utils.seats_usageRecord[seat_id][0] else "无数据",
                                 
                                utils.second_format(int(tm.time() - utils.seats_usageRecord[seat_id][1])) if utils.seats_usageRecord[seat_id][1] else "无数据",
                                 
                                "临时使用超时" if utils.seats_warning[seat_id] else "正常"
                                 ])
    seat_logs = []
    for log in utils.read_seat_logs():
        seat_logs.append([dt.datetime.fromtimestamp(log[0]), # time
                          log[1], # seat_id
                          utils.SEAT_STATUS[log[2]], # seat status
                          log[3], # seat reservation
                          utils.SEAT_CONDITIONS[log[4]] # seat condition
                          ])
        
    season = timeView.get_ChinaSeason()
    cal_res = IP_VIEW.refresh(LIBRARY_IP, season) # 进行计算
    if cal_res == None: # 计算失败
        print(f"[Warning] Faild to get addr: {LIBRARY_IP}. Use default condition instead")
        view = "Main_noon_bg_summer.png" # 使用默认情况
    else:
        view = cal_res[0]
    return render_template('monitor.html', seat_logs=seat_logs, seat_conditions=seat_conditions, view_cover=view)

@app.route('/reserve', methods=['GET'])
def reserve_page():
    seats_status = utils.seat_reservation.items()
    print(seats_status)
    return render_template('reserve.html', seats=seats_status)

if __name__ == '__main__':
    utils.init_db()
    timeView.init()
    app.run('0.0.0.0', port=1145, debug=True)
