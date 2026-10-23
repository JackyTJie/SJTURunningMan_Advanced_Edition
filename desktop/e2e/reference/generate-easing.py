"""Generate golden easing tables from the original AOSP Path.cpp C++ functions.

Needs clang++/g++. Extracts the unchanged cubic approximation routines and uses
host stubs for SkPoint. Table lookup mirrors PathInterpolator.java.
"""
import json
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[2] / 'third_party/material-progress/Path.cpp').read_text()
functions = source[source.index('    typedef SkPoint (*bezierCalculation)'):source.index('    static void createVerbSegments')]
prefix = '''#include <cmath>
#include <map>
#include <vector>
#include <iostream>
#include <iomanip>
struct SkPoint {
 float a,b; float x() const {return a;} float y() const {return b;}
 static SkPoint Make(float a,float b) {return {a,b};}
 static float Distance(const SkPoint& a,const SkPoint& b) {return std::hypot(a.a-b.a,a.b-b.b);}
 bool operator==(const SkPoint& rhs) const {return a==rhs.a && b==rhs.b;}
};
'''
main = '''int main() {
 std::cout << std::setprecision(10) << "[";
 for(int curve=0;curve<2;curve++) {
  SkPoint points[4]={{0,0},{curve?0.3f:0.2f,0},{curve?0.8f:0.0f,curve?0.2f:1.0f},{1,1}};
  std::vector<SkPoint> samples; std::vector<float> lengths;
  addBezier(points,cubicBezierCalculation,samples,lengths,0.002f*0.002f,true);
  if(curve) std::cout << ",";
  std::cout << "[";
  for(int i=0;i<=1000;i++) {
   float input=i/1000.0f; int lo=0,hi=samples.size()-1;
   while(hi-lo>1) {int mid=(lo+hi)/2;if(input<samples[mid].x())hi=mid;else lo=mid;}
   float dx=samples[hi].x()-samples[lo].x();
   float y=dx==0?samples[lo].y():samples[lo].y()+((input-samples[lo].x())/dx)*(samples[hi].y()-samples[lo].y());
   if(i)std::cout << ",";
   std::cout << y;
  }
  std::cout << "]";
 }
 std::cout << "]";
}
'''
with tempfile.TemporaryDirectory(prefix='sjtu-easing-') as folder:
    cpp = Path(folder) / 'reference.cpp'
    cpp.write_text(prefix+functions+main)
    binary = Path(folder) / 'reference'
    subprocess.run(['c++', '-std=c++17', '-ffp-contract=off', str(cpp), '-o', str(binary)], check=True)
    cases = json.loads(subprocess.check_output([str(binary)]))
    Path(__file__).with_name('easing.json').write_text(json.dumps(cases, separators=(',', ':'))+'\n')
    print('2002 easing samples from AOSP C++ -> easing.json')
