"""Regenerate native Skia reference paths; needs skia-python==144.1 + numpy.

Algorithm transcription from the pinned LinearDrawingDelegate.java. This runs
native Skia PathMeasure.getSegment, not the TypeScript contour implementation.
No Android UI/emulator is involved; these are geometry fixtures, not screenshots
of a running Android component.
"""
import json
from pathlib import Path
import numpy as np
import skia

f = np.float32

def reference(width, progress, phase, amplitude):
    width, progress, phase = f(width), f(progress), f(phase)
    cycles = int(width / 40)
    if cycles == 0:  # Our guarded behaviour; upstream divides by zero here.
        cycles = 1
    wavelength = f(width / cycles)
    p = skia.Path()
    smooth = f(.48)
    for i in range(cycles + 1):
        p.cubicTo(float(f(2*i + smooth)), 0, float(f(2*i + 1 - smooth)), 1, 2*i+1, 1)
        p.cubicTo(float(f(2*i + 1 + smooth)), 1, float(f(2*i + 2 - smooth)), 0, 2*i+2, 0)
    matrix = skia.Matrix.Scale(float(f(wavelength/2)), -2)
    matrix.postTranslate(0, 1)
    p.transform(matrix)
    measure = skia.PathMeasure(p, False)
    radius = f(2)
    start = f(radius / width)
    end = f(f(int(f(progress * width)) - radius) / width)
    count = f(width / wavelength)
    ratio = f(count / f(count+1))
    start = f(f(start + f(phase / count)) * ratio)
    end = f(f(end + f(phase / count)) * ratio)
    result = skia.Path()
    measure.getSegment(float(f(start*f(measure.getLength()))), float(f(end*f(measure.getLength()))), result, True)
    transform = skia.Matrix.Translate(float(f(-f(phase * wavelength))), 0)
    transform.postScale(1, amplitude)
    result.transform(transform)
    curves = [[[float(p.x()), float(p.y())] for p in pts] for verb, pts in result if verb == skia.Path.kCubic_Verb]
    return dict(width=float(width), progress=float(progress), phase=float(phase), amplitude=amplitude,
                length=measure.getLength(), curves=curves)

cases = []
for width in [39, 40, 41, 100, 300, 712, 1000]:
    for progress in [.1, .5001, .8, .9]:
        for phase in [0, .25, .5, .999]:
            for amplitude in [.6, 3]:
                cases.append(reference(width, progress, phase, amplitude))
out = Path(__file__).with_name('paths.json')
out.write_text(json.dumps(dict(skia=skia.__version__, cases=cases), separators=(',', ':'))+'\n')
print(f'{len(cases)} native Skia reference paths -> {out} ({out.stat().st_size} bytes)')
