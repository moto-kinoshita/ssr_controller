
import sys, queue
import re
import time

from threading import Thread
import RPi.GPIO as GPIO

"""
    SSR制御クラス

    設定温度：target_temp
    出力ピン：pin_num
    温度取得キュー：tc_readers_dict

"""

MAX_PWM_WIDTH = 10

class SsrDriver(Thread):
    def __init__(self, target_pin, tc_readers_dict, target_temp=20):
        Thread.__init__(self)
        self.pin_num = target_pin["pin_num"]  #これはなんですか?
        print(f"init SSR PIN({self.pin_num})")

        # 設定
        self.tc_index = target_pin["tc_index"]   #これはなんですか?   
        self.target_temp = target_temp
        self.kp = 0.1
        """
        Kメモ{210103}
        ここ（def __init__ ）はあくまで、デフォルトのパラメータを決めていると言う位置づけで
        本当に制限をやっているのは、あるいはやるべきなのは、現場に1番近いところ。
        したがって、デフォルトのパラメータを、現場のプログラムに渡してあげると言う立ち位置になる。
        現場が無茶をやっても、ここで安全性を見てあげると言うような立場なのかもしれない。
        （試行錯誤でプログラムの構造を考えてみる。）
        """
        self.tc_readers_dict = tc_readers_dict

        self.running = True     # 外部からスレッドを止める用フラグ

        self.d_temp = None      # 温度差（将来PID制御用）

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_num, GPIO.OUT)
        time.sleep(0.1)
        GPIO.output(self.pin_num, False)
        time.sleep(0.1)


    def run(self):

        time.sleep(0.2)
        print(f"start SSR PIN({self.pin_num})")  # 変数名が未定義だったので直したK{210103}
  
        while self.running:

            try:
                """
                このプログラム1が1番、コントロールの現場に近いところで、本来あらゆる温度の情報とSSRの操作ができる
                作業フィールドになっているべき。今そうなっているかどうか、よくわからないけど。。。。。
                self.tc_readers_dict[input_port[0]].get_tc_now(input_port[1])　
                """
                list_tc_temp = []
                # キューから温度を取得
                """
                K210104, ジェイソンの使い方、ジェイソンからデータとってくるところをきれいにわかるようにしないといけない
                （変数の説明）：
                 input_port= config.json の終端 
                            ['/dev/ttyUSB0', 2]　＝［Tc収録機のUARTの番号、「熱電対Tcの番号」］
                            input_port[1]は「熱電対Tcの番号」
                 get_tc_now = temperatures[idx] すなわち、吉澤さんのTc収録機から読み込んだcsv形式をばらしたもの
                 tc_readers_dict
                            この名前でスレッド（TempReaderを呼び出してTc収録機のデー打を受け取る）を立ち上げたもの。
                """
                
                print("{210104} SSR pin_num=2 でしか動いてないように見える")
                print("debug self.tc_index=",self.tc_index)
                for input_port in self.tc_index:
                    print("debug_input_port=",input_port) 
                    if self.tc_readers_dict[input_port[0]].get_tc_now(input_port[1]) is not None:
                        ###################
                        list_tc_temp.append(
                          float(
                          self.tc_readers_dict[input_port[0]].get_tc_now(input_port[1])
                          ))
                
                # キューに入っている温度の平均
                if len(list_tc_temp) > 0:
                    tc_temp_avg = sum(list_tc_temp) / len(list_tc_temp)
                else:
                    tc_temp_avg = 0
                
                """
                
                """
                print(f"@@@@@@@@  SSR({self.pin_num}) Tc: {tc_temp_avg:.2f}")
                pwm_width = self.get_pwm_width(self.target_temp, tc_temp_avg)
                self.set_pwm_width(pwm_width)
                # time.sleep(1)
            except KeyboardInterrupt:
                print (f'exiting thread-1 in temp_read({self.pin_num})')
                self.close()

            
        print(f"exit SSR: {self.pin_num}")

  
    def get_pwm_width(self, target_temp, tc_temp):
        """
            PWM幅の計算
            P制御：設定温度との温度差 * 0.1
            I制御：未実装
            D制御：未実装
        """

        if self.d_temp is None:
            self.d_temp = target_temp - tc_temp
        
        pwm_width = round( (target_temp - tc_temp) * self.kp )

        # print(f"pwm_width = {pwm_width} befor limit")
        # PWM幅を制限 MAX 10
        if pwm_width > MAX_PWM_WIDTH:
            pwm_width = MAX_PWM_WIDTH

        # 温度差（将来のPID制御用）
        self.d_temp = target_temp - tc_temp

        return pwm_width

    def set_pwm_width(self, pwm_width):
        """
            PWMの出力
            on_time: ON時間
            off_time: OFF時間
        """
        pwm_total_time = 1.0
        on_time = pwm_total_time * pwm_width / MAX_PWM_WIDTH
        off_time = pwm_total_time * (MAX_PWM_WIDTH - pwm_width) / MAX_PWM_WIDTH
        # print(f"on: {on_time}, off: {off_time}"
        GPIO.output(self.pin_num, True)
        time.sleep(on_time)
        GPIO.output(self.pin_num, False)
        time.sleep(off_time)

        print(f"SSR({self.pin_num}) pwm_width = {pwm_width}")

    def set_target_temp(self, target_temp):
        self.target_temp = target_temp

    def set_kp(self, kp):
        self.kp = kp

    def close(self):
        """
        外部からSSR制御のスレッド停止用
        """
        print(f"close SSR: {self.pin_num}")
        self.running = False

