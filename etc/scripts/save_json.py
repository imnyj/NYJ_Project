import json

data = [
    {
        "type": "Conference",
        "title": "Posterior Augmented CVAE for Pedestrian Trajectory Prediction with Momentary Observation",
        "authors": ["Yuxuan Wu", "Le Wang", "Sanping Zhou", "Ning Ding", "Gang Hua"],
        "venue": "IEEE Transactions on Multimedia",
        "year": 2026,
        "doi": "10.1109/tmm.2026.3673507",
        "summary": "This paper develops a Conditional Variational Autoencoder (CVAE) architecture augmented with posterior information to predict trajectories under momentary observations. The model handles spatial-temporal uncertainty by learning a probabilistic latent space conditioned on short historical inputs, generating multimodal future paths. It represents a state-of-the-art ST-CVAE baseline capable of robust spatio-temporal inference even with limited sequence data."
    },
    {
        "type": "Conference",
        "title": "Time-Frequency Wavelet Transformer Forecasting for Hypersonic Glide Vehicle Trajectory Prediction",
        "authors": ["Marina Kurilova", "Howard Li"],
        "venue": "2026 IEEE Aerospace Conference",
        "year": 2026,
        "doi": "10.1109/aero66936.2026.11519972",
        "summary": "This paper proposes a trajectory prediction model for high-speed vehicles leveraging a Time-Frequency Wavelet Transformer architecture. By integrating wavelet transforms with attention mechanisms, the model effectively captures both time and frequency domain features of complex flight dynamics. This approach serves as a robust baseline for Transformer-based long-term trajectory forecasting under nonlinear conditions."
    },
    {
        "type": "Conference",
        "title": "UUV Trajectory Prediction Based on GRU Neural Network",
        "authors": ["Yue Liu", "Hongjian Wang", "Kai Zhang", "Jingfei Ren"],
        "venue": "2021 40th Chinese Control Conference (CCC)",
        "year": 2021,
        "doi": "10.23919/ccc52363.2021.9549995",
        "summary": "This study introduces a trajectory prediction method utilizing a Gated Recurrent Unit (GRU) neural network. The GRU-based framework is designed to process sequential movement data, efficiently learning temporal dependencies with lower computational overhead compared to traditional LSTMs. The proposed model provides a reliable baseline for time-series forecasting in navigation and mobility tasks."
    },
    {
        "type": "Conference",
        "title": "An Effective Driver Intention and Trajectory Prediction for Autonomous Vehicle based on LSTM",
        "authors": ["Fatimetou El Jili"],
        "venue": "Proceedings of the 13th International Conference on Agents and Artificial Intelligence",
        "year": 2021,
        "doi": "10.5220/0010321710901096",
        "summary": "The authors present a Long Short-Term Memory (LSTM) based framework for simultaneously predicting driver intention and vehicle trajectory in autonomous driving scenarios. The network learns historical motion states and environmental cues to forecast future positions and lane-changing behaviors. As a fundamental sequential model, it represents a standard LSTM baseline for vehicular mobility prediction."
    }
]

# IEEE Transactions on Multimedia is a Journal actually
data[0]["type"] = "Journal"
data[0]["journal"] = data[0]["venue"]
del data[0]["venue"]

with open("trajectory_baselines.json", "w") as f:
    json.dump(data, f, indent=4)
print("File saved successfully.")
