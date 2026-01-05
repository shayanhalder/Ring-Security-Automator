#!/usr/bin/env python3
"""
Test script to verify server-client connection.
Run this on the Raspberry Pi to test connectivity.
"""
import requests
import sys

if len(sys.argv) < 2:
    print("Usage: python test_connection.py <server_ip>")
    print("Example: python test_connection.py 192.168.1.100")
    sys.exit(1)

SERVER_IP = sys.argv[1]
SERVER_URL = f"http://{SERVER_IP}:5000"

print(f"Testing connection to server at {SERVER_URL}...")
print("-" * 50)

# Test 1: Basic connectivity
print("\n1. Testing basic connectivity...")
try:
    response = requests.get(f"{SERVER_URL}/status", timeout=2)
    if response.status_code == 200:
        print("   ✓ Server is reachable")
        status = response.json()
        print(f"   - People in house: {status['people_in_house']}")
        print(f"   - Security status: {status['security_status']}")
        print(f"   - Active trackers: {status['tracker_count']}")
    else:
        print(f"   ✗ Server returned error: {response.status_code}")
        sys.exit(1)
except requests.exceptions.Timeout:
    print("   ✗ Connection timeout - server may be down")
    sys.exit(1)
except requests.exceptions.ConnectionError:
    print("   ✗ Connection failed - check IP address and firewall")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: Test with dummy frame
print("\n2. Testing frame processing...")
try:
    import cv2
    import numpy as np
    import base64
    
    # Create a dummy 640x360 frame
    dummy_frame = np.random.randint(0, 255, (360, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', dummy_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    frame_b64 = base64.b64encode(buffer).decode('utf-8')
    
    payload = {
        'frame': frame_b64,
        'timestamp': 1234567890.0
    }
    
    response = requests.post(f"{SERVER_URL}/process_frame", json=payload, timeout=10)
    
    if response.status_code == 200:
        print("   ✓ Frame processing works")
        result = response.json()
        print(f"   - Detections: {len(result.get('detections', []))}")
        print(f"   - Face recognition results: {len(result.get('face_recognition', []))}")
    else:
        print(f"   ✗ Frame processing failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
except ImportError:
    print("   ⚠ Skipping frame test (cv2 not installed)")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: Network latency
print("\n3. Testing network latency...")
try:
    import time
    latencies = []
    
    for i in range(5):
        t0 = time.time()
        response = requests.get(f"{SERVER_URL}/status", timeout=2)
        latency = (time.time() - t0) * 1000  # Convert to ms
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    
    print(f"   - Average latency: {avg_latency:.1f} ms")
    print(f"   - Min latency: {min_latency:.1f} ms")
    print(f"   - Max latency: {max_latency:.1f} ms")
    
    if avg_latency < 50:
        print("   ✓ Latency is good")
    elif avg_latency < 100:
        print("   ⚠ Latency is acceptable")
    else:
        print("   ⚠ Latency is high - may affect performance")
        
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 50)
print("Connection test complete!")
print("You can now run: python tripwire_client.py")
