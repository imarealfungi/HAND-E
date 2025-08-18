using System;
using System.IO;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Reflection;
using System.Linq;
using Buttplug.Client;
using Buttplug.Core;
using Buttplug.Core.Messages;

namespace HandyButtplugServer
{
    public class CommandRequest
    {
        public string command { get; set; } = "";
        public double position { get; set; } = 0.0;
        public int duration { get; set; } = 0;
    }

    public class StatusResponse
    {
        public bool connected { get; set; } = false;
        public bool device_connected { get; set; } = false;
        public string device_name { get; set; } = "";
        public string status { get; set; } = "";
    }

    public class RealButtplugServer
    {
        private readonly HttpListener _httpListener;
        private ButtplugClient? _buttplugClient;
        private ButtplugClientDevice? _handyDevice;
        private bool _isRunning;
        private bool _isConnectedToIntiface;
        private bool _isDeviceConnected;

        public RealButtplugServer()
        {
            _httpListener = new HttpListener();
            _httpListener.Prefixes.Add("http://localhost:8080/");  // FIXED: Back to port 8080
        }

        public async Task StartAsync()
        {
            try
            {
                _httpListener.Start();
                _isRunning = true;

                Console.WriteLine("=== HANDY AI STROKER - BUTTPLUG 3.1.1 SERVER ===");
                Console.WriteLine("HTTP Server started on: http://localhost:8080/");
                Console.WriteLine("Ready to connect to Intiface Central and The Handy");
                Console.WriteLine("Press Ctrl+C to stop");
                Console.WriteLine();

                await HandleHttpRequests();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error starting server: {ex.Message}");
            }
        }

        private async Task HandleHttpRequests()
        {
            while (_isRunning)
            {
                try
                {
                    var context = await _httpListener.GetContextAsync();
                    _ = Task.Run(() => ProcessRequest(context));
                }
                catch (Exception ex) when (_isRunning)
                {
                    Console.WriteLine($"Error handling request: {ex.Message}");
                }
            }
        }

        private async Task ProcessRequest(HttpListenerContext context)
        {
            var request = context.Request;
            var response = context.Response;

            try
            {
                response.Headers.Add("Access-Control-Allow-Origin", "*");
                response.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
                response.Headers.Add("Access-Control-Allow-Headers", "Content-Type");

                if (request.HttpMethod == "OPTIONS")
                {
                    response.StatusCode = 200;
                    response.Close();
                    return;
                }

                Console.WriteLine($"Received {request.HttpMethod} request to {request.Url?.AbsolutePath}");

                string responseString = "";

                switch (request.Url?.AbsolutePath.ToLower())
                {
                    case "/connect":
                        responseString = await HandleConnect();
                        break;

                    case "/disconnect":
                        responseString = await HandleDisconnect();
                        break;

                    case "/status":
                        responseString = HandleStatus();
                        break;

                    case "/command":  // FIXED: Added back the /command endpoint
                        responseString = await HandleCommand(request);
                        break;

                    default:
                        response.StatusCode = 404;
                        responseString = JsonSerializer.Serialize(new { error = "Endpoint not found" });
                        break;
                }

                byte[] buffer = Encoding.UTF8.GetBytes(responseString);
                response.ContentType = "application/json";
                response.ContentLength64 = buffer.Length;
                await response.OutputStream.WriteAsync(buffer, 0, buffer.Length);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing request: {ex.Message}");
                response.StatusCode = 500;
                string errorResponse = JsonSerializer.Serialize(new { error = ex.Message });
                byte[] errorBuffer = Encoding.UTF8.GetBytes(errorResponse);
                await response.OutputStream.WriteAsync(errorBuffer, 0, errorBuffer.Length);
            }
            finally
            {
                response.Close();
            }
        }

        private async Task<string> HandleConnect()
        {
            try
            {
                if (!_isConnectedToIntiface)
                {
                    Console.WriteLine("🔌 Python app requested connection");
                    Console.WriteLine("Creating Buttplug client...");

                    _buttplugClient = new ButtplugClient("Handy AI Stroker Server");

                    // Set up event handlers
                    _buttplugClient.DeviceAdded += OnDeviceAdded;
                    _buttplugClient.DeviceRemoved += OnDeviceRemoved;
                    _buttplugClient.ServerDisconnect += OnServerDisconnect;

                    Console.WriteLine("Connecting to Intiface Central...");

                    // Try multiple Intiface addresses
                    string[] intifaceUrls = {
                        "ws://localhost:12345",
                        "ws://127.0.0.1:12345",
                        "ws://192.168.4.24:12345"
                    };

                    foreach (string url in intifaceUrls)
                    {
                        try
                        {
                            Console.WriteLine($"  Trying to connect to: {url}");
                            await _buttplugClient.ConnectAsync(new ButtplugWebsocketConnector(new Uri(url)));
                            _isConnectedToIntiface = true;
                            Console.WriteLine($"✓ Connected to Intiface at: {url}");
                            break;
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"✗ Failed to connect to {url}: {ex.Message}");
                        }
                    }

                    if (!_isConnectedToIntiface)
                    {
                        return JsonSerializer.Serialize(new StatusResponse
                        {
                            connected = false,
                            device_connected = false,
                            status = "Could not connect to Intiface Central. Make sure it's running."
                        });
                    }

                    // Start scanning for devices
                    Console.WriteLine("Starting device scan...");
                    await _buttplugClient.StartScanningAsync();

                    // Wait a moment for devices to be discovered
                    await Task.Delay(3000);
                    await _buttplugClient.StopScanningAsync();
                }

                return JsonSerializer.Serialize(new StatusResponse
                {
                    connected = _isConnectedToIntiface,
                    device_connected = _isDeviceConnected,
                    device_name = _handyDevice?.Name ?? "None",
                    status = _isConnectedToIntiface ?
                        (_isDeviceConnected ? "Connected and device ready" : "Connected, scanning for devices...") :
                        "Disconnected"
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Connection error: {ex.Message}");
                return JsonSerializer.Serialize(new StatusResponse
                {
                    connected = false,
                    device_connected = false,
                    status = $"Error: {ex.Message}"
                });
            }
        }

        private async Task<string> HandleDisconnect()
        {
            try
            {
                Console.WriteLine("🔌 Python app requested disconnection");

                if (_isConnectedToIntiface && _buttplugClient != null)
                {
                    await _buttplugClient.DisconnectAsync();
                    _isConnectedToIntiface = false;
                    _isDeviceConnected = false;
                    _handyDevice = null;
                    Console.WriteLine("✓ Disconnected from Intiface Central");
                }

                return JsonSerializer.Serialize(new { status = "Disconnected" });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Disconnect error: {ex.Message}");
                return JsonSerializer.Serialize(new { error = ex.Message });
            }
        }

        private string HandleStatus()
        {
            return JsonSerializer.Serialize(new StatusResponse
            {
                connected = _isConnectedToIntiface,
                device_connected = _isDeviceConnected,
                device_name = _handyDevice?.Name ?? "None",
                status = _isConnectedToIntiface ?
                    (_isDeviceConnected ? "Connected and device ready" : "Connected, no device") :
                    "Disconnected"
            });
        }

        private async Task<string> HandleCommand(HttpListenerRequest request)
        {
            try
            {
                if (!_isDeviceConnected || _handyDevice == null)
                {
                    return JsonSerializer.Serialize(new { error = "No device connected" });
                }

                // Read request body
                string requestBody;
                using (var reader = new StreamReader(request.InputStream))
                {
                    requestBody = await reader.ReadToEndAsync();
                }

                var command = JsonSerializer.Deserialize<CommandRequest>(requestBody);

                if (command == null)
                {
                    return JsonSerializer.Serialize(new { error = "Invalid command format" });
                }

                switch (command.command.ToLower())
                {
                    case "move":
                        await SendLinearCommand(command.position, command.duration);
                        Console.WriteLine($"🎮 REAL MOVE: Position {command.position:F2}, Duration {command.duration}ms → The Handy");
                        break;

                    case "stop":
                        await SendLinearCommand(0.0, 500);
                        Console.WriteLine($"🛑 REAL STOP: Moving The Handy to position 0 (full depth)");
                        break;

                    default:
                        return JsonSerializer.Serialize(new { error = "Unknown command" });
                }

                return JsonSerializer.Serialize(new { status = "Command sent to device" });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Command error: {ex.Message}");
                return JsonSerializer.Serialize(new { error = ex.Message });
            }
        }

        private async Task SendLinearCommand(double position, int durationMs)
        {
            try
            {
                if (_handyDevice == null || !_isDeviceConnected)
                {
                    Console.WriteLine("⚠️  Cannot send command: device not connected");
                    return;
                }

                // Clamp position to 0-1 range
                position = Math.Round(Math.Max(0.0, Math.Min(1.0, position)), 2);
                uint duration = (uint)Math.Max(100, durationMs);

                Console.WriteLine($"🔄 Using LinearAsync with CORRECT parameter order: duration={duration}, position={position:F2}");

                // Use the correct method signature: LinearAsync(UInt32 duration, Double position)
                try
                {
                    await _handyDevice.LinearAsync(duration, position);
                    Console.WriteLine($"📤 SUCCESS: LinearAsync sent to {_handyDevice.Name}: duration={duration}ms, position={position:F2}");
                    return;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"❌ LinearAsync failed: {ex.Message}");
                }

                Console.WriteLine($"❌ LinearAsync command failed for {_handyDevice.Name}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Error in SendLinearCommand: {ex.Message}");
            }
        }

        private void OnDeviceAdded(object? sender, DeviceAddedEventArgs e)
        {
            Console.WriteLine($"🔍 Device found: {e.Device.Name} (Index: {e.Device.Index})");

            // THOROUGHLY INSPECT THE HANDY'S PROPERTIES
            Console.WriteLine($"📋 INSPECTING {e.Device.Name} PROPERTIES:");

            try
            {
                // Get all public properties of the device
                var deviceType = e.Device.GetType();
                var properties = deviceType.GetProperties();

                Console.WriteLine($"  Device Type: {deviceType.Name}");
                Console.WriteLine($"  Available Properties:");

                foreach (var prop in properties)
                {
                    try
                    {
                        var value = prop.GetValue(e.Device);
                        Console.WriteLine($"    - {prop.Name}: {value ?? "null"}");

                        // If it's a collection, show its contents
                        if (value is System.Collections.IDictionary dict)
                        {
                            Console.WriteLine($"      Dictionary contents:");
                            foreach (var key in dict.Keys)
                            {
                                Console.WriteLine($"        {key}: {dict[key]}");
                            }
                        }
                        else if (value is System.Collections.IEnumerable enumerable && !(value is string))
                        {
                            Console.WriteLine($"      Collection contents:");
                            foreach (var item in enumerable)
                            {
                                Console.WriteLine($"        {item}");
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"    - {prop.Name}: ERROR - {ex.Message}");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  ❌ Error inspecting device: {ex.Message}");
            }

            // Accept The Handy regardless so we can test commands
            _handyDevice = e.Device;
            _isDeviceConnected = true;

            Console.WriteLine($"✓ Device connected: {e.Device.Name}");
            Console.WriteLine($"  Device Index: {e.Device.Index}");
            Console.WriteLine($"  Device ready for capability analysis!");
        }

        private void OnDeviceRemoved(object? sender, DeviceRemovedEventArgs e)
        {
            if (e.Device == _handyDevice)
            {
                _handyDevice = null;
                _isDeviceConnected = false;
                Console.WriteLine("✗ The Handy device disconnected");
            }
            else
            {
                Console.WriteLine($"Device disconnected: {e.Device.Name}");
            }
        }

        private void OnServerDisconnect(object? sender, EventArgs e)
        {
            _isConnectedToIntiface = false;
            _isDeviceConnected = false;
            _handyDevice = null;
            Console.WriteLine("✗ Disconnected from Intiface Central");
        }

        public void Stop()
        {
            _isRunning = false;
            _httpListener?.Stop();

            if (_buttplugClient != null && _isConnectedToIntiface)
            {
                try
                {
                    _buttplugClient.DisconnectAsync().Wait(1000);
                }
                catch { }
            }

            Console.WriteLine("Server stopped");
        }
    }

    class Program
    {
        private static RealButtplugServer? _server;

        static async Task Main(string[] args)
        {
            Console.CancelKeyPress += (sender, e) =>
            {
                e.Cancel = true;
                _server?.Stop();
                Environment.Exit(0);
            };

            try
            {
                _server = new RealButtplugServer();
                await _server.StartAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Fatal error: {ex.Message}");
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
            }
        }
    }
}