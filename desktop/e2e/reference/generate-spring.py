"""Run the unmodified pinned AndroidX SpringForce.java to generate reference data.

Needs a JDK. Minimal host stubs only supply annotations, Force and MassState;
all spring mathematics execute in the original Java class.
"""
import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = root / 'third_party/material-progress/SpringForce.java'
with tempfile.TemporaryDirectory(prefix='sjtu-spring-') as folder:
    dest = Path(folder)
    files = {
        'androidx/annotation/FloatRange.java': 'package androidx.annotation; public @interface FloatRange { double from() default Double.NEGATIVE_INFINITY; double to() default Double.POSITIVE_INFINITY; boolean fromInclusive() default true; boolean toInclusive() default true; }',
        'androidx/annotation/RestrictTo.java': 'package androidx.annotation; public @interface RestrictTo { Scope[] value(); enum Scope { LIBRARY } }',
        'androidx/dynamicanimation/animation/Force.java': 'package androidx.dynamicanimation.animation; public interface Force { float getAcceleration(float value, float velocity); boolean isAtEquilibrium(float value, float velocity); }',
        'androidx/dynamicanimation/animation/DynamicAnimation.java': 'package androidx.dynamicanimation.animation; public class DynamicAnimation { static class MassState { float mValue; float mVelocity; } }',
        'androidx/dynamicanimation/animation/Reference.java': '''package androidx.dynamicanimation.animation;
public class Reference {
 public static void main(String[] args) {
  System.out.print("["); boolean first = true;
  for(float value : new float[]{0,2500,8000}) for(float velocity : new float[]{-1000,0,1000})
  for(float target : new float[]{0,5000,10000}) for(int dt : new int[]{0,1,16,33,100,500,1000}) {
   SpringForce spring = new SpringForce(target).setStiffness(50).setDampingRatio(1);
   DynamicAnimation.MassState result = spring.updateValues(value, velocity, dt);
   if(!first) System.out.print(","); first=false;
   System.out.print("["+value+","+velocity+","+target+","+dt+","+result.mValue+","+result.mVelocity+"]");
  }
  System.out.println("]");
 }
}''',
    }
    java_files = [str(source)]
    for name, text in files.items():
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        java_files.append(str(p))
    subprocess.run(['javac', '-d', str(dest), *java_files], check=True)
    output = subprocess.check_output(['java', '-cp', str(dest), 'androidx.dynamicanimation.animation.Reference'])
    cases = json.loads(output)
    target = Path(__file__).with_name('spring.json')
    target.write_text(json.dumps(cases, separators=(',', ':'))+'\n')
    print(f'{len(cases)} unmodified AndroidX Java spring cases -> {target}')
