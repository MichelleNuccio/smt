import Foundation
import JavaScriptCore

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let html = try String(contentsOf: root.appendingPathComponent("index.html"), encoding: .utf8)
let record = try String(contentsOf: root.appendingPathComponent("data/Processed/sandbox.json"), encoding: .utf8)
let code = html.components(separatedBy: "<script>\n")[1].components(separatedBy: "</script>")[0]
let context = JSContext()!
context.exceptionHandler = { _, exception in
    print("JavaScript error: \(exception?.toString() ?? "unknown")")
}
context.setObject(record, forKeyedSubscript: "recordJSON" as NSString)
context.evaluateScript("""
const elements=new Map();
const fakeContext=new Proxy({}, {get:(o,k)=>()=>{},set:()=>true});
function element(id){if(!elements.has(id))elements.set(id,{
  textContent:id==='record'?recordJSON:'',value:'',style:{},clientWidth:800,clientHeight:900,
  parentElement:{},getContext:()=>fakeContext,addEventListener(){},setAttribute(){},
  replaceChildren(){},appendChild(){},getBoundingClientRect(){return {left:0,top:0};}
});return elements.get(id);}
const document={getElementById:element,addEventListener(){},createElement:()=>element(Math.random())};
const window={};
class ResizeObserver{constructor(callback){}observe(){}}
class Path2D{moveTo(){}lineTo(){}closePath(){}}
function setInterval(){return 1;}function clearInterval(){}
""
)
context.evaluateScript(code)
if context.exception != nil { exit(1) }
let tests = try String(contentsOf: root.appendingPathComponent("work/check_model.js"), encoding: .utf8)
let result = context.evaluateScript(tests)
if context.exception != nil { exit(1) }
print(result?.toString() ?? "No test result")
