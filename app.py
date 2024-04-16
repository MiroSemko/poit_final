from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect
import MySQLdb       
import math
import time
import configparser as ConfigParser
import random
import math
import serial
from flask import jsonify

async_mode = None

app = Flask(__name__)


config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print(myhost)


app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 

data_switch = "Temperature" #or Humidity


#ser = serial.Serial('/dev/ttyUSB0', 9600)



def write2file(val):
    fo = open("static/files/graph.txt","a+")    
    # val = '[{"y": 0.6551787400492523, "x": 1, "t": 1522016547.531831}, {"y": 0.47491473008127605, "x": 2, "t": 1522016549.534749}, {"y": 0.7495528524284468, "x": 3, "t": 1522016551.537547}, {"y": 0.19625207463282368, "x": 4, "t": 1522016553.540447}, {"y": 0.3741884249440639, "x": 5, "t": 1522016555.543216}, {"y": 0.06684808042190538, "x": 6, "t": 1522016557.546104}, {"y": 0.17399442194131343, "x": 7, "t": 1522016559.54899}, {"y": 0.025055174467733865, "x": 8, "t": 1522016561.551384}]'
    fo.write("%s\r\n" %val)
    return "done"

def background_thread(args):
    count = 0  
    dataCounter = 0 
    dataList = []  
    start_time = time.time()
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)          
    while True:
        if args:
            A = dict(args).get('A')
            dbV = dict(args).get('db_value')
        else:
            A = 1
            dbV = 'nieco'  
        
        socketio.sleep(1)
        
        #nodemcu_data = ser.readline().decode('utf-8').strip().split();
        if(data_switch == "Temperature"):       
            nodemcu_data = ["Temperature", "25.00"]    #simulating sensor data
        elif(data_switch == "Humidity"):
            nodemcu_data = ["Humidity", "57.00"]
        
        if (nodemcu_data[0] == data_switch):
            sensor_data = nodemcu_data[1]
        else:
            continue
            
        
        
        
        
        print(dbV)
        if dbV == 'start':
            count += 1
            dataCounter +=1
            
            
            dataDict = {
                "start_time": start_time,
                "t": time.time(),
                "x": dataCounter,
                "sensor_data": sensor_data,
                "data_switch": data_switch
            }
            dataList.append(dataDict)
            
            socketio.emit('my_response',
                      {'sensor_data': str(sensor_data), 'count': count},
                      namespace='/test') 
        else:
            start_time = time.time()
            if len(dataList) > 0:
                print(str(dataList))
                fuj = str(dataList).replace("'", "\"")
                print(fuj)
                
                cursor = db.cursor()
                cursor.execute("SELECT MAX(id) FROM final")
                maxid = cursor.fetchone()
                max_id = maxid[0] + 1 if maxid[0] is not None else 1
                cursor.execute("INSERT INTO final (id, start_time, hodnoty, data_switch) VALUES (%s, %s,%s,%s)", (max_id, start_time, fuj,data_switch))
                db.commit()
                
                write2file(fuj)
                
            dataList = []
            dataCounter = 0
            count = 0
        
         
    #db.close()
    
    

    
    

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)
    
# @app.route('/db')
# def db():
  # db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  # cursor = db.cursor()
  # cursor.execute('''SELECT  hodnoty FROM  graph WHERE id=1''')
  # rv = cursor.fetchall()
  # return str(rv)    





def readmyfile(num):
    fo = open("static/files/graph.txt","r")
    rows = fo.readlines()
    return rows[int(num)-1]

@app.route('/dbdata/<string:num>', methods=['GET', 'POST'])
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  print(num)
  cursor.execute("SELECT hodnoty FROM  final WHERE id=%s", num)
  rv = cursor.fetchone()
  return str(rv[0])
  
@app.route('/filedata/<string:num>', methods=['GET', 'POST'])
def filedata(num):
  print(num)
  return str(readmyfile(num))
  
  


@app.route('/temperature_data', methods=['GET'])
def get_temperature_data():
    print("db")
    db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM final WHERE data_switch = 'Temperature'")
    rows = cursor.fetchall()
    temperature_data = []
    for row in rows:
        temperature_data.append({
            'id': row[0],
            'start_time': row[1],
            'hodnoty': row[2],
            'data_switch': row[3]
        })
    db.close()
    return jsonify(temperature_data)
    
@app.route('/temperature_data_file', methods=['GET'])
def get_temperature_data_file():
    print("file")

    try:
        with open("static/files/graph.txt", "r") as fo:
            rows = fo.readlines()
            temperature_data = []
            for index, row in enumerate(rows, start=1):
                row_data = row.strip()[1:-1].split(", ")  # Remove square brackets and split by ", "
                start_time = float(row_data[0].split(": ")[1])
                data_switch = row_data[-1].split(": ")[1].strip('"')
                if data_switch == 'Temperature"}':
                    temperature_data.append({
                        'id': index,
                        'start_time': start_time,
                        'hodnoty': "",
                        'data_switch': data_switch
                    })

        print(temperature_data)
        return jsonify(temperature_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/humidity_data', methods=['GET'])
def get_humidity_data():
    db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM final WHERE data_switch = 'Humidity'")
    rows = cursor.fetchall()
    temperature_data = []
    for row in rows:
        temperature_data.append({
            'id': row[0],
            'start_time': row[1],
            'hodnoty': row[2],
            'data_switch': row[3]
        })
    db.close()
    return jsonify(temperature_data)
    
@app.route('/humidity_data_file', methods=['GET'])
def get_humidity_data_file():

    try:
        with open("static/files/graph.txt", "r") as fo:
            rows = fo.readlines()
            temperature_data = []
            for index, row in enumerate(rows, start=1):
                row_data = row.strip()[1:-1].split(", ")  # Remove square brackets and split by ", "
                start_time = float(row_data[0].split(": ")[1])
                data_switch = row_data[-1].split(": ")[1].strip('"')
                if data_switch == 'Humidity"}':
                    temperature_data.append({
                        'id': index,
                        'start_time': start_time,
                        'hodnoty': "",
                        'data_switch': data_switch
                    })

        print(temperature_data)
        return jsonify(temperature_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


    
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['A'] = message['value']    
    #emit('my_response',
    #     {'data': message['value'], 'count': session['receive_count']})

@socketio.on('db_event', namespace='/test')
def db_message(message):   
    
    print("db event")
#    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['db_value'] = message['value']   
    print("aaaaa"+ message['value'])
#    emit('my_response',
#         {'data': message['value'], 'count': session['receive_count']})

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

#@socketio.on('connect', namespace='/test')
@socketio.on('initialize', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    #emit('my_response', {'data': 'Connected', 'count': 0})
   
# @app.route('/initialize', methods=['POST'])
# def initialize():
    # global thread
    # with thread_lock:
        # if thread is None:
            # thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    # return jsonify({'message': 'Initialization started'})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


@socketio.on('switch_data', namespace='/test')
def switch_data(message):
    global data_switch
    print(data_switch)
    data_switch = message['value']
    print(data_switch)
    


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)

















