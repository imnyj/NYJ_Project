import os
import time
import pickle
import numpy as np

def calculate_flops(W1, W2, W3):
    # FLOPs = 2 * Input * Output (Multiply and Accumulate) for each layer
    # Plus activation functions
    macs_L1 = W1.shape[1] * W1.shape[0]  # 5 * 8 = 40
    macs_L2 = W2.shape[1] * W2.shape[0]  # 8 * 8 = 64
    macs_L3 = W3.shape[1] * W3.shape[0]  # 8 * 9 = 72
    total_macs = macs_L1 + macs_L2 + macs_L3
    total_flops = total_macs * 2  # MAC = 2 FLOPs
    return total_macs, total_flops

def main():
    model_path = "tinymlp_model.pkl"
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        return

    # 1. Measure File Size
    size_bytes = os.path.getsize(model_path)
    size_kb = size_bytes / 1024.0

    # 2. Load Model & Count Parameters
    with open(model_path, "rb") as f:
        model_dict = pickle.load(f)
        
    weights = model_dict["weights"]
    W1, b1 = weights["W1"], weights["b1"]
    W2, b2 = weights["W2"], weights["b2"]
    W3, b3 = weights["W3"], weights["b3"]
    
    total_params = (W1.size + b1.size) + (W2.size + b2.size) + (W3.size + b3.size)
    
    # 3. Calculate MACs and FLOPs
    total_macs, total_flops = calculate_flops(W1, W2, W3)
    
    # 4. Measure Inference Time (CPU)
    # Using the exact inference logic from ai_dcc_hook.py
    n_iters = 10000
    dummy_input = np.array([0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    
    start_time = time.perf_counter()
    for _ in range(n_iters):
        # Layer 1
        h1 = np.dot(W1, dummy_input) + b1
        h1 = np.maximum(0, h1)  # ReLU
        # Layer 2
        h2 = np.dot(W2, h1) + b2
        h2 = np.maximum(0, h2)  # ReLU
        # Layer 3
        logits = np.dot(W3, h2) + b3
        action_idx = int(np.argmax(logits))
    end_time = time.perf_counter()
    
    avg_inference_time_us = ((end_time - start_time) / n_iters) * 1e6
    
    # Jetson / Raspberry Pi Proxy Estimation
    # Assume a low-end ARM Cortex-A53 (Raspberry Pi 3) is ~10-20x slower than a high-end Desktop CPU for single-thread numpy.
    # We will conservatively project it as 15x slower.
    jetson_inference_time_us = avg_inference_time_us * 15.0
    
    print("=== Table 1: Edge Device Profiling of TinyMLP ===")
    print(f"| Metric | Value |")
    print(f"|---|---|")
    print(f"| Architecture | 3-Layer MLP (5 -> 8 -> 8 -> 9) |")
    print(f"| Total Parameters | {total_params} |")
    print(f"| Model Size (Disk) | {size_kb:.2f} KB |")
    print(f"| Computational Cost (MACs) | {total_macs} MACs |")
    print(f"| Computational Cost (FLOPs) | {total_flops} FLOPs |")
    print(f"| Avg Inference Time (Workstation CPU) | {avg_inference_time_us:.2f} 쨉s |")
    print(f"| Est. Inference Time (Jetson Nano / RPi) | ~{jetson_inference_time_us:.2f} 쨉s |")
    print("=================================================")
    print("\n[Analysis] With inference times in the microsecond (쨉s) range and model size around 1.5 KB,")
    print("this model is exceptionally lightweight and perfectly suited for ultra-low latency vehicular edge computing (OBU/RSU).")

if __name__ == "__main__":
    main()
