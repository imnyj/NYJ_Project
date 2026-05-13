from __future__ import annotations
import subprocess, time, threading, os, platform, sys
from datetime import datetime, timedelta

# ── 설정 상수 ────────────────────────────────────────────
TOTAL_EPISODES  = 30
SIM_MAX_STEPS   = 3600
RESTART_DELAY   = 10
EXIT_FLAG_FILE  = "exit.flag"
PROGRESS_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sim_progress")
POLL_MS         = 1000   # 상태 갱신 주기 (ms, GUI) / 폴 주기 (s, CLI)

IS_LINUX = platform.system() != "Windows"

# ── OS별 실행 경로 ─────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
if IS_LINUX:
    TARGET_FILE = os.path.join(_BASE, "dataset_scenario.py")
    PYTHON_EXE  = "python3"
    _PROC_ENV   = {**os.environ, "PYTHONPATH": ""}   # PYTHONPATH 초기화
else:
    TARGET_FILE = "SumoNetSim1.1.5\\dataset_scenario.py"
    PYTHON_EXE  = "/home/imnyj/venv/bin/python3"
    _PROC_ENV   = None   # 환경변수 상속

# ── 공유 상태 ─────────────────────────────────────────────
_ep_done    = 0
_sim_active = False
_t_start    = None
_ep_times: list[float] = []

# ── 유틸 ─────────────────────────────────────────────────
def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _fmt_hms(sec: float) -> str:
    h, rem = divmod(int(max(0, sec)), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def _read_step() -> int:
    try:
        with open(PROGRESS_FILE, "r") as f:
            return max(0, min(SIM_MAX_STEPS, int(f.read().strip())))
    except Exception:
        return 0

def _calc_times() -> tuple[str, str, str]:
    """(소요, 남은시간, 완료예정) 문자열 반환"""
    elapsed = _fmt_hms(time.time() - _t_start) if _t_start else "--:--:--"
    if _t_start and _ep_times:
        avg     = sum(_ep_times) / len(_ep_times)
        frac    = (_read_step() / SIM_MAX_STEPS) if _sim_active else 0.0
        eta_sec = max(0, avg * (TOTAL_EPISODES - _ep_done - frac))
        remain  = _fmt_hms(eta_sec)
        end_t   = (datetime.now() + timedelta(seconds=eta_sec)).strftime("%m/%d %H:%M:%S")
    else:
        remain = "--:--:--"
        end_t  = "--:--:--"
    return elapsed, remain, end_t


# ══════════════════════════════════════════════════════════
#  LINUX CLI 모드
# ══════════════════════════════════════════════════════════
if IS_LINUX:
    _print_lock   = threading.Lock()
    _status_len   = 0    # 현재 터미널에 출력된 상태 라인 길이

    def _erase_status() -> None:
        global _status_len
        if _status_len:
            sys.stdout.write(f"\r{' ' * _status_len}\r")
            _status_len = 0

    def _write_status(ep_done: int, step: int) -> None:
        global _status_len
        elapsed, remain, end_t = _calc_times()
        ep_pct   = ep_done / TOTAL_EPISODES * 100
        step_pct = step / SIM_MAX_STEPS * 100
        avg_str  = f"{sum(_ep_times)/len(_ep_times):.0f}s/ep" if _ep_times else "---"
        line = (
            f"  Ep {ep_done:>2}/{TOTAL_EPISODES} ({ep_pct:4.1f}%)"
            f"  Step {step:>4}/{SIM_MAX_STEPS} ({step_pct:4.1f}%)"
            f"  |  소요 {elapsed}"
            f"  남은 {remain}"
            f"  완료예정 {end_t}"
            f"  [{avg_str}]"
        )
        sys.stdout.write(f"\r{line}")
        sys.stdout.flush()
        _status_len = len(line)

    def cli_print(*args) -> None:
        """로그 출력: 상태 라인 지우고 메시지 출력 후 상태 재출력"""
        text = " ".join(str(a) for a in args)
        step = _read_step() if _sim_active else 0
        with _print_lock:
            _erase_status()
            print(text, flush=True)
            if _t_start:
                _write_status(_ep_done, step)

    def _cli_poll() -> None:
        """백그라운드: 1초마다 상태 라인 갱신"""
        while True:
            time.sleep(1)
            if _t_start:
                step = _read_step() if _sim_active else 0
                with _print_lock:
                    _write_status(_ep_done, step)

    print_fn = cli_print


# ══════════════════════════════════════════════════════════
#  WINDOWS GUI 모드
# ══════════════════════════════════════════════════════════
else:
    import tkinter as tk
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText

    window = tk.Tk()
    window.title("SumoNetSim Watchdog Runner")
    window.geometry("720x600")
    window.resizable(True, True)

    tk.Label(window, text="SumoNetSim Watchdog Runner",
             font=("Arial", 14, "bold")).pack(pady=(10, 2))

    # ── Progress 프레임
    pf = tk.LabelFrame(window, text=" Progress ",
                       font=("Arial", 10, "bold"), padx=12, pady=8)
    pf.pack(padx=12, pady=4, fill="x")
    pf.columnconfigure(1, weight=1)

    ep_var      = tk.StringVar(value=f"Episode   0 / {TOTAL_EPISODES}")
    step_var    = tk.StringVar(value=f"Step      0 / {SIM_MAX_STEPS}")
    elapsed_var = tk.StringVar(value="소요:       --:--:--")
    remain_var  = tk.StringVar(value="남은 시간:  --:--:--")
    endtime_var = tk.StringVar(value="완료 예정:  --:--:--")

    tk.Label(pf, textvariable=ep_var, font=("Consolas", 10),
             anchor="w", width=22).grid(row=0, column=0, sticky="w")
    ep_bar = ttk.Progressbar(pf, orient="horizontal",
                             maximum=TOTAL_EPISODES, mode="determinate")
    ep_bar.grid(row=0, column=1, padx=(8, 0), pady=4, sticky="we")

    tk.Label(pf, textvariable=step_var, font=("Consolas", 10),
             anchor="w", width=22).grid(row=1, column=0, sticky="w")
    step_bar = ttk.Progressbar(pf, orient="horizontal",
                               maximum=SIM_MAX_STEPS, mode="determinate")
    step_bar.grid(row=1, column=1, padx=(8, 0), pady=4, sticky="we")

    tf = tk.Frame(pf)
    tf.grid(row=2, column=0, columnspan=2, sticky="we", pady=(2, 0))
    tk.Label(tf, textvariable=elapsed_var, font=("Consolas", 9),
             fg="#333333", anchor="w").pack(side="left", padx=(0, 20))
    tk.Label(tf, textvariable=remain_var,  font=("Consolas", 9),
             fg="#333333", anchor="w").pack(side="left", padx=(0, 20))
    tk.Label(tf, textvariable=endtime_var, font=("Consolas", 9),
             fg="#555555", anchor="w").pack(side="left")

    # ── 로그 박스
    log_box = ScrolledText(window, height=18, width=80,
                           state="disabled", wrap="word", font=("Consolas", 9))
    log_box.pack(padx=10, pady=6, fill="both", expand=True)

    def gui_print(*args) -> None:
        text = " ".join(str(a) for a in args)
        def _append():
            log_box.config(state="normal")
            log_box.insert(tk.END, text + "\n")
            log_box.see(tk.END)
            log_box.config(state="disabled")
        window.after(0, _append)

    def _update_ui(ep_done: int, step: int) -> None:
        ep_var.set(  f"Episode {ep_done:>3} / {TOTAL_EPISODES}")
        step_var.set(f"Step  {step:>5} / {SIM_MAX_STEPS}")
        ep_bar["value"]   = ep_done
        step_bar["value"] = step

        elapsed, remain, end_t = _calc_times()
        elapsed_var.set(f"소요:       {elapsed}")
        remain_var.set( f"남은 시간:  {remain}")
        endtime_var.set(f"완료 예정:  {end_t}")

    def _poll() -> None:
        step = _read_step() if _sim_active else 0
        window.after(0, lambda s=step: _update_ui(_ep_done, s))
        window.after(POLL_MS, _poll)

    print_fn = gui_print


# ── 감시 루프 (공통) ──────────────────────────────────────
def _watchdog() -> None:
    global _ep_done, _sim_active, _t_start, _ep_times

    _t_start = time.time()
    print_fn(f"[{ts()}][INFO] 감시 시작: 총 {TOTAL_EPISODES}에피소드 예정")
    print_fn(f"[{ts()}][INFO] Python: {PYTHON_EXE}")
    print_fn(f"[{ts()}][INFO] Target: {TARGET_FILE}")

    ep = 0
    while _ep_done < TOTAL_EPISODES:
        ep += 1

        if os.path.exists(EXIT_FLAG_FILE):
            print_fn(
                f"[{ts()}][INFO] 종료 예약 감지. "
                f"에피소드 {_ep_done}/{TOTAL_EPISODES} 완료 후 중단."
            )
            try: os.remove(EXIT_FLAG_FILE)
            except Exception: pass
            break

        try:
            with open(PROGRESS_FILE, "w") as f: f.write("0")
        except Exception: pass

        _sim_active = True
        if not IS_LINUX:
            window.after(0, lambda d=_ep_done: _update_ui(d, 0))
        print_fn(f"[{ts()}][INFO] ▶ Episode {_ep_done + 1}/{TOTAL_EPISODES} 시작")
        t_ep_start = time.time()

        try:
            proc = subprocess.Popen(
                [PYTHON_EXE, TARGET_FILE],
                stdout=None, stderr=None,
                env=_PROC_ENV,
            )
            proc.wait()
            rc = proc.returncode
        except Exception as ex:
            print_fn(f"[{ts()}][CRITICAL] 프로세스 오류: {ex}")
            rc = -1

        ep_elapsed = time.time() - t_ep_start
        _sim_active = False

        if rc == 0:
            _ep_done += 1
            _ep_times.append(ep_elapsed)
            print_fn(
                f"[{ts()}][INFO] ✓ Episode {_ep_done}/{TOTAL_EPISODES} 완료 "
                f"(소요 {ep_elapsed:.0f}s)"
            )
            if not IS_LINUX:
                window.after(0, lambda d=_ep_done: _update_ui(d, SIM_MAX_STEPS))
        else:
            print_fn(
                f"[{ts()}][WARNING] Episode {ep} 비정상 종료 (rc={rc}). "
                f"재시도합니다. (완료 카운트: {_ep_done})"
            )
            if not IS_LINUX:
                window.after(0, lambda d=_ep_done: _update_ui(d, 0))

        if _ep_done < TOTAL_EPISODES:
            print_fn(f"[{ts()}][INFO] {RESTART_DELAY}초 후 다음 에피소드 시작...")
            time.sleep(RESTART_DELAY)

    total_min = (time.time() - _t_start) / 60
    print_fn(
        f"[{ts()}][INFO] ===== 전체 {TOTAL_EPISODES}에피소드 완료 ===== "
        f"(총 소요 {total_min:.1f}분)"
    )
    if not IS_LINUX:
        window.after(0, lambda: _update_ui(TOTAL_EPISODES, SIM_MAX_STEPS))
        window.after(0, lambda: remain_var.set( "남은 시간:  완료!"))
        window.after(0, lambda: endtime_var.set("완료 예정:  완료!"))
        window.after(0, lambda: run_button.config(state="normal"))


# ── 진입점 ────────────────────────────────────────────────
if IS_LINUX:
    print(f"[{ts()}][INFO] Linux CLI 모드  (Ctrl+C로 즉시 종료 / exit.flag 파일 생성으로 에피소드 완료 후 종료)")
    print()
    threading.Thread(target=_cli_poll, daemon=True).start()
    try:
        _watchdog()
    except KeyboardInterrupt:
        print()
        print(f"[{ts()}][INFO] 사용자 중단 (Ctrl+C). 완료된 에피소드: {_ep_done}/{TOTAL_EPISODES}")
        sys.exit(0)

else:
    # Windows: 버튼 UI 생성 후 메인루프
    def run_watchdog():
        run_button.config(state="disabled")
        threading.Thread(target=_watchdog, daemon=True).start()

    def schedule_exit():
        open(EXIT_FLAG_FILE, "w").close()
        gui_print(f"[{ts()}][INFO] 종료 예약 설정됨. 현재 에피소드 완료 후 중단됩니다.")

    btn_frame = tk.Frame(window)
    btn_frame.pack(pady=6)

    run_button = tk.Button(
        btn_frame, text=f"▶ Run  ({TOTAL_EPISODES} Episodes)",
        command=run_watchdog,
        bg="#5cb85c", fg="white", font=("Arial", 12, "bold"), width=20,
    )
    run_button.grid(row=0, column=0, padx=10)

    exit_button = tk.Button(
        btn_frame, text="⏹ Schedule Exit",
        command=schedule_exit,
        bg="#d9534f", fg="white", font=("Arial", 12, "bold"), width=16,
    )
    exit_button.grid(row=0, column=1, padx=10)

    window.after(POLL_MS, _poll)
    window.mainloop()
