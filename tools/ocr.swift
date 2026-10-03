import Vision; import AppKit
let args=CommandLine.arguments
let url=URL(fileURLWithPath: args[1])
guard let img=NSImage(contentsOf:url), let cg=img.cgImage(forProposedRect:nil,context:nil,hints:nil) else { exit(1) }
let W=Double(cg.width), H=Double(cg.height)
let req=VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
req.recognitionLanguages = ["la","it-IT","en-US"]
req.minimumTextHeight = 0.004
try VNImageRequestHandler(cgImage:cg).perform([req])
var out:[[String:Any]]=[]
for o in req.results ?? [] {
  guard let c=o.topCandidates(1).first else { continue }
  let b=o.boundingBox
  out.append(["t":c.string,"c":c.confidence,"x":b.minX*W,"y":(1-b.maxY)*H,"w":b.width*W,"h":b.height*H])
}
let d=try JSONSerialization.data(withJSONObject:out)
FileHandle.standardOutput.write(d)
