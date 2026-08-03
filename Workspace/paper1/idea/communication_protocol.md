# Event-Driven Protocol for Feature Extraction, Precaching, and Local Fine-Tuning

To ensure that the 30-dimensional snapshot vector ($\mathbf{X}_v$) exactly reflects the network state at the moment of the request ($t_0$), and to complete the lifecycle for dual-model fine-tuning, the RSUs and vehicles execute the following strictly on-demand communication sequence.

## 1. Content Request and Local Delivery (V2I)
**Packet:** `[INTEREST] <v, r_{cur}> (VID, CID, req_start_chunk_no, GPS_pos, GPS_speed, d_leader, v_leader, planned_route)`
**Packet:** `[DATA] <r_{cur}, v> (Chunks)`
- **Action:** Vehicle $v$ initiates a session by transmitting an `[INTEREST]` packet to $r_{cur}$. Following standard CCN procedures, $r_{cur}$ immediately begins delivering any locally available content via `[DATA]` packets. 
- **Data Management:** Simultaneously, $r_{cur}$ extracts the piggybacked kinematic sensor data and calculates the spatial variables based on GPS coordinates. The request metadata is stored in the `pending_request_table`.

## 2. Local State Extraction (Internal RSU)
- **Action:** Triggered by the `[INTEREST]`, $r_{cur}$ reads its own traffic signal controller and roadside sensors to extract current local metrics (`tls_c`, `tlt_c`, `q_{len,cur}`, `occ_{cur}`).

## 3. Next Intersection State Query (I2I)
**Packet:** `[INFO REQ] <r_{cur}, r_{nxt}> (VID)`
- **Action:** To predict `Dwell_Nxt`, $r_{cur}$ must acquire the state of the next intersection at time $t_0$. It sends an on-demand `[INFO REQ]` to $r_{nxt}$.

## 4. Neighboring Traffic Query and Reply (I2I)
**Packet:** `[INFO HELLO] <r_{nxt}, neighbor_rsus> ()`
**Packet:** `[INFO REP] <neighbor_rsus, r_{nxt}> (outbound_count)`
**Packet:** `[INFO REP] <r_{nxt}, r_{cur}> (tls_n, tlt_n, n_{nxt}, q_{len,nxt}, occ_{nxt}, n_{merge,nxt}, inbound_counts)`
- **Action:** Upon receiving the query, $r_{nxt}$ broadcasts an `[INFO HELLO]` packet to its adjacent RSUs to count incoming traffic. The neighbors reply with their outbound counts towards $r_{nxt}$.
- **Data Management:** $r_{nxt}$ aggregates these inbound counts ($n_{t,0} \dots n_{t,3}$), combines them with its local signal and queue data, and sends the final `[INFO REP]` back to $r_{cur}$. This fully assembles the 30-dimensional $\mathbf{X}_v$.

## 5. Inference and Precaching Execution (I2I)
**Packet:** `[PRECACHE REQ] <r_{cur}, r_{nxt}> (VID, CID, next_start_chunk_no, \hat{\tau}_{nxt})`
- **Action:** $r_{cur}$ feeds $\mathbf{X}_v$ into the ST-MBAN model to predict $(\hat{\tau}_{cur}, \hat{\tau}_{nxt})$. Based on $\hat{\tau}_{cur}$ and network bandwidth, $r_{cur}$ determines exactly how many chunks it can transmit before $v$ leaves its coverage, thus identifying the `next_start_chunk_no`.
- **Data Management:** $r_{cur}$ sends a `[PRECACHE REQ]` to $r_{nxt}$. Using the predicted $\hat{\tau}_{nxt}$, $r_{nxt}$ calculates the precise number of chunks it needs to fetch ($N_{nxt} = \hat{\tau}_{nxt} \times \frac{Rate}{Chunk\_Size}$) and proactively caches them from the Core Server before the vehicle arrives.

## 6. Ground Truth Feedback and Fine-Tuning (V2I/I2I)
**Packet:** `[RESULT] <v, r_{cur}> (VID, \tau_{cur}^{true}, \tau_{nxt}^{true})`
- **Action:** Vehicle $v$ internally monitors its actual entrance and exit times at both $r_{cur}$ and $r_{nxt}$. Upon leaving the coverage of $r_{nxt}$, the vehicle generates a `[RESULT]` packet containing the true dwell times and transmits it back to the original $r_{cur}$ (via multi-hop relay if necessary).
- **Data Management:** $r_{cur}$ receives the `[RESULT]` packet, looks up the original $\mathbf{X}_v$ from its `pending_request_table` using the `VID`, and pairs them to form a complete training sample $(\mathbf{X}_v, \tau_{cur}^{true}, \tau_{nxt}^{true})$. This sample is pushed into the `dataset_queue`. Once the queue reaches its threshold (e.g., 5,000 samples), $r_{cur}$ triggers the background shadow model for continuous fine-tuning.
