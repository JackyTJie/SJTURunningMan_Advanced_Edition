"""Render fixed-phase golden frames with native Skia and the Android draw order.

Needs skia-python==144.1 + numpy. This checks the Web renderer against Skia;
these frames are not screenshots of an Android widget/emulator.
"""
import base64
import json
from pathlib import Path
import numpy as np
import skia
from importlib.util import spec_from_file_location, module_from_spec

spec = spec_from_file_location('paths', Path(__file__).with_name('generate-paths.py'))
paths = module_from_spec(spec)
spec.loader.exec_module(paths)
f = np.float32

WIDTH, HEIGHT = 300, 10
ACTIVE, TRACK = '#2b5ea7', '#dae2f9'

def rect(cx, width, height):
    return skia.Rect.MakeXYWH(cx-width/2, -height/2, width, height)

def paint(color, stroke=False):
    value = skia.Paint(Color=skia.ColorSetRGB(*bytes.fromhex(color[1:])), AntiAlias=True)
    if stroke:
        value.setStyle(skia.Paint.kStroke_Style)
        value.setStrokeWidth(4)
        value.setStrokeCap(skia.Paint.kRound_Cap)
    return value

def round_block(canvas, color, center, clip_center=None, clip_right=False):
    canvas.save()
    if clip_center is not None:
        clip_width = 4
        if clip_right:
            diff = clip_center-center
            if diff > 0:
                clip_center -= diff/2
                clip_width += diff
        else:
            diff = clip_center-center
            if diff < 0:
                clip_center -= diff/2
                clip_width -= diff
        canvas.clipRRect(skia.RRect.MakeRectXY(rect(clip_center,clip_width,4),2,2), skia.ClipOp.kIntersect, False)
        canvas.drawRect(skia.Rect.MakeXYWH(center if clip_right else center-2,-2,2,4), paint(color))
    canvas.drawRoundRect(rect(center,4,4),2,2,paint(color))
    canvas.restore()

def draw(progress, phase, amplitude):
    surface = skia.Surface(WIDTH, HEIGHT)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    canvas.save()
    canvas.clipRect(skia.Rect.MakeWH(WIDTH,HEIGHT))
    canvas.translate(0,5)
    progress = f(progress)
    def draw_line(start, end, gap, color, active):
        gap = int(f(f(gap * min(start,f(.01))) / f(.01)))
        start_px, end_px = int(f(f(start*WIDTH)+gap)), int(f(end*WIDTH))
        if start_px>end_px:
            return
        first,last=start_px+2,end_px-2
        if start_px==0 and end_px<4:
            round_block(canvas,color,first,last,True)
        elif start_px>end_px-4:
            round_block(canvas,color,last,first,False)
        elif active and amplitude>0:
            result=paths.reference(WIDTH,progress,phase,amplitude)
            path=skia.Path()
            for i,c in enumerate(result['curves']):
                if i==0:path.moveTo(*c[0])
                path.cubicTo(*c[1],*c[2],*c[3])
            canvas.drawPath(path,paint(color,True))
        else:
            canvas.drawLine(first,0,last,0,paint(color,True))
    draw_line(progress,f(1),4,TRACK,False)
    draw_line(f(0),progress,0,ACTIVE,True)
    round_block(canvas,ACTIVE,WIDTH-2)
    canvas.restore()
    data = surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType, alphaType=skia.AlphaType.kUnpremul_AlphaType)
    return base64.b64encode(data.tobytes()).decode()

cases=[]
for progress in [0,.002,.005,.01,.1,.5,.8,.9,.99,.995,1]:
    for phase in [0,.25,.999]:
        amplitude = 3 if .1<=progress<=.9 else 0
        cases.append(dict(progress=progress,phase=phase,amplitude=amplitude,rgba=draw(progress,phase,amplitude)))
Path(__file__).with_name('rasters.json').write_text(json.dumps(dict(width=WIDTH,height=HEIGHT,active=ACTIVE,track=TRACK,cases=cases),separators=(',',':'))+'\n')
print(f'{len(cases)} native Skia raster frames -> rasters.json')
