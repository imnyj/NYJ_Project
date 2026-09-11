* delay와 wasted traffic 계산 알고리즘

delay, traffic = 0, 0

cur_diff = cur_true - cur_pred
cur_dif_chunk = int(abs(cur_diff) * 0.75) / 2 # WAVE 기준 6 Mbps = 0.75 MB/sec, chunk 당 2MB
nxt_diff = nxt_true - nxt_pred
nxt_dif_chunk = int(abs(nxt_diff) * 0.75) / 2 # WAVE 기준 6 Mbps = 0.75 MB/sec, chunk 당 2MB

# [1, 2, 3, 4, 5] [6, 7, 8, 9, 10]

if(cur_diff > 0) # R_cur에서 예상보다 늦게 나갔다. [1, 2, 3, 4, 5, +6] [-6, 7, 8, 9, 10, +11]
    # R_cur에서 준비되지 않은 chunks들을 가져오느라 access delay가 발생한다.
    # R_nxt에 precache 해둔 chunks가 차이 수 만큼 버려진다.
     
    traffic +=  cur_dif_chunk * 2
    delay += cur_dif_chunk * 0.01 # chunk당 10ms delay

    if(nxt_diff > 0) # R_nxt에서 예상보다 늦게 나갔다. [7, 8, 9, 10, +11, +12]
        # R_nxt에서 더 오래 머물면서 access delay 발생 
        delay += nxt_dif_chunk * 0.01
        # R_cur에서 전달한 만큼 R_nxt에서 준비되지 않은 뒷 부분의 chunk를 더 보내느라 access delay 발생
        delay += cur_dif_chunk * 0.01
    else
        # R_nxt에서 일찍 나가면서 준비해둔 precached chunks 버려짐 [7, 8, 9, ?10, ?11]
        # R_cur에서 전달한 맘큼 R_nxt에서 준비되지 않은 뒷 부분을 보내는 데도 그보다 빨리나갈 수도 있음.
        if(cur_diff + nxt_diff > 0)
            delay += (cur_dif_chunk - nxt_dif_chunk) * 0.01
        else
            traffic += (nxt_dif_chunk - cur_cif_chunk) * 2
else # R_cur에서 예상 보다 빨리 나갔다. [1, 2, 3, 4, -5] [+5, 6, 7, 8, 9, ?10]
    # R_nxt에서 준비 되지 않은 chunks를 줘야 해서 access delay 발생
    # R_nxt에서 그 만큼 시간이 부족해짐
    
    delay += cur_dif_chunk * 0.01

    if(nxt_diff > 0) # R_nxt에서 예상보다 늦게 나갔다. [5, 6, 7, 8, 9, ?10]
        # precached chunks 보다 늦게 나가면 delay 발생
        delay += max(nxt_dif_chunk - cur_dif_chunk, 0) * 0.01
        # precached chunks 보다 빨리 나가면 wasted traffic 발생
        traffic += max(cur_dif_chunk - nxt_dif_chunk, 0) * 2
    else # R_nxt에서 예상보다 빨리 나갔다. [5, 6, 7, 8, ?9, -10]
        traffic += max(cur_dif_chunk + nxt_dif_chunk, 0) * 2
