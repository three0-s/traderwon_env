import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import time
import pandas as pd
import sqlite3

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.balance = 0
        self.purchased_price = 0
        self.screen_no = 0

        self.opening_price = 0
        self.opening_volume = 0
        self.set_first_data = False

        self.current_price = 0
        self.current_volume = 0

        self.minbefore_price = 0
        self.minbefore_volume = 0
       
        self.rapidly_increased = []

        self.prev_state = 0
        self.current_time = None

        self._create_kiwoom_instance()
        self._set_signal_slots()
    """    
    def set_timer(self):
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.time_event_loop = QEventLoop()
        self.time_event_loop.exec_()
    """

    def get_current_data(self):
        return (self.current_price, self.current_volume)
    
    
    def set_past_data(self, past_price, past_volume):
        self.minbefore_price = past_price
        self.minbefore_volume = past_volume


    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveChejanData.connect(self._receive_chejan_data)
        self.OnReceiveMsg.connect(self.get_error_message)
        # self.timer.timeout.connect(self.timeout)
        # self.OnReceiveRealData.connect(self._receive_real_data)
    """
    def timeout(self):
        self.time_event_loop.exit()
        self.current_time = time.localtime()
        state = self.GetConnectState()
        
        if state == 1:
            state_msg = "Server Connected!"
        else:
            state_msg = "Server Not Connected!"

        if not state == self.prev_state:
            print(state_msg)
        self.prev_state = state
    """
    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no):
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                     [rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no])
        self.order_event_loop = QEventLoop()
        self.order_event_loop.exec_()
    """
    # 실시간 데이터 수신
    def _receive_real_data(self, stockcode, realtype, data):
        # assuming that the user requests only 현재가 and 누적거래량 
        # Returns: (price, volume) tuple
        self.real_data = self._get_comm_real_data(stockcode)
    """
    def disconnect(self, screen_no):
        self.dynamicCall("DisconnectRealData(QString)", screen_no)

    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    """
    def _get_comm_real_data(self, stockcode):
        price = self.dynamicCall("GetCommRealData(QString, int)", stockcode, 10)
        volume = self.dynamicCall("GetCommRealData(QString, int)", stockcode, 13)
        
        return (price, volume)
    """
    def set_screen_no(self):
        if (self.screen_no + 1) > 199:
            self.screen_no -= 199
        else:
            self.screen_no += 1
        
    def _event_connect(self, err_code):
        if err_code == 0:
            print("connected")
            self.set_accno()

        else:
            print("disconnected")

        self.login_event_loop.exit()
    
    def get_balance(self):
        print("잔고조회 요청")
        self.set_input_value("계좌번호", self.accno)
        self.set_input_value("비밀번호", "0000")
        self.set_input_value("비밀번호입력매체구분", "00")
        self.set_input_value("조회구분", "3")
        self.set_screen_no()
        
        self.comm_rq_data("잔고조회", "opw00001", "0", str(self.screen_no))

    def rapid_vol_increase(self):
        self.set_input_value("시장구분", "101")       #101 -> 코스닥
        self.set_input_value("정렬구분", "1")         #2 -> 급증률기준 정렬, 1-> 급증량기준 정렬
        self.set_input_value("시간구분", "1")
        self.set_input_value("거래량구분", "500")     #500-> 50만주 이상 거래량
        self.set_input_value("시간", "1")
        self.set_input_value("종목조건", "6")         #증100
        self.set_input_value("가격구분", "8")         #1000원 이상

        self.set_screen_no()
        self.comm_rq_data("거래량급증", "OPT10023", "0", str(self.screen_no))

    def set_accno(self):
        self.accno = self.dynamicCall("GetLoginInfo(QString)", ["ACCNO"]).split(';')[1]
        print(self.accno)

    def get_chejan_data(self, fid):
        ret = self.dynamicCall("GetChejanData(int)", fid)
        return ret

    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
        if gubun == "0" :
            price_str = self.get_chejan_data(910)
            if not price_str == '' :
                self.purchased_price = abs(int(price_str)) 
            else:
                self.purchased_price = -1               # 주문가격
        
            print("주문번호", self.get_chejan_data(9203)) #	주문번호
            print("종목명", self.get_chejan_data(302))  # 종목명
            print("주문수량", self.get_chejan_data(900))  # 주문수량
            print("주문가격", self.purchased_price)  # 주문가격
            
        else:
            try:
                self.order_event_loop.exit()
            except AttributeError:
                ...

    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = code_list.split(';')
        return code_list[:-1]


    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name


    def get_connect_state(self):
        ret = self.dynamicCall("GetConnectState()")
        return ret


    def set_input_value(self, id_, value):
        self.dynamicCall("SetInputValue(QString, QString)", id_, value)


    def comm_rq_data(self, rqname, trcode, next_, screen_no):
        print("[commrq_return]",self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next_, screen_no))
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

   
    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code,
                               real_type, field_name, index, item_name)
        return ret.strip()

    def _get_comm_data(self, trcode, rqname, index, data_name):
        ret = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode,
                               rqname, index, data_name)
        return ret.strip()

    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    def get_error_message(self, screen_no, rqname, trcode, msg):
        print(rqname, "]", msg)

    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        now = time.localtime()

        if next == '2':
            self.remained_data = True
        else:
            self.remained_data = False

        if rqname == "opt10081_req":
            self._opt10081(rqname, trcode)
        """
        elif rqname == "opt10004_req":
            self._opt10004(rqname, trcode)
        """
        if rqname == "시장가매수":
            print(now.tm_hour, "h", now.tm_min, "m 시장가매수 주문 들어옴")
            order_no = self._get_comm_data(trcode, rqname, 0, "주문번호")
            if order_no == "":
                print("매수 주문실패")
                self.order_event_loop.exit()
            
            else:
                print("매수 주문들어감")

        if rqname == "시장가매도":
            print(now.tm_hour, "h", now.tm_min, "m 시장가매도 주문 들어옴")
            order_no = self._get_comm_data(trcode, rqname, 0, "주문번호")
            if order_no == "":
                print("매도 주문실패")
                self.order_event_loop.exit()
            
            else:
                print("매도 주문들어감")
        
        if rqname == "현재가조회":
            # print("현재가 조회 요청이 OnReceiveTRData로 들어옴")
            self.current_price = abs(int(self._get_comm_data(trcode, rqname, 0, "현재가")))
            self.current_volume = abs(int(self._get_comm_data(trcode, rqname, 0, "누적거래량")))
            
            print(now.tm_hour, "h", now.tm_min, "m 현재가:", self.current_price)
            print(now.tm_hour, "h", now.tm_min, "m 현재 거래량:", self.current_volume)
            
            if self.current_price==(None or 0):
                print("주말엔 안해요;)")
            self.disconnect(str(self.screen_no))
            
        if rqname =="잔고조회":
            self.balance = abs(int(self._get_comm_data(trcode, rqname, 0, "d+2추정예수금")))
            print("현재잔고:", self.balance)


        if rqname =="시가조회":
            print("시가조회함.")
            self.opening_price = abs(int(self._get_comm_data(trcode, rqname, 0, "현재가")))
            self.opening_volume = abs(int(self._get_comm_data(trcode, rqname, 0, "누적거래량")))
            print("시가", self.opening_price)
            print("시초거래량", self.opening_volume)
            self.disconnect(str(self.screen_no))

        if rqname=="거래량급증":
            increased_list = []
            increase_ratio_list = []
            code_list = []

            for i in range(30):
                name = self._get_comm_data(trcode, rqname, i, "종목명")
                code = self._get_comm_data(trcode, rqname, i, "종목코드")
                increase_ratio = self._get_comm_data(trcode, rqname, i, "급증률")
                price_ratio = self._get_comm_data(trcode, rqname, i, "등락률")

                if name == '' or code  == '' or name==' ' or code == " " or increase_ratio == '' or increase_ratio == ' ' or price_ratio == '' or price_ratio ==' ':
                    increase_ratio_list.append(0)
                    increased_list.append("조건 미충족")
                    code_list.append("조건 미충족")
                    break

                increase_ratio = float(increase_ratio)
                price_ratio = float(price_ratio)
                if ("KODEX" in name) or ("ETN" in name) or ("ELW" in name) or ("K-OTC" in name) or ("선물" in name) or (price_ratio < 0):
                    continue
                else:
                    increased_list.append(name)
                    increase_ratio_list.append(increase_ratio)
                    code_list.append(code)
            self.rapidly_increased = list(zip(increased_list, code_list, increase_ratio_list))
            self.disconnect(str(self.screen_no))
        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass
    
    """
    def _opt10004(Self, rqname, trcode):
        stock_price = self._get_comm_data(trcode, rqname, 0, "매도최우선호가")
        return stock_price
    """
        

    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname)

        for i in range(data_cnt):
            date = self._comm_get_data(trcode, "", rqname, i, "일자")
            open = self._comm_get_data(trcode, "", rqname, i, "시가")
            high = self._comm_get_data(trcode, "", rqname, i, "고가")
            low = self._comm_get_data(trcode, "", rqname, i, "저가")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.ohlcv['date'].append(date)
            self.ohlcv['open'].append(int(open))
            self.ohlcv['high'].append(int(high))
            self.ohlcv['low'].append(int(low))
            self.ohlcv['close'].append(int(close))
            self.ohlcv['volume'].append(int(volume))