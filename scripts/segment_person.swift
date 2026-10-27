import Foundation
import Vision
import AppKit
import CoreImage

guard CommandLine.arguments.count >= 3 else {
    fputs("Usage: swift segment_person.swift <input_image> <output_mask_png>\n", stderr)
    exit(1)
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])

guard let ciImage = CIImage(contentsOf: inputURL) else {
    fputs("Failed to load input image\n", stderr)
    exit(1)
}

let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8

let handler = VNImageRequestHandler(ciImage: ciImage, options: [:])
do {
    try handler.perform([request])
    guard let maskPixelBuffer = request.results?.first?.pixelBuffer else {
        fputs("No segmentation result\n", stderr)
        exit(1)
    }
    let maskCI = CIImage(cvPixelBuffer: maskPixelBuffer)
    let context = CIContext()
    guard let cgImage = context.createCGImage(maskCI, from: maskCI.extent) else {
        fputs("Failed to create CGImage\n", stderr)
        exit(1)
    }
    let rep = NSBitmapImageRep(cgImage: cgImage)
    guard let pngData = rep.representation(using: .png, properties: [:]) else {
        fputs("Failed to encode PNG\n", stderr)
        exit(1)
    }
    try pngData.write(to: outputURL)
    print("Mask saved to \(outputURL.path)")
} catch {
    fputs("Error: \(error)\n", stderr)
    exit(1)
}
