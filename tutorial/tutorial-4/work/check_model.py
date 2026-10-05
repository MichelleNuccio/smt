"""Execute the page's actual JavaScript with macOS JavaScriptCore, without a browser."""
import ctypes as C
from pathlib import Path
import json

lib = C.CDLL("/System/Library/Frameworks/JavaScriptCore.framework/JavaScriptCore")
lib.JSGlobalContextCreate.argtypes = [C.c_void_p]
lib.JSGlobalContextCreate.restype = C.c_void_p
lib.JSStringCreateWithUTF8CString.argtypes = [C.c_char_p]
lib.JSStringCreateWithUTF8CString.restype = C.c_void_p
lib.JSStringGetMaximumUTF8CStringSize.argtypes = [C.c_void_p]
lib.JSStringGetMaximumUTF8CStringSize.restype = C.c_size_t
lib.JSStringGetUTF8CString.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t]
lib.JSStringRelease.argtypes = [C.c_void_p]
lib.JSEvaluateScript.argtypes = [C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_int,C.POINTER(C.c_void_p)]
lib.JSEvaluateScript.restype = C.c_void_p
lib.JSValueToStringCopy.argtypes = [C.c_void_p,C.c_void_p,C.POINTER(C.c_void_p)]
lib.JSValueToStringCopy.restype = C.c_void_p
context = lib.JSGlobalContextCreate(None)
def stringify(value):
    string = lib.JSValueToStringCopy(context,value,None)
    size = lib.JSStringGetMaximumUTF8CStringSize(string)
    buf = C.create_string_buffer(size)
    lib.JSStringGetUTF8CString(string,buf,size)
    lib.JSStringRelease(string)
    return buf.value.decode()
def run(script):
    string = lib.JSStringCreateWithUTF8CString(script.encode())
    error = C.c_void_p()
    result = lib.JSEvaluateScript(context,string,None,None,1,C.byref(error))
    lib.JSStringRelease(string)
    if error.value:
        raise RuntimeError(stringify(error.value))
    return stringify(result)

root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text()
code = html.split("<script>\n")[1].split("</script>")[0]
record = (root / "data/Processed/sandbox.json").read_text()
run("const recordJSON=" + json.dumps(record) + ";")
run("""
const elements=new Map();
const fakeContext=new Proxy({}, {get:(o,k)=>()=>{},set:()=>true});
function element(id){if(!elements.has(id))elements.set(id,{
  textContent:id==='record'?recordJSON:'',value:'',style:{},clientWidth:800,clientHeight:900,
  events:{},attributes:{},parentElement:{},getContext:()=>fakeContext,
  addEventListener(name,handler){this.events[name]=handler;},setAttribute(name,value){this.attributes[name]=value;},
  replaceChildren(){},appendChild(){},getBoundingClientRect(){return {left:0,top:0};}
});return elements.get(id);}
const document={getElementById:element,addEventListener(){},createElement:()=>element(Math.random())};
const window={};
class ResizeObserver{constructor(callback){}observe(){}}
class Path2D{moveTo(){}lineTo(){}closePath(){}}
let timerCallback=null;
function setInterval(callback){timerCallback=callback;return 1;}function clearInterval(){timerCallback=null;}
""")
run(code)
print(run((root / "work/check_model.js").read_text()))
print(run("""
(function(){
  const assert=(v,m)=>{if(!v)throw Error(m);};
  resize();
  $('clock').events.input({target:{value:'2045'}});
  assert(window.sandbox.year===2045&&$('year').value===2045,'Clock updates the displayed year');
  $('rewind').events.click();timerCallback();
  assert(window.sandbox.year===2044,'Rewind moves backward');
  $('play').events.click();assert(timerCallback===null,'Pause stops the clock');
  $('blocks-view').events.click();
  assert(window.sandbox.view==='blocks'&&$('blocks-view').attributes['aria-pressed']==='true','Block view toggles');
  assert($('legend-title').textContent==='US gallons / block / year','Block legend units');
  $('plantings').events.input({target:{value:'100'}});
  assert(window.sandbox.settings.plantings===100,'Planting slider recomputes');
  $('rain').events.input({target:{value:'85'}});
  assert($('rain-value').value==='85.0 in','Rain display shows units');
  $('clock').events.input({target:{value:'2015'}});
  assert(window.sandbox.snapshots[0].alive.reduce((a,b)=>a+b,0)===12094,'Sliders preserve original census');
  $('trees-view').events.click();
  assert($('legend-title').textContent==='US gallons / tree / year','Tree legend units');
  return 'UI event checks passed: clock, rewind, pause, views, planting and rainfall.';
})();
"""))
