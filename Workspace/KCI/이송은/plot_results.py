import os
import csv
import time
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import SAC, TD3, PPO

# 기본 설정
DATA_DIR = "data"
MODELS_DIR = "models"
OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 폰트 및 스타일 (논문용 포맷에 가깝게 설정)
plt.rcParams.update({'font.size': 12, 'axes.grid': True, 'grid.alpha': 0.5})

def load_csv(filepath):
    """CSV 파일을 읽어서 x(Timestep 등), y(값) 리스트로 반환"""
    if not os.path.exists(filepath):
        return [], []
    x, y = [], []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader) # 헤더 스킵
        for row in reader:
            if len(row) >= 2:
                x.append(float(row[0]))
                y.append(float(row[1]))
    return np.array(x), np.array(y)

def plot_1_reward_ablation_study():
    """1. 리워드 절제 연구 (Proposed vs Ablation)"""
    plt.figure(figsize=(8, 5))
    
    x1, y1 = load_csv(f"{DATA_DIR}/learning_curve_Proposed_PPO.csv")
    x2, y2 = load_csv(f"{DATA_DIR}/learning_curve_Proposed_PPO_ablation.csv")
    
    if len(x1) > 0:
        plt.plot(x1, y1, label='Proposed PPO (Continuous Reward)', color='blue', linewidth=2)
    if len(x2) > 0:
        plt.plot(x2, y2, label='Proposed PPO (Ablation - Binary Reward)', color='red', linestyle='--', linewidth=2)
        
    plt.xlabel('Timesteps')
    plt.ylabel('Success Rate')
    plt.title('Reward Ablation Study')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/1_reward_ablation_study.png", dpi=300)
    plt.close()
    print("Generated 1_reward_ablation_study.png")

def plot_2_learning_curves():
    """2. 방안별 학습 곡선 비교"""
    plt.figure(figsize=(8, 5))
    
    colors = {'Proposed_PPO': 'blue', 'SAC': 'green', 'TD3': 'orange'}
    for model_name, color in colors.items():
        x, y = load_csv(f"{DATA_DIR}/learning_curve_{model_name}.csv")
        if len(x) > 0:
            plt.plot(x, y, label=model_name.replace("_", " "), color=color, linewidth=2)
            
    plt.xlabel('Timesteps')
    plt.ylabel('Success Rate')
    plt.title('Learning Curves Comparison')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/2_learning_curves.png", dpi=300)
    plt.close()
    print("Generated 2_learning_curves.png")

import psutil

def generate_3_hardware_feasibility():
    """3. 하드웨어 적용 가능성 (NVIDIA Jetson 호환성 분석용)"""
    models = {'SAC': SAC, 'TD3': TD3, 'Proposed_PPO': PPO}
    output_csv = f"{OUTPUT_DIR}/3_hardware_feasibility_table.csv"
    
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Model", "Num_Parameters", "Model_Size_MB", 
            "Est_FLOPs_per_step", "Training_Time_sec", "Inference_Time_ms", 
            "CPU_Usage_Percent", "RAM_Usage_MB", "Jetson_Feasible"
        ])
        
        for name, ModelClass in models.items():
            model_path = f"{MODELS_DIR}/{name}.zip"
            if not os.path.exists(model_path):
                continue
                
            model = ModelClass.load(model_path, device='cpu')
            
            # 파라미터 수 및 모델 크기
            num_params = sum(p.numel() for p in model.policy.parameters())
            model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
            
            # 대략적인 FLOPs 계산 (MLP 구조 가정, 파라미터 수 * 2)
            est_flops = num_params * 2
            
            # 훈련 시간 로드
            train_time_file = f"{DATA_DIR}/training_time_{name}.txt"
            train_time = 0.0
            if os.path.exists(train_time_file):
                with open(train_time_file, "r") as f:
                    train_time = float(f.read().strip())
            
            dummy_obs = np.zeros((1,) + model.observation_space.shape, dtype=np.float32)
            
            # CPU/RAM 측정 시작
            process = psutil.Process(os.getpid())
            cpu_before = process.cpu_percent(interval=0.1)
            mem_before = process.memory_info().rss
            
            # 인퍼런스 타임 측정 (웜업 후 1000회 반복)
            for _ in range(10):
                model.predict(dummy_obs, deterministic=True)
                
            start_time = time.time()
            n_iters = 1000
            for _ in range(n_iters):
                model.predict(dummy_obs, deterministic=True)
            end_time = time.time()
            
            # CPU/RAM 측정 종료
            cpu_after = process.cpu_percent(interval=0.1)
            mem_after = process.memory_info().rss
            
            avg_inference_ms = ((end_time - start_time) / n_iters) * 1000.0
            ram_usage_mb = max(0, (mem_after - mem_before) / (1024 * 1024))
            # cpu_percent는 interval 측정에 따라 달라질 수 있으므로 절대값만 참고
            cpu_usage = cpu_after
            
            # NVIDIA Jetson Nano/Xavier 기준 판별 (매우 넉넉한 기준)
            # Jetson Nano: 4GB RAM, 0.5 TFLOPS. (우리의 MLP 모델은 보통 수 MB, 수 Kilo FLOPs 수준)
            jetson_feasible = "Yes (Zero Downtime Capable)" if (model_size_mb < 50 and avg_inference_ms < 10.0) else "Borderline"
            
            writer.writerow([
                name, num_params, f"{model_size_mb:.3f}", 
                est_flops, f"{train_time:.2f}", f"{avg_inference_ms:.4f}", 
                f"{cpu_usage:.1f}", f"{ram_usage_mb:.2f}", jetson_feasible
            ])
            
    print(f"Generated {output_csv}")

def plot_4_delay_vs_density():
    """4. 차량 밀도별 딜레이 비교"""
    filepath = f"{DATA_DIR}/access_delay_vs_density.csv"
    if not os.path.exists(filepath):
        return
        
    data = {}
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 3:
                density = float(row[0])
                model = row[1]
                delay = float(row[2])
                
                if model not in data:
                    data[model] = {'x': [], 'y': []}
                data[model]['x'].append(density)
                data[model]['y'].append(delay)
                
    plt.figure(figsize=(8, 5))
    markers = {'Proposed_PPO': 'o', 'SAC': 's', 'TD3': '^'}
    
    for model, values in data.items():
        marker = markers.get(model, 'D')
        plt.plot(values['x'], values['y'], marker=marker, label=model.replace("_", " "), linewidth=2, markersize=8)
        
    plt.xlabel('Vehicle Density Scale')
    plt.ylabel('Average Access Delay (sec)')
    plt.title('Access Delay vs. Vehicle Density')
    plt.xticks([0.5, 1.0, 1.5, 2.0])
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/4_delay_vs_density.png", dpi=300)
    plt.close()
    print("Generated 4_delay_vs_density.png")

def plot_5_model_delay():
    """5. 각 모델별 종합 평균 딜레이 막대 그래프"""
    filepath = f"{DATA_DIR}/access_delay_vs_density.csv"
    if not os.path.exists(filepath):
        return
        
    model_delays = {}
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 3:
                model = row[1]
                delay = float(row[2])
                if model not in model_delays:
                    model_delays[model] = []
                model_delays[model].append(delay)
                
    models = list(model_delays.keys())
    avg_delays = [np.mean(model_delays[m]) for m in models]
    
    plt.figure(figsize=(8, 5))
    colors = ['blue' if 'Proposed' in m else 'gray' for m in models]
    
    plt.bar(models, avg_delays, color=colors, alpha=0.8, edgecolor='black')
    
    plt.xlabel('Models')
    plt.ylabel('Overall Average Access Delay (sec)')
    plt.title('Average Access Delay Comparison')
    
    # 텍스트로 값 표시
    for i, v in enumerate(avg_delays):
        plt.text(i, v + (max(avg_delays)*0.02), f"{v:.2f}s", ha='center', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/5_model_delay.png", dpi=300)
    plt.close()
    print("Generated 5_model_delay.png")

if __name__ == "__main__":
    print("=== Generating Result Plots & Tables ===")
    plot_1_reward_ablation_study()
    plot_2_learning_curves()
    generate_3_hardware_feasibility()
    plot_4_delay_vs_density()
    plot_5_model_delay()
    print(f"=== All results saved in {OUTPUT_DIR}/ directory ===")
