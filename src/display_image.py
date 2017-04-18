#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import functools

FONT_PATH    = '/usr/share/fonts/opentype/'
FONT_MAP     = {
    'REGULAR': 'ShinGoPro/A-OTF-ShinGoPro-Regular.otf',
    'MEDIUM': 'ShinGoPro/A-OTF-ShinGoPro-Medium.otf',
    'BOLD': 'ShinGoPro/A-OTF-ShinGoPro-Bold.otf',
}
FACE_MAP = {
    'temp_large': { 'type': 'BOLD',  'size': 300, },
    'humi_large': { 'type': 'BOLD',  'size': 300, },
    'unit_large': { 'type': 'MEDIUM',  'size': 150, },
    'place': { 'type': 'MEDIUM',  'size': 40, },
    'temp' : { 'type': 'BOLD',    'size': 80, },
    'humi' : { 'type': 'BOLD',    'size': 80, },
    'co2'  : { 'type': 'BOLD',    'size': 40, },
    'unit' : { 'type': 'REGULAR', 'size': 30, },
}

PLACE_LIST = [u'リビング', u'寝室', u'家事室', u'書斎']
DATA_MAP  = {
    u'リビング': 'rasp-meter-1',
    u'寝室'    : 'rasp-meter-2',
    u'家事室'  : 'rasp-meter-4',
    u'書斎'    : 'rasp-meter-3',
}
UNIT_MAP = {
    'temp': u'℃',
    'humi': u'％',
    'co2': u'ppm',
}
PANEL = {
    'width': 1072,
    'height': 1448,
}


MARGIN = {
    'panel': [30,20],
}

def get_font(face):
  font = PIL.ImageFont.truetype(
      FONT_PATH + FONT_MAP[FACE_MAP[face]['type']],
      FACE_MAP[face]['size']
  )
  return font


######################################################################
class SenseLargePanel:
    def __init__(self, image, offset, width):
        self.image = image
        self.offset = np.array(offset)
        self.width = width

    def __get_temp_box_size(self):
        return get_font('temp_large').getsize('44.4')

    def __get_temp_unit_box_size(self):
        return get_font('unit_large').getsize(UNIT_MAP['temp'])

    def __get_humi_box_size(self):
        return get_font('humi_large').getsize('44.4')

    def __get_humi_unit_box_size(self):
        return get_font('unit_large').getsize(UNIT_MAP['humi'])
        
    def offset_map(self):
        box_size = {
            'temp'     : self.__get_temp_box_size(),
            'temp_unit': self.__get_temp_unit_box_size(),
            'humi'     : self.__get_humi_box_size(),
            'humi_unit': self.__get_humi_unit_box_size(),
        }
        max_height = max(map(lambda x: x[1], box_size.values()))

        return {
            'temp_right':
                self.offset + np.array([box_size['temp'][0], 0]),
            'temp_unit_right':
                self.offset + np.array([self.width, (max_height - box_size['temp_unit'][1])]),
            'humi_right':
                self.offset + np.array([box_size['humi'][0], box_size['temp'][1] * 1.2]),
            'humi_unit_right':
                self.offset + np.array([
                    self.width,
                    box_size['temp'][1] * 1.2 + (max_height - box_size['humi_unit'][1])
                ])
        }
    
    def draw(self, data):
        offset_map = self.offset_map()
        next_draw_y_list = []

        for sense_type in ['temp', 'humi']:
            next_draw_y = draw_text(
                self.image, '%.1f' % (data[sense_type]),
                offset_map[sense_type + '_right'],
                sense_type + '_large', False
            )
            next_draw_y_list.append(next_draw_y)
            
            next_draw_y = draw_text(
                self.image, UNIT_MAP[sense_type],
                offset_map[sense_type + '_unit_right'],
                'unit_large', False
            )
            next_draw_y_list.append(next_draw_y)

        return int(max(next_draw_y_list))
            
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
            font.getsize(u'　')[0],
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

        col_gap = (self.width - \
                   functools.reduce((lambda x, y: x + y),
                                    map(lambda x: x[0], box_size.values()))) / 2
        max_height = max(map(lambda x: x[1], box_size.values()))
        offset_map = {
            'place-left':
                np.array([
                    0,
                    (max_height - box_size['place'][1]) / 2
                ]),
        }
        offset_map['temp-right'] = offset_map['place-left'] + np.array([
            box_size['place'][0] + box_size['temp'][0],
            - offset_map['place-left'][1] + max_height - box_size['temp'][1]
        ])
        offset_map['temp_unit-right'] = offset_map['temp-right'] + np.array([
            box_size['temp_unit'][0],
            - offset_map['temp-right'][1] + max_height - box_size['temp_unit'][1]
        ])
        offset_map['humi-right'] = offset_map['temp_unit-right'] + np.array([
            box_size['humi'][0] + col_gap,
            - offset_map['temp_unit-right'][1] + max_height - box_size['humi'][1]
        ])
        offset_map['humi_unit-right'] = offset_map['humi-right'] + np.array([
            box_size['humi_unit'][0],
            - offset_map['humi-right'][1] + max_height - box_size['humi_unit'][1]
        ])
        offset_map['co2-right'] = offset_map['humi_unit-right'] + np.array([
            box_size['co2'][0] + col_gap,
            - offset_map['humi_unit-right'][1] + max_height - box_size['co2'][1]
        ])
        offset_map['co2_unit-right'] = offset_map['co2-right'] + np.array([
            box_size['co2_unit'][0],
            - offset_map['co2-right'][1] + max_height - box_size['co2_unit'][1]
        ])
        
        for key in offset_map.keys():
            offset_map[key] += self.offset

        offset_map['line_height'] = max_height * 1.5
            
        return offset_map
    
    def draw(self, data_list):
        offset_map = self.offset_map()
        i = 0
        for data in data_list:
            line_offset = np.array([
                0, (offset_map['line_height'] * i)
            ])
            draw_text(
                self.image, data['place'],
                offset_map['place-left'] + line_offset,
                'place'
            )
            draw_text(
                self.image, '%.1f' % (data['temp']),
                offset_map['temp-right'] + line_offset,
                'temp', False
            )
            draw_text(
                self.image, UNIT_MAP['temp'],
                offset_map['temp_unit-right'] + line_offset,
                'unit', False
            )
            draw_text(
                self.image, '%.1f' % (data['humi']),
                offset_map['humi-right'] + line_offset,
                'humi', False
            )
            draw_text(
                self.image, UNIT_MAP['humi'],
                offset_map['humi_unit-right'] + line_offset,
                'unit', False
            )
            draw_text(
                self.image, '{:,}'.format(data['co2']),
                offset_map['co2-right'] + line_offset,
                'co2', False
            )
            draw_text(
                self.image, UNIT_MAP['co2'],
                offset_map['co2_unit-right'] + line_offset,
                'unit', False
            )
            i += 1


            
            
        # draw_text(
        #     self.image, '%.1f' % (data['humi']),
        #     offset_map['humi_right'],
        #     'humi_large', False
        # )
            


    #     print((10, 20) + (1, 2))
        
    #     print(offset_map)
        
        # draw_text(
        #     self.image, '%.1f' % (data['temp']),
        #     offset_map['temp_right'],
        #     'temp_large', False
        # )
    #     draw_text(
    #         self.image, UNIT_MAP['temp'],
    #         offset_map['temp_unit_right'],
    #         'unit_large', False
    #     )
    #     draw_text(
    #         self.image, '%.1f' % (data['humi']),
    #         offset_map['humi_right'],
    #         'humi_large', False
    #     )
    #     draw_text(
    #         self.image, UNIT_MAP['humi'],
    #         offset_map['humi_unit_right'],
    #         'unit_large', False
    #     )
######################################################################




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

def draw_text_at_center(img, text):
  draw = PIL.ImageDraw.Draw(img)
  draw.font = get_font('label')

  img_size = numpy.array(img.size)
  txt_size = numpy.array(draw.font.getsize(text))
  pos = (img_size - txt_size) / 2

  draw.text(pos, text, (0, 0, 0))

def draw_sense_data(img, label, data, y, col_map):
    draw_text(img, label,
              (
                  col_map['pos']['label-left'][0],
                  y + col_map['pos']['label-left'][1]
              ),
              'label')
    draw_text(img, '%.1f' % (data['temp']),
              (
                  col_map['pos']['temp-right'][0],
                  y + col_map['pos']['temp-right'][1]
              ),
              'temp', False)
    draw_text(img, UNIT_MAP['temp'],
              (
                  col_map['pos']['temp_unit-right'][0],
                  y + col_map['pos']['temp_unit-right'][1]
              ),
              'unit', False)
    draw_text(img, '%.1f' % (data['humi']),
              (
                  col_map['pos']['humi-right'][0],
                  y + col_map['pos']['humi-right'][1]
              ),
              'temp', False)
    draw_text(img, UNIT_MAP['humi'],
              (
                  col_map['pos']['humi_unit-right'][0],
                  y + col_map['pos']['humi_unit-right'][1]
              ),
              'unit', False)
    draw_text(img, "{:,}".format(data['co2']),
              (
                  col_map['pos']['co2-right'][0],
                  y + col_map['pos']['co2-right'][1]
              ),
              'co2', False)
    draw_text(img, UNIT_MAP['co2'],
              (
                  col_map['pos']['co2_unit-right'][0],
                  y + col_map['pos']['co2_unit-right'][1]
              ),
              'unit', False)
    
  
img = PIL.Image.new("RGBA", (PANEL['width'], PANEL['height']))





sense_data = [
    {
        'place': u'リビング',
        'temp': 24.3,
        'humi': 45.1,
        'co2' : 1240,
    },
    {
        'place': u'寝室',
        'temp': 24.3,
        'humi': 45.1,
        'co2' : 1240,
    },
    {
        'place': u'和室',
        'temp': 24.3,
        'humi': 45.1,
        'co2' : 1240,
    },
    {
        'place': u'家事室',
        'temp': 24.3,
        'humi': 45.1,
        'co2' : 1240,
    },


    
]

sense_large_panel = SenseLargePanel(
    img,
    MARGIN['panel'],
    PANEL['width'] - MARGIN['panel'][0]*2
)
next_draw_y = sense_large_panel.draw({
    'temp': 34.8,
    'humi': 63.1,
})

sense_detail_panel = SenseDetailPanel(
    img,
    np.array(MARGIN['panel']) + np.array([0, next_draw_y + 40]),
    PANEL['width'] - MARGIN['panel'][0]*2
)


sense_detail_panel.draw(sense_data)



y = 800


img.save("out.png")


