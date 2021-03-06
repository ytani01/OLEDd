#!/usr/bin/env python3
#
# (c) 2019 Yoichi Tanibayashi
#
import time
import threading
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont

from Oled import Oled
from RotaryEncoder import RotaryEncoder, RotaryEncoderListener

import click

from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
logger = getLogger(__name__)
logger.setLevel(INFO)
handler = StreamHandler()
handler.setLevel(DEBUG)
handler_fmt = Formatter(
    '%(asctime)s %(levelname)s %(name)s.%(funcName)s> %(message)s',
    datefmt='%H:%M:%S')
handler.setFormatter(handler_fmt)
logger.addHandler(handler)
logger.propagate = False
def init_logger(name, debug):
    l = logger.getChild(name)
    if debug:
        l.setLevel(DEBUG)
    else:
        l.setLevel(INFO)
    return l

#####  application
class Frame:
    def __init__(self, ol, color, w, debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.debug = debug
        self.logger.debug('color = %s', color)
        self.logger.debug('w     = %d', w)

        self.ol    = ol
        self.color = color
        self.w     = w

        (self.x1, self.y1) = (0, 0)
        (self.x2, self.y2) = (self.ol.disp.width - 1, self.ol.disp.height - 1)

    def draw(self):
        xy = [(self.x1, self.y1), (self.x2, self.y2)]
        self.ol.draw.rectangle(xy, outline=self.color, width=self.w, fill=0)

class Bar:
    def __init__(self, ol, color, xy, l, debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.debug = debug
        self.logger.debug('color = %s', str(color))
        self.logger.debug('xy    = %s', xy)
        self.logger.debug('l     = %d', l)

        self.ol          = ol
        self.color       = color
        (self.x, self.y) = xy
        self.l           = l

        self.lock = threading.Lock()

    def move(self, v):
        self.lock.acquire()
        self.logger.debug('')

        self.lock.release()

    def draw(self):
        self.lock.acquire()

        x1 = self.x - int(self.l/2)
        x2 = self.x + int(self.l/2)

        self.ol.draw.line([(x1, self.y), (x2, self.y)],
                          fill=self.color, width=2)
        
        self.lock.release()

class Ball:
    def __init__(self, ol, bar, color, xy, r, v=(0, 0), debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.debug = debug
        self.logger.debug('color = %s', str(color))
        self.logger.debug('xy    = %s', xy)
        self.logger.debug('r     = %d', r)
        self.logger.debug('v     = %s', v)

        self.ol            = ol
        self.bar           = bar
        self.color         = color
        (self.x, self.y)   = xy
        self.r             = r
        (self.vx, self.vy) = v

        self.lock = threading.Lock()

    def check_frame(self):
        (x1,  y1)  = (self.x,   self.y)
        (vx1, vy1) = (self.vx,  self.vy)
        
        (x2,  y2)  = (x1 + vx1, y1 + vy1)
        (vx2, vy2) = (vx1,      vy1)

        (x_min, y_min) = (0, 0)
        (x_max, y_max) = (self.ol.disp.width - 1, self.ol.disp.height -1)

        if x2 < 0:
            x2 = -x2
            vx2 = -vx1
        if x2 > x_max:
            x2 = 2 * x_max - x2
            vx2 = -vx1

        if y2 < 0:
            y2 = -y2
            vy2 = -vy1
        if y2 > y_max:
            y2 = 2 * y_max - y2
            vy2 = -vy1

        return ((x2, y2), (vx2, vy2))

    def move(self):
        self.lock.acquire()

        (x1,  y1)  = (self.x,   self.y)
        (vx1, vy1) = (self.vx,  self.vy)
        
        (x2,  y2)  = (x1 + vx1, y1 + vy1)
        (vx2, vy2) = (vx1,      vy1)

        # frame
        ((x2, y2), (vx2, vy2)) = self.check_frame()

        # bar
        (bar_x, bar_y) = (self.bar.x, self.bar.y)
        bar_l          = self.bar.l
        
        if y1 <= bar_y and y2 >= bar_y:
            xb = (x2 - x1) * (bar_y - y1) / (y2 - y1) + x1

            if abs(xb - bar_x) <= bar_l / 2:
                # shoot!
                self.logger.debug('|xb - bar_x| = %f', abs(xb - bar_x))

                y2 = 2 * bar_y - y2
                vx2 = vx1
                vy2 = -vy1

                dy = 0.7
                dx = 1.0
                vx_min = 0.8
                vx_max = 5.0
                vy_min = 0.5
                vy_max = 6.0

                if abs(xb - bar_x) <= 2:
                    self.logger.debug('A:vy2 = %f', vy2)
                    vy2 -= dy
                    
                if xb > bar_x + bar_l / 2 - bar_l * 0.2:
                    vx2 = vx1 + dx
                    vy2 += dy
                    self.logger.debug('B:vx2,vy2 = %f,%f', vx2, vy2)
                    if vx1 > 0 and vx2 > vx_max:
                        vx2 = vx_max
                        self.logger.debug('C:vx2,vy2 = %f,%f', vx2, vy2)
                    if vx1 < 0 and vx2 > -vx_min:
                        vx2 = -vx_min
                        self.logger.debug('D:vx2,vy2 = %f,%f', vx2, vy2)
                    
                if xb < bar_x - bar_l / 2 + bar_l * 0.2:
                    vx2 = vx1 - dx
                    vy2 += dy
                    self.logger.debug('E:vx2,vy2 = %f,%f', vx2, vy2)
                    if vx1 > 0 and vx2 < vx_min:
                        vx2 = vx_min
                        self.logger.debug('F:vx2,vy2 = %f,%f', vx2, vy2)
                    if vx1 < 0 and vx2 < -vx_max:
                        vx2 = -vx_max
                        self.logger.debug('G:vx2,vy2 = %f,%f', vx2, vy2)
                    
                if vy2 < -vy_max:
                    vy2 = -vy_max
                    self.logger.debug('H:vy2 = %f', vy2)
                if vy2 > -vy_min:
                    vy2 = -vy_min
                    self.logger.debug('I:vy2 = %f', vy2)

                self.vx = vx2
                self.vy = vy2
                    
                self.logger.debug('v = (%f, %f)', self.vx, self.vy)

        (self.x,  self.y)  = (x2,  y2)
        (self.vx, self.vy) = (vx2, vy2)
        

        self.lock.release()

    def draw(self):
        self.lock.acquire()
        
        x1 = round(self.x - self.r / 2)
        y1 = round(self.y - self.r / 2)
        x2 = x1 + self.r
        y2 = y1 + self.r

        self.ol.draw.rectangle([(x1, y1), (x2, y2)],
                               outline=self.color, fill=self.color)
        
        self.lock.release()

class App:
    def __init__(self, dev, pin_re, pin_sw, debug=False):
        self.logger = init_logger(__class__.__name__, debug)
        self.debug = debug
        self.logger.debug('dev    = %s',   dev)
        self.logger.debug('pin_re = %s', pin_re)
        self.logger.debug('pin_sw = %d', pin_sw)

        GPIO.setmode(GPIO.BCM)

        self.dev  = dev
        
        self.ol = Oled(self.dev, debug=False)
        self.re = RotaryEncoderListener(pin_re, self.cb_re, debug=False)

        self.color = {}
        self.color['frame'] = 255
        self.color['bar']   = 255
        self.color['ball']  = [255]
        if dev == 'ssd1331':
            self.color['frame'] = 0x00ffff # 'yellow'
            self.color['bar']   = 'green'
            self.color['ball']  = ['red']
            
        self.frame = Frame(self.ol, self.color['frame'], 3, debug=debug)
        self.bar   = Bar(self.ol, self.color['bar'], (20, 52), 13, debug=debug)

        self.ball  = []
        for i in range(len(self.color['ball'])):
            self.ball.append(Ball(self.ol, self.bar, self.color['ball'][i],
                              (5, 10), 3, (2, -2),
                              debug=self.debug))

        self.frame.draw()
        for i in range(len(self.ball)):
            self.ball[i].draw()
        self.ol.display()

    def main(self):
        disp_th = threading.Thread(target=self.move, daemon=True)
        disp_th.start()

        while True:
            self.draw()
            self.ol.display()
            time.sleep(0.01)
                
    def cb_re(self, val):
        self.logger.debug('val = %s', RotaryEncoder.val2str(val))

        if val == RotaryEncoder.CW:
            self.bar.x += 1
        if val == RotaryEncoder.CCW:
            self.bar.x -= 1

        if self.bar.x < 0:
            self.bar.x = 0
        if self.bar.x > self.ol.disp.width - 1:
            self.bar.x = self.ol.disp.width - 1

    def move(self):
        while True:
            for b in self.ball:
                b.move()
                
            time.sleep(.1)

    def draw(self):
        self.frame.draw()
        for b in self.ball:
            b.draw()
        self.bar.draw()

    def finish(self):
        self.logger.debug('')
        self.ol.cleanup()
        GPIO.cleanup()

#####
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('dev', type=str, metavar='<ssd1306|ssd1327|ssd1331>', nargs=1)
@click.option('--pin1', '-p1', 'pin1', type=int, default=27,
              help='rotary encoder pin1')
@click.option('--pin2', '-p2', 'pin2', type=int, default=22,
              help='rotary encoder pin2')
@click.option('--pinsw', '-ps', 'pin_sw', type=int, default=17,
              help='switch pin')
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(dev, pin1, pin2, pin_sw, debug):
    logger = init_logger('', debug)
    logger.debug('dev   = %s', dev)
    logger.debug('debug = %s', debug)

    obj = App(dev, [pin1, pin2], pin_sw, debug=debug)
    try:
        obj.main()
    finally:
        print('finally')
        obj.finish()

if __name__ == '__main__':
    main()
