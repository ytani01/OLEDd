#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
#import Adafruit_SSD1306
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1327, ssd1306
from PIL import Image, ImageDraw, ImageFont
#import textwrap
import mojimoji
import unicodedata
import time
import click

from ipaddr import ipaddr

## logging
from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
logger = getLogger(__name__)
logger.setLevel(INFO)
handler = StreamHandler()
handler.setLevel(DEBUG)
handler_fmt = Formatter('%(asctime)s %(levelname)s %(funcName)s> %(message)s',
                        datefmt='%H:%M:%S')
handler.setFormatter(handler_fmt)
logger.addHandler(handler)
logger.propagate = False

# $ wget http://www.geocities.jp/littlimi/arc/misaki/misaki_ttf_2015-04-10.zip
FONT_DIR	= '/home/pi/font/misakifont'
FONT_NAME	= 'misaki_gothic.ttf'
FONT_PATH	= FONT_DIR + '/' + FONT_NAME

#
# part: 'header', 'body', 'footer'
#
class OledPart:
    def __init__(self, disp_row, rows=0, zenkaku=True, crlf=True):
        self.enable = True

        self.disp_row = disp_row
        self.rows     = rows

        self.zenkaku  = zenkaku
        self.crlf     = crlf
        
        self.cur_row  = 0
        self.clear()		# self.line[]

    def clear(self):
        self.line = [''] * self.rows

    def writeline(self, text):
        if self.cur_row > self.rows - 1:
            self.cur_row = self.rows -1
            if self.crlf:
                self.line.pop(0)
                self.line.append('')
            
        self.line[self.cur_row] = text

        if self.crlf:
            self.cur_row += 1
#
#
#
class OledText:
    # 全角モードで半角に変換し直す文字
    TRANS_SRC = '　．、，－＋＊／’”｀：；（）［］＜＞＃＄％＆＠￥'
    TRANS_DST = ' .､,-+*/\'\"`:;()[]<>#$%&@\\'

    def __init__(self, device='ssd1306', headerlines=0, footerlines=0,
                 zenkaku=False, fontsize=8, rst=24):
        self.device   = device
        self.enable   = True
        self.fontsize = fontsize
        self.rst      = rst

        self.trans_tbl = str.maketrans(__class__.TRANS_SRC,
                                       __class__.TRANS_DST)

        # initialize display
        self.i2c = i2c(port=1, address=0x3C)

        self.disp = None
        if device == 'ssd1306':
            #self.disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.rst)
            self.disp = ssd1306(self.i2c)
            self.mode = '1'
        if device == 'ssd1327':
            self.disp = ssd1327(self.i2c)
            self.mode = 'RGB'
        if self.disp == None:
            self.enable = False
            return None
        '''
        try:
            self.disp.begin()
        except:
            self.enable = False
            return None
        '''

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self.image = Image.new(self.mode, (self.disp.width, self.disp.height))

        # Get drawing object to draw on image.
        self.draw = ImageDraw.Draw(self.image)

        # clear display
        self.disp.clear()

        # load font
        self.font = ImageFont.truetype(FONT_PATH, self.fontsize,
                                       encoding='unic')
        (self.char_width, self.char_height) = self.font.getsize('８')
        self.char_height += 1
        
        # physical cols and rows
        self.disp_cols = int(self.disp.width  / self.char_width)
        self.disp_rows = int(self.disp.height / self.char_height)

        # setup header, footer and body
        self.cur_part = 'body'
        if not self.set_layout(headerlines, footerlines):
            self.enable = False
            return None

    # set header and footer
    def set_layout(self, header_lines=0, footer_lines=0, display_now=True):
        if header_lines + footer_lines + 2 > self.disp_rows:
            return False

        header_start = 0
        body_start   = header_lines
        footer_start = self.disp_rows - footer_lines
        body_lines   = self.disp_rows - header_lines - footer_lines
        if header_lines > 0:
            body_start += 1
            body_lines -= 1
        if footer_lines > 0:
            body_lines -= 1

        self.part = {}
        self.part['header'] = OledPart(header_start, header_lines)
        self.part['body']   = OledPart(body_start,   body_lines)
        self.part['footer'] = OledPart(footer_start, footer_lines)

        # display
        self._draw_border()
        self._display(display_now)
            
        return True

    # output physical display
    def _display(self, display_now=True):
        if not self.enable:
            return
        
        if display_now:
            #self.disp.image(self.image)
            self.disp.display(self.image)

    # draw border
    def _draw_border(self, width=2, display_now=False):
        x1 = 0
        x2 = self.disp.width - 1

        # header
        if self.part['header'].rows > 0:
            y1 = self.char_height * (self.part['header'].rows + 0.5) - 1
            self.draw.line([(x1, y1), (x2, y1)], fill=255, width=width)

        # footer
        if self.part['footer'].rows > 0:
            y1 = self.disp.height - \
                 self.char_height * (self.part['footer'].rows + 0.5) - 1
            self.draw.line([(x1, y1), (x2, y1)], fill=255, width=width)

        self._display(display_now)

    def _clear(self, part=''):
        if part == '':
            part = self.cur_part

        x1 = 0
        y1 = self.char_height * self.part[part].disp_row
        x2 = self.disp.width - 1
        y2 = y1 + self.char_height * self.part[part].rows - 1
        self.draw.rectangle([(x1, y1), (x2, y2)], outline=0, fill=0)
        logger.debug('clear rectangle (%d,%d),(%d,%d)', x1, y1, x2, y2)
        
    # clear display
    def clear(self, part='', display_now=True):
        if part == '':
            part = self.cur_part

        # clear text
        self.part[part].clear()

        # clear part area
        self._clear(part)
        
        # display
        self._display(display_now)

    # selct current part
    def set_part(self, part='body', row=-1, zenkaku=None, crlf=None):
        if not self.enable:
            return

        if part in self.part.keys():
            self.cur_part = part
        else:
            return

        if row >= 0:
            self.part[part].cur_row = row

        if zenkaku != None:
            self.part[part].zenkaku = zenkaku

        if crlf != None:
            self.part[part].crlf = crlf
        
    # set part and row
    def set_row(self, row, part=''):
        if part == '':
            part = self.cur_part

        self.set_part(part, row=row)
    
    # set zenkaku_flag
    def set_zenkaku(self, zenkaku, part=''):
        if part == '':
            part = self.cur_part

        self.set_part(part, zenkaku=zenkaku)

    # 改行設定
    def set_crlf(self, crlf, part=''):
        if part == '':
            part = self.cur_part

        self.set_part(part, crlf=crlf)

    #
    def _draw_1line(self, disp_row, text, fill=255):
        x1, y1 = 0, disp_row * self.char_height
        self.draw.text((x1,y1), text, font=self.font, fill=fill)
        logger.debug('draw.text(%d, %d)', x1, y1)

    #
    def _draw_part(self, part=''):
        if part == '':
            part = self.cur_part

        # clear part area
        self._clear(part)

        # draw lines in current part
        disp_row = self.part[part].disp_row
        for txt in self.part[part].line:
            self._draw_1line(disp_row, txt)
            disp_row += 1

    # 1行分出力し、crlfフラグに応じてスクロール処理も行う
    def _print_1line(self, text, part='', crlf=None):
        logger.debug('part=%-6s crlf=%s text=\'%s\'', part, crlf, text)

        if part == '':
            part = self.cur_part
            logger.debug('part=%-6s', part)
        if self.part[part].rows < 1:
            return

        if crlf == None:
            crlf = self.part[part].crlf
            logger.debug('crlf=%s', crlf)
        self.part[part].crlf = crlf

        self.part[part].writeline(text)

        # draw part
        # (text[]上での操作を self.drawに反映)
        self._draw_part(part)

    # 長い行を折り返して出力する。必要に応じてスクロールも行う。
    def print(self, text, part='', crlf=None, display_now=True):
        logger.debug('part=%-6s crlf=%s text=\'%s\'', part, crlf, text)
        if part == '':
            part = self.cur_part
            logger.debug('part=%-6s', part)
        if crlf == None:
            crlf = self.part[part].crlf
            logger.debug('crlf=%s', crlf)
        self.part[part].crlf = crlf

        if len(text) == 0:
            # clear one line
            self._print_1line('', part=part, crlf=crlf)
            return

        if self.part[part].zenkaku:
            text = mojimoji.han_to_zen(text).translate(self.trans_tbl)

        # 長い行は折り返し
        # crlfがFalseの場合は、最初の1行だけ出力
        line = ''
        zenkaku_len = 0
        for ch in text:
            if unicodedata.east_asian_width(ch) in 'FWA':
                ch_len = 1
            else:
                ch_len = 0.5

            if zenkaku_len + ch_len > self.disp_cols:
                logger.debug('line=%s zenkaku_len=%.1f ch_len=%.1f',
                             line, zenkaku_len, ch_len)
                self._print_1line(line, part=part, crlf=crlf)

                line = ''
                zenkaku_len = 0
                
                if not crlf:
                    break
                
            line += ch
            zenkaku_len += ch_len

        if zenkaku_len > 0:
            self._print_1line(line, part=part, crlf=crlf)
        
        # display OLED
        self._display(display_now)
        
#####
@click.command(help='OLED Text library')
@click.argument('display', nargs=1)
@click.option('--debug', '-d', 'debug', is_flag=True, default=False,
              help='debug flag')
def main(display, debug):
    logger.setLevel(INFO)
    if debug:
        logger.setLevel(DEBUG)

    ot = OledText(display, 2,1)
    logger.info('font:   %d', ot.fontsize)
    logger.info('char:   %d x %d', ot.char_width, ot.char_height)
    logger.info('disp:   %d x %d', ot.disp_cols, ot.disp_rows)
    ip = ipaddr().ip_addr()
    logger.info('ipaddr: %s', ip)

    ot.set_part('header')
    ot.print(time.strftime('%Y/%m/%d(%a)'))
    time.sleep(2)
    ot.print(time.strftime('%H:%M:%S'))
    time.sleep(2)
    ot.set_part('footer', crlf=False)
    ot.print(ip, part='footer')
    time.sleep(2)
    ot.set_part('body', zenkaku=False)
    ot.print('ABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞ')
    time.sleep(2)
    ot.print('ABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞABCあいうえお0123456789ガギグゲゴｶﾞｷﾞｸﾞｹﾞｺﾞ')
    time.sleep(2)
    ot.print('font: %d = %d x %d pixels' % (ot.fontsize,
                                              ot.char_width, ot.char_height))
    ot.print('%d cols x %d rows' % (ot.disp_cols, ot.disp_rows))
    time.sleep(2)
    ot.set_row(1, 'header')
    ot.set_crlf(False)
    ot.set_zenkaku(True)
    ot.print(time.strftime('%H:%M:%S'))
    time.sleep(0.5)
    ot.set_row(1)
    ot.print(time.strftime('%H:%M:%S'))
    time.sleep(0.5)
    ot.set_row(1)
    ot.print(time.strftime('%H:%M:%S'))
    time.sleep(0.5)
    ot.set_row(1)
    ot.print(time.strftime('%H:%M:%S'))
    time.sleep(0.5)
    ot.clear('footer')
    time.sleep(2)
    ot.clear('body')
    time.sleep(2)
    ot.clear('header')

if __name__ == '__main__':
    main()
