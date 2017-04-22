#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import requests
import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import functools

CALENDAR_ICON_PATH = '../img/calendar.png'
POWER_ICON_PATH    = '../img/power.png'
FONT_PATH          = '/usr/share/fonts/opentype/'
FONT_MAP           = {
  'SHINGO_REGULAR'  : 'ShinGoPro/A-OTF-ShinGoPro-Regular.otf',
  'SHINGO_MEDIUM'   : 'ShinGoPro/A-OTF-ShinGoPro-Medium.otf',
  'SHINGO_BOLD'     : 'ShinGoPro/A-OTF-ShinGoPro-Bold.otf',
  'FUTURA_COND_BOLD': 'Futura/FuturaStd-CondensedBold.otf',
  'FUTURA_COND'     : 'Futura/FuturaStd-Condensed.otf',
  'FUTURA_MEDIUM'   : 'Futura/FuturaStd-Medium.otf',
  'FUTURA_BOLD'     : 'Futura/FuturaStd-Bold.otf',
}
FACE_MAP = {
  'date_large' : { 'type': 'FUTURA_COND_BOLD',  'size': 200, },
  'wday_large' : { 'type': 'SHINGO_BOLD',  'size': 140, },
  'power_large': { 'type': 'FUTURA_COND_BOLD',  'size': 180, },
  'temp_large' : { 'type': 'FUTURA_COND_BOLD',  'size': 210, },
  'humi_large' : { 'type': 'FUTURA_COND_BOLD',  'size': 210, },
  'unit_large' : { 'type': 'FUTURA_MEDIUM',  'size': 40, },
  'place'      : { 'type': 'SHINGO_MEDIUM',  'size': 40, },
  'temp'       : { 'type': 'FUTURA_COND_BOLD',    'size': 170, },
  'humi'       : { 'type': 'FUTURA_COND_BOLD',    'size': 170, },
  'co2'        : { 'type': 'FUTURA_COND_BOLD',    'size': 80, },
  'unit'       : { 'type': 'SHINGO_REGULAR', 'size': 40, },
  'time'       : { 'type': 'SHINGO_REGULAR', 'size': 20, },
}

UNIT_MAP = {
  'power'   : u'W',
  'temp'    : u'℃',
  'humi'    : u'％',
  'co2'     : u'ppm',
}
PANEL = {
  'width'   : 1072,
  'height'  : 1448,
}

MARGIN = {
  'panel'   : [30,20],
}

def get_font(face):
  font = PIL.ImageFont.truetype(
    FONT_PATH + FONT_MAP[FACE_MAP[face]['type']],
    FACE_MAP[face]['size']
  )
  return font

def draw_text(img, text, pos, face, align=True):
  draw = PIL.ImageDraw.Draw(img)
  draw.font = get_font(face)
  next_pos_y =  pos[1] + draw.font.getsize(text)[1]

  if align:
    # 右寄せ
    None
  else:
    # 左寄せ
    pos = (pos[0]-draw.font.getsize(text)[0], pos[1])
    
  draw.text(pos, text, (0, 0, 0))
  
  return next_pos_y

######################################################################
class SenseLargePanel:
  def __init__(self, image, offset, width):
    self.image = image
    self.offset = np.array(offset)
    self.width = width
    self.calendar_icon = PIL.Image.open(CALENDAR_ICON_PATH, 'r')
    self.power_icon = PIL.Image.open(POWER_ICON_PATH, 'r')

  def __get_date_box_size(self, value):
    return get_font('date_large').getsize('12331')

  def __get_wday_box_size(self):
    return get_font('wday_large').getsize(u'(金)')
  
  def __get_temp_box_size(self):
    return get_font('temp_large').getsize('44.4')
  
  def __get_temp_unit_box_size(self):
    return get_font('unit_large').getsize(UNIT_MAP['temp'])

  def __get_humi_box_size(self):
    return get_font('humi_large').getsize('44.4')

  def __get_humi_unit_box_size(self):
    return get_font('unit_large').getsize(UNIT_MAP['humi'])

  def __get_power_box_size(self, value):
    # PIM が baseline を取得できないっぽいので，「,」ではなく「.」を使う
    return get_font('power_large').getsize('{:,}'.format(value).replace(',', '.'))
  
  def __get_power_unit_box_size(self):
    size = get_font('unit_large').getsize(UNIT_MAP['power'])
    return (int(size[0] * 1.2), size[1])
  
  def offset_map(self, data):
    box_size = {
      'date'      : self.__get_date_box_size(data['date']),
      'wday'      : self.__get_wday_box_size(),
      'temp'      : self.__get_temp_box_size(),
      'temp_unit' : self.__get_temp_unit_box_size(),
      'humi'      : self.__get_humi_box_size(),
      'humi_unit' : self.__get_humi_unit_box_size(),
      'power'     : self.__get_power_box_size(data['power']),
      'power_unit': self.__get_power_unit_box_size(),
    }
    max_height = max(map(lambda x: x[1], box_size.values()))

    return {
      # 'temp_right':
      #   self.offset + np.array([box_size['temp'][0], 0]),
      # 'temp_unit_right':
      #   self.offset + np.array([self.width/2-20, max_height - box_size['temp_unit'][1]]),
      # 'humi_right':
      #   self.offset + np.array([self.width/2+40 + box_size['humi'][0], 0]),
      # 'humi_unit_right':
      #   self.offset + np.array([
      #     self.width,
      #     max_height - box_size['humi_unit'][1]
      #   ]),
      
      'calendar_icon_left':
        self.offset + np.array([
          0,
          0
        ]),
      'date_right':
        self.offset + np.array([self.width - box_size['wday'][0], 0]),
      'wday_right':
        self.offset + np.array([self.width, box_size['date'][1] - box_size['wday'][1]]),
      'power_icon_left':
        self.offset + np.array([
          0,
          box_size['date'][1] + 60
        ]),
      'power_right':
        self.offset + np.array([
          self.width - box_size['power_unit'][0],
          box_size['date'][1] + 60
        ]),
      'power_unit_right':
        self.offset + np.array([
          self.width,
          self.calendar_icon.height + 60 + box_size['power'][1] - box_size['power_unit'][1]
        ]),
    }
      
  def draw(self, data):
    data['date_str'] = '{0:%-m/%-d}'.format(data['date'])
    data['wday_str'] = u'(%s)' % ([u'月',u'火',u'水',u'木',u'金',u'土',u'日'][data['date'].weekday()])
    
    offset_map = self.offset_map(data)
    next_draw_y_list = []

    next_draw_y_list.append(draw_text(
      self.image, data['date_str'],
      offset_map['date_right'],
      'date_large', False
    ))
    next_draw_y_list.append(draw_text(
      self.image, data['wday_str'],
      offset_map['wday_right'],
      'wday_large', False
    ))

    
    for sense_type in ['power']:
      value = ''
      if sense_type == 'power':
        value = '{:,}'.format(data[sense_type])
      else:
        value = '%.1f' % (data[sense_type])
        
      next_draw_y_list.append(draw_text(
        self.image, value,
        offset_map[sense_type + '_right'],
        sense_type + '_large', False
      ))

      if sense_type != 'date':
        next_draw_y_list.append(draw_text(
          self.image, UNIT_MAP[sense_type],
          offset_map[sense_type + '_unit_right'],
          'unit_large', False
        ))

    img.paste(self.calendar_icon, tuple(offset_map['calendar_icon_left']))
    img.paste(self.power_icon, tuple(offset_map['power_icon_left']))
      
    return int(max(next_draw_y_list)) + 20
      
######################################################################
class SenseDetailPanel:
  def __init__(self, image, offset, width):
    self.image = image
    self.offset = np.array(offset)
    self.width = width

  def __get_place_box_size(self):
    font = get_font('place')
    max_size = np.array([0, 0])
      
    for label in PLACE_LIST:
      size = np.array(font.getsize(label))
      max_size = np.maximum(max_size, size)

      return max_size + np.array([
        font.getsize(u' ')[0],
        0
      ])

  def __get_temp_box_size(self):
    return get_font('temp').getsize('44.4')

  def __get_temp_unit_box_size(self):
    size = get_font('unit').getsize(UNIT_MAP['temp'])
    return (int(size[0] * 1.2), size[1])

  def __get_humi_box_size(self):
    return get_font('humi').getsize('44.4')

  def __get_humi_unit_box_size(self):
    size = get_font('unit').getsize(UNIT_MAP['humi'])
    return (int(size[0] * 1.2), size[1])

  def __get_co2_box_size(self):
    return (
      get_font('co2').getsize('4,444')[0],
      get_font('co2').getsize('4')[1],
    )
  def __get_co2_unit_box_size(self):
    # PIM が baseline を取得できないっぽいので，descent が無い「m」を使う
    return get_font('unit').getsize('m' * len(UNIT_MAP['co2']))
      
  def offset_map(self):
    box_size = {
      'place'	: self.__get_place_box_size(),
      'temp'      : self.__get_temp_box_size(),
      'temp_unit' : self.__get_temp_unit_box_size(),
      'humi'      : self.__get_humi_box_size(),
      'humi_unit' : self.__get_humi_unit_box_size(),
      'co2'       : self.__get_co2_box_size(),
      'co2_unit'  : self.__get_co2_unit_box_size(),
    }

    col_gap = (self.width + box_size['place'][0] - \
               functools.reduce((lambda x, y: x + y),
                                map(lambda x: x[0], box_size.values()))) / 2

    max_height = max(map(lambda x: x[1], box_size.values()))
    
    offset_map = {
      'place-left': (0, 0),
      'temp-right': (box_size['temp'][0], box_size['place'][1]*1.2),
    }
    
    offset_map['temp_unit-right'] \
      = np.array([offset_map['temp-right'][0], offset_map['temp-right'][1]]) + \
        np.array([box_size['temp_unit'][0], max_height - box_size['temp_unit'][1]])
    
    offset_map['humi-right'] \
      = np.array([offset_map['temp_unit-right'][0], offset_map['temp-right'][1]]) + \
        np.array([col_gap + box_size['humi'][0], max_height - box_size['humi'][1]])

    offset_map['humi_unit-right'] \
      = np.array([offset_map['humi-right'][0], offset_map['temp-right'][1]]) + \
        np.array([box_size['humi_unit'][0], max_height - box_size['humi_unit'][1]])

    offset_map['co2-right'] \
      = np.array([offset_map['humi_unit-right'][0], offset_map['temp-right'][1]]) + \
        np.array([col_gap + box_size['co2'][0], max_height - box_size['co2'][1]])

    offset_map['co2_unit-right'] \
      = np.array([offset_map['co2-right'][0], offset_map['temp-right'][1]]) + \
        np.array([box_size['co2_unit'][0], max_height - box_size['co2_unit'][1]])
    
    for key in offset_map.keys():
      offset_map[key] += self.offset

    offset_map['line_height'] = box_size['place'][1] + max_height * 1.45
      
    return offset_map
      
  def draw(self, data_list):
    offset_map = self.offset_map()
    next_draw_y_list = []
    
    i = 0
    for data in data_list:
      line_offset = np.array([
        0, (offset_map['line_height'] * i)
      ])
      next_draw_y_list.append(draw_text(
        self.image, data['place'],
        offset_map['place-left'] + line_offset,
        'place'
      ))
      next_draw_y_list.append(draw_text(
        self.image, '%.1f' % (data['temp']),
        offset_map['temp-right'] + line_offset,
        'temp', False
      ))
      next_draw_y_list.append(draw_text(
        self.image, UNIT_MAP['temp'],
        offset_map['temp_unit-right'] + line_offset,
        'unit', False
      ))
      next_draw_y_list.append(draw_text(
        self.image, '%.1f' % (data['humi']),
        offset_map['humi-right'] + line_offset,
        'humi', False
      ))
      next_draw_y_list.append(draw_text(
        self.image, UNIT_MAP['humi'],
        offset_map['humi_unit-right'] + line_offset,
        'unit', False
      ))
      next_draw_y_list.append(draw_text(
        self.image, '{:,}'.format(data['co2']),
        offset_map['co2-right'] + line_offset,
        'co2', False
      ))
      next_draw_y_list.append(draw_text(
        self.image, UNIT_MAP['co2'],
        offset_map['co2_unit-right'] + line_offset,
        'unit', False
      ))
      i += 1

    return int(max(next_draw_y_list)) + 40

######################################################################
class UpdateTimePanel:
  def __init__(self, image, offset, width):
    self.image = image
    self.offset = np.array(offset)
    self.width = width

  def __get_time_box_size(self):
    return get_font('time').getsize(
      u'{0:%Y-%m-%d %H:%M} 更新'.format(datetime.datetime.now())
    )

  def offset_map(self, data):
    box_size = {
      'time'      : self.__get_time_box_size(),
    }
    max_height = max(map(lambda x: x[1], box_size.values()))

    return {
      'time_right':
        self.offset + np.array([
          self.width,
          -20
        ]),
    }
      
  def draw(self, data):
    offset_map = self.offset_map(data)
    next_draw_y_list = []

    next_draw_y_list.append(draw_text(
      self.image, u'{0:%Y-%m-%d %H:%M} 更新'.format(data['date']),
      offset_map['time_right'],
      'time', False
    ))

    return int(max(next_draw_y_list)) + 40
      
######################################################################

PLACE_LIST = [u'リビング', u'和室', u'家事室', u'書斎']
HOST_MAP  = {
  u'リビング': 'rasp-meter-1',
  u'和室'    : 'rasp-meter-2',
  u'家事室'  : 'rasp-meter-4',
  u'書斎'    : 'rasp-meter-3',
  u'電力'    : 'rasp-meter-5',
}

# InfluxDB にアクセスしてセンサーデータを取得
def get_sensor_value(hostname):
  response = requests.get(
    'http://localhost:8086/query',
    params={
      'db': 'sensor',
      'q': 'SELECT * FROM "sensor" WHERE "hostname" = \'%s\' ORDER by time desc  LIMIT 1' % hostname
    })
  columns = response.json()['results'][0]['series'][0]['columns']
  values = response.json()['results'][0]['series'][0]['values'][0]

  data = {}
  for i, key in enumerate(columns):
    data[key] = values[i]

  return data

def get_sensor_data_map():
  data = []
  for place in PLACE_LIST:
    value = get_sensor_value(HOST_MAP[place])
    value['place'] = place
    data.append(value)

  return data
  
  
######################################################################

sense_data = get_sensor_data_map()

img = PIL.Image.new("RGBA", (PANEL['width'], PANEL['height']))

next_draw_y = 0
sense_large_panel = SenseLargePanel(
  img,
  np.array(MARGIN['panel']) + np.array([0, next_draw_y]),
  PANEL['width'] - MARGIN['panel'][0]*2
)
next_draw_y = sense_large_panel.draw({
  'date': datetime.datetime.now(),
  'power': get_sensor_value(HOST_MAP[u'電力'])['power'],
})
sense_detail_panel = SenseDetailPanel(
  img,
  np.array(MARGIN['panel']) + np.array([0, next_draw_y]),
  PANEL['width'] - MARGIN['panel'][0]*2
)
next_draw_y = sense_detail_panel.draw(sense_data)
update_time_panel = UpdateTimePanel(
  img,
  np.array(MARGIN['panel']) + np.array([0, next_draw_y]),
  PANEL['width'] - MARGIN['panel'][0]*2
)
next_draw_y = update_time_panel.draw({'date': datetime.datetime.now()})


img.save("out.png")


