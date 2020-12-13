import os
import numpy as np
import pandas as pd
import random
import gym
from gym import spaces
import time
from threading import Timer
from PyQt5.QtWidgets import *

import sys
from kiwoom import Kiwoom

ACTION_SKIP = 0
ACTION_BUY = 1
ACTION_SELL = 2
eps = 1e-7

class c_Account:
  def __init__(self, balance):
    self.balance = balance
  
  def withdraw(self, money):
    if self.balance < money:
      return False
    
    else:
      self.balance -= money
      return True
  
  def deposit(self, money):
    self.balance += money
    return True

  def show_balance(self):
    return self.balance

  def get_balance(self, new_balance):
    self.balance = new_balance


def search(dirname):
  filenames = os.listdir(dirname)
  stockdata_list = []
  for filename in filenames:
      full_filename = os.path.join(dirname, filename)
      stockdata_list.append(full_filename)
    
  return stockdata_list
        

class c_StockMarketEnv(gym.Env): 
    def __init__(self, istest=False, kiwoom_linked=False, stock_code=None, num=10, delta=10000):
      self.kiwoom_linked = kiwoom_linked
      self.num = num
      self.timer_end = False

      if not kiwoom_linked:  
        path = "C:/Users/yewon/Documents/traderWon/test_stock_data" if istest else "C:/Users/yewon/Documents/traderWon/stock_data"
        super(c_StockMarketEnv, self).__init__()
        self.istest= istest
        
        self.state = None
        self.commision = 0.994
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=-1000, high=1000, shape=(2,)) # Price, Tarding Volume.
        self.reward_range = (-300, 300) # only applied to Korean market 
        self.purchased = False
        self.purchased_price = 0
        self.reward_list = []

        # the account balance will later be replced with the real value.
        self.account = c_Account(10000000)
        self.companies = search(path)
        self.index = 0
        self.df = None
        self.buy_num = 0

        if len(self.companies) == 0:
          raise NameError('Invalid empty directory {}'.format(path))
        
        self.reset()
      
      else:
        self.state = None
        self.kiwoom_linked = kiwoom_linked
        self.stock_code = stock_code
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=-1000, high=1000, shape=(2,)) # Price, Tarding Volume.
        self.purchased = False
        self.state = None
        self.commision = 0.997313064
        self.reward_list = []
        self.delta = delta
        self.current_time = time.localtime()
        self.kiwoom_init()
        self.set_time()
        

    def set_time(self):
      if self.timer_end:
        self.current_time = time.localtime()
      else:
        self.current_time=time.localtime()
        timer = Timer(1, self.set_time)
        timer.start()

    def seed(self, seed=None):
      pass
    
    # -----------------------------------------------------------------------------------------------------------------------
    # order type lookup = {'신규매수': 1, '신규매도': 2, '매수취소': 3, '매도취소': 4}
    # hoga lookup = {'지정가': "00", '시장가': "03"}
    def sell(self):
      if self.purchased:
        self.kiwoom.send_order("시장가매도", "101", self.kiwoom.accno, 2, self.stock_code, self.num, 0, "03", "")
        self.purchased = False

    def buy(self):
      if not self.purchased:
        self.kiwoom.send_order("시장가매수", "101", self.kiwoom.accno, 1, self.stock_code, self.num, 0, "03", "")
        self.purchased = True
    # -----------------------------------------------------------------------------------------------------------------------

    def kiwoom_init(self):
      self.kiwoom = Kiwoom()
      self.kiwoom.comm_connect()
    
  
    def step(self, action):
      assert self.action_space.contains(action)
      
      if self.kiwoom_linked:       
        time.sleep(59.8)        #장 시작 후에는 1분을 대기하고 데이터를 조회한다
        self.state = self.next()
        reward = 0
        observation = np.array([[self.state[0], self.state[1]]]).reshape((1, 2, 1))

        finished = self.state[3]
        info = {}
        info["price"] = self.state[2]
        
        if finished and self.purchased:
          cost = self.kiwoom.purchased_price
          self.sell()
          reward = ((self.kiwoom.purchased_price * self.commision / (cost + eps)) - 1) * 100
        
        if (not finished) and (action == ACTION_BUY) and (not self.purchased) and (abs(self.kiwoom.balance - info["price"] * self.num) > self.delta):
          self.buy() # 돈이 부족하지 않으면 산다.
          self.kiwoom.get_balance()

        elif (not finished) and (action == ACTION_SELL) and self.purchased:
          cost = self.kiwoom.purchased_price
          self.sell()
          self.kiwoom.get_balance()
          reward = ((self.kiwoom.purchased_price * self.commision / (cost + eps)) - 1) * 100
        
        return observation, reward, finished, info

      else:
          self.state = self.next(self.df)  # (price_percentage, volume_percentage, price, finished)
        
          reward = 0
          observation = np.array([[self.state[0], self.state[1]]]).reshape((1, 2, 1))
        
          finished = self.state[3]
          info = {}
          info["price"] = self.state[2]
          
          if finished and (info["price"] != 0):
            if self.purchased:
              reward = ((info["price"] * self.commision / (self.purchased_price + eps)) - 1) * 1000
              self.purchased = False
            print(self.buy_num)

            return observation, reward, finished, info 

          if (action == ACTION_BUY) and (not self.purchased):
            if (self.account.withdraw(info["price"])):
              self.purchased = True
              self.buy_num += 1
              self.purchased_price = info["price"]

          elif (action == ACTION_SELL) and self.purchased:
            if self.account.deposit(info["price"]):
              self.purchased = False
              reward = ((info["price"] * self.commision/ (self.purchased_price + eps)) - 1) * 1000 #reward corresponds to the revenue ratio
              self.reward_list.append(reward)

          return observation, reward, finished, info 

    def get_data(self, train=True):
      if train:
        data = random.choice(self.companies)
        return pd.read_csv(data)
        
      else:
        pass

    def _get_changed_volume(self):
      time.sleep(60)
      self.kiwoom.set_input_value("종목코드", self.stock_code)
      self.kiwoom.set_screen_no()
      self.kiwoom.comm_rq_data("현재가조회", "opt10003", "0", str(self.kiwoom.screen_no))

    def set_opening_data(self):
      self.kiwoom.set_input_value("종목코드", self.stock_code)
      self.kiwoom.set_input_value("당일전일", "1")
      self.kiwoom.set_input_value("틱분", "1")
      self.kiwoom.set_input_value("시간", "0900")
      self.kiwoom.set_screen_no()
      self.kiwoom.comm_rq_data("시가조회", "opt10084", "0", str(self.kiwoom.screen_no))

    def next(self, df=None):
      if self.kiwoom_linked:
        if not self.kiwoom.set_first_data:
          self.set_opening_data()
          
          # 9시에 시작하는 경우
          if self.current_time.tm_hour == 9 and self.current_time.tm_min == 0:
            self.kiwoom.current_price = self.kiwoom.opening_price
            self.kiwoom.current_volume = self.kiwoom.opening_volume

          # 9시에 시작하지 않는 경우
          else:
            self.kiwoom.set_input_value("종목코드", self.stock_code)
            self.kiwoom.set_screen_no()
            self.kiwoom.comm_rq_data("현재가조회", "opt10003", "0", str(self.kiwoom.screen_no))
        
            while(self.kiwoom.current_volume == self.kiwoom.minbefore_volume):
              self._get_changed_volume()
          #-----------------------시초가에는 이전데이터가 없기에 시초가와 동일하게 설정--------
          self.kiwoom.set_past_data(self.kiwoom.current_price, self.kiwoom.current_volume)
          self.kiwoom.set_first_data = True

        else:
          self.kiwoom.set_input_value("종목코드", self.stock_code)
          self.kiwoom.set_screen_no()
          self.kiwoom.comm_rq_data("현재가조회", "opt10003", "0", str(self.kiwoom.screen_no))
        
          while(self.kiwoom.current_volume == self.kiwoom.minbefore_volume):
            self._get_changed_volume()
            if ((self.current_time.tm_hour == 15) and (self.current_time.tm_min >= 19)) or ((self.current_time.tm_hour > 15) or (self.current_time.tm_hour < 8)):
              break
            
          self.kiwoom.set_past_data(self.kiwoom.current_price, self.kiwoom.current_volume)
        
        price_per = (1 - self.kiwoom.current_price / self.kiwoom.opening_price) * 100
        volume_per = (1 - self.kiwoom.current_volume / self.kiwoom.opening_volume) * 100
        finished = False
        
        if ((self.current_time.tm_hour == 15) and (self.current_time.tm_min >= 19)) or ((self.current_time.tm_hour > 15) or (self.current_time.tm_hour < 8)):
          finished = True 
        
        return (price_per, volume_per, self.kiwoom.current_price, finished)

      else:
        finished = False
        if self.index == (len(df) - 1):
          finished = True
      
        elif self.index > (len(df) - 1):
          finished = True
          return (0, 0, 0, finished)
      
        price_percentage = (1 - df.iloc[self.index]["체결가"] / df.iloc[0]["체결가"]) * 100
        volume_percentage = (1 - df.iloc[self.index]["거래량"] / df.iloc[0]["거래량"]) * 100
        price = df.iloc[self.index]["체결가"]

        self.index += 1

        return (price_percentage, volume_percentage, price, finished)

# ---------------------------Not Used In Kiwoom Based Env-----------------------------------
    def reset(self):   
      if self.kiwoom_linked:
        ...
      
      else:
        self.index = 0
        self.purchased = False
        self.purchased_price = 0
        self.df = self.get_data()
        self.buy_num = 0
        self.account.get_balance(10000000)

    def render(self, mode='human', close=False):
        return self.reward_list


if __name__ == "__main__":
  app = QApplication(sys.argv) #stockmarket instance를 생성하기전 외부에서 호출해야함.
  a = c_StockMarketEnv(kiwoom_linked=True, stock_code="010140")
  st = a.next()
  # a.purchased = True
  print(st)
  for i in range(100):
    a.kiwoom.get_balance()
    time.sleep(1)
    
  a.timer_end = True

    
