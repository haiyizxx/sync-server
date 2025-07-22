import SwiftUI
import AVFoundation

@main
struct RobotSyncCameraApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

class SyncViewModel: NSObject, ObservableObject, AVCapturePhotoCaptureDelegate {
    @Published var isRecording = false
    @Published var lastCommand: String? = nil
    @Published var lastTask: String? = nil
    @Published var lastImageTimestamp: String? = nil
    let serverURL = "https://c4a396c168fb.ngrok.app" // Change to your ngrok URL
    var lastCommandId = 0
    var pollingTimer: Timer?
    var captureTimer: Timer?
    var session: AVCaptureSession?
    var output: AVCapturePhotoOutput?
    var videoDevice: AVCaptureDevice?
    var commandId: Int = 0
    var taskName: String = ""
    
    func startPolling() {
        pollingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            self.pollServer()
        }
    }
    
    func stopPolling() {
        pollingTimer?.invalidate()
        pollingTimer = nil
    }
    
    func pollServer() {
        guard let url = URL(string: "\(serverURL)/poll?last_id=\(lastCommandId)") else { 
            print("❌ Invalid URL: \(serverURL)")
            return 
        }
        
        print(" Polling server: \(url)")
        
        URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                print("❌ Network error: \(error)")
                return
            }
            
            if let data = data {
                print("📦 Received data: \(String(data: data, encoding: .utf8) ?? "none")")
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let newCommand = json["new_command"] as? Bool else { 
                print("❌ Invalid response format")
                return 
            }
            
            print("✅ Parsed response: newCommand=\(newCommand)")
            
            if newCommand, let command = json["command"] as? String, let commandId = json["command_id"] as? Int {
                DispatchQueue.main.async {
                    print("🎯 Received command: \(command), id: \(commandId)")
                    self.lastCommandId = commandId
                    self.commandId = commandId
                    self.lastCommand = command
                    self.taskName = (json["task_name"] as? String) ?? ""
                    if command == "start" {
                        self.isRecording = true
                        self.startImageCapture()
                    } else if command == "end" {
                        self.isRecording = false
                        self.stopImageCapture()
                    }
                }
            }
        }.resume()
    }
    
    func startImageCapture() {
        // Setup camera session
        session = AVCaptureSession()
        session?.sessionPreset = .photo
        guard let device = AVCaptureDevice.default(for: .video) else { 
            print("❌ No camera device available")
            return 
        }
        videoDevice = device
        
        do {
            let input = try AVCaptureDeviceInput(device: device)
            if session!.canAddInput(input) { 
                session!.addInput(input) 
            } else {
                print("❌ Cannot add camera input")
                return
            }
        } catch {
            print("❌ Camera input error: \(error)")
            return
        }
        
        output = AVCapturePhotoOutput()
        if session!.canAddOutput(output!) { 
            session!.addOutput(output!) 
        } else {
            print("❌ Cannot add camera output")
            return
        }
        
        // Start session on background thread
        DispatchQueue.global(qos: .userInitiated).async {
            self.session?.startRunning()
        }
        
        // Start timer for 2 times per second capture (every 0.5 seconds)
        captureTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
            self.capturePhoto()
        }
    }
    
    func stopImageCapture() {
        captureTimer?.invalidate()
        captureTimer = nil
        session?.stopRunning()
        session = nil
        output = nil
    }
    
    func capturePhoto() {
        guard let output = output else {
            print("⚠️ Camera output not available")
            return
        }
        
        let settings = AVCapturePhotoSettings()
        // Use standard settings for better compatibility
        settings.photoQualityPrioritization = .balanced
        
        output.capturePhoto(with: settings, delegate: self)
    }
    
    func uploadImage(imageData: Data, timestamp: String, commandId: Int) {
        guard let url = URL(string: "\(serverURL)/upload_image") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data()
        // Image
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
        // Timestamp
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"timestamp\"\r\n\r\n".data(using: .utf8)!)
        body.append(timestamp.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)
        // Command ID
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"command_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(commandId)".data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)
        // Task name
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"task_name\"\r\n\r\n".data(using: .utf8)!)
        body.append(taskName.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)
        // End
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body
        URLSession.shared.dataTask(with: request) { data, response, error in
            // Optionally handle response
        }.resume()
    }

    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard let data = photo.fileDataRepresentation() else { return }
        
        // Resize image to 224x224
        if let resizedData = resizeImageData(data, to: CGSize(width: 224, height: 224)) {
            let timestamp = String(format: "%.3f", Date().timeIntervalSince1970)
            DispatchQueue.main.async {
                self.lastImageTimestamp = timestamp
            }
            self.uploadImage(imageData: resizedData, timestamp: timestamp, commandId: self.commandId)
        }
    }
    
    private func resizeImageData(_ imageData: Data, to size: CGSize) -> Data? {
        guard let image = UIImage(data: imageData) else { return nil }
        
        let renderer = UIGraphicsImageRenderer(size: size)
        let resizedImage = renderer.image { context in
            // Calculate aspect ratio to maintain proportions
            let imageSize = image.size
            let targetSize = size
            
            let scaleX = targetSize.width / imageSize.width
            let scaleY = targetSize.height / imageSize.height
            let scale = max(scaleX, scaleY) // Use the larger scale to ensure we cover the target size
            
            let scaledWidth = imageSize.width * scale
            let scaledHeight = imageSize.height * scale
            
            // Calculate the crop rectangle to center the image
            let cropX = (scaledWidth - targetSize.width) / 2
            let cropY = (scaledHeight - targetSize.height) / 2
            
            // Draw the image scaled up and cropped to center
            let drawRect = CGRect(x: -cropX, y: -cropY, width: scaledWidth, height: scaledHeight)
            image.draw(in: drawRect)
        }
        
        return resizedImage.jpegData(compressionQuality: 0.8)
    }
}

struct ContentView: View {
    @StateObject var vm = SyncViewModel()
    var body: some View {
        VStack(spacing: 20) {
            Text("Robot Sync Camera App").font(.title)
            Text("Last Command: \(vm.lastCommand ?? "None")")
            Text("Task: \(vm.taskName)")
            Text("Recording: \(vm.isRecording ? "Yes" : "No")")
            Text("Last Image Timestamp: \(vm.lastImageTimestamp ?? "-")")
            Button(vm.pollingTimer == nil ? "Start Polling" : "Stop Polling") {
                if vm.pollingTimer == nil {
                    vm.startPolling()
                } else {
                    vm.stopPolling()
                }
            }
        }
        .padding()
        .onAppear { vm.startPolling() }
        .onDisappear { vm.stopPolling() }
    }
}

// Data extension for multipart
extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
} 