#!/usr/bin/env python3
"""본훈련의 베이스라인별 학습 상황을 한 표로 낸다.

    python3 etc/scripts/baseline_status.py                 # 사람이 읽는 표
    python3 etc/scripts/baseline_status.py --discord       # 디스코드용 짧은 형식

`runs/<arm>_seed<N>/lg/<MODEL>_progress.csv` 를 읽는다. 그 파일은 훈련이 에피소드마다
한 줄씩 덧붙이므로, 마지막 줄이 그 모델의 현재 상태이고 줄 수가 진행도다.

`best_reward_so_far` 를 쓰는 이유는 그것이 검증 에피소드에서 고른 값이고 `_best.pt` 의
근거이기 때문이다. 마지막 에피소드의 보상은 그 순간의 밀도에 좌우되므로 모델 간 비교에
쓸 수 없다. 밀도 스케줄이 5에서 35까지 순회하므로 같은 에피소드 번호라도 조건이 다르다.

읽기 전용이며 실행 중인 훈련에 영향을 주지 않는다.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path

CODER_DIR = Path(__file__).resolve().parents[2]
RUNS = CODER_DIR / "runs"

#: 훈련이 도는 순서. `run_all.py` 가 이 순서로 돌므로 표도 같은 순서를 쓴다.
#: 아직 시작하지 않은 모델을 "대기"로 보이려면 전체 목록이 필요하다.
MODEL_ORDER = [
    "PPO", "SAC", "TD3", "RES-MAPDDPG", "MA2HDQN",
    "I-HAMAPPO", "SPAM-D3QN", "HOORL", "MADDPG-MT",
]


def _key(name: str) -> str:
    """모델 이름을 비교용으로 정규화한다.

    진행 CSV 는 클래스 이름으로 쓰이므로 `RES-MAPDDPG` 가 `RESMAPDDPG` 로,
    `MADDPG-MT` 가 `MADDPGMT` 로 저장된다. 하이픈을 그대로 두고 비교하면 그 모델이
    끝났는데도 "대기 중"으로 보고된다. 2026-09-11 06:00 보고에서 실제로 그렇게 나왔고,
    RES-MAPDDPG 가 완료 03:04~05:30 인데 표에 없었다.
    """
    return name.replace("-", "").replace("_", "").upper()


def _f(row: dict, key: str):
    """CSV 칸을 float 으로. 비었거나 숫자가 아니면 None."""
    v = (row.get(key) or "").strip()
    if not v:
        return None
    try:
        x = float(v)
    except ValueError:
        return None
    return None if math.isnan(x) else x


def read_run(run_dir: Path) -> dict:
    """한 실행 디렉터리의 모델별 상태를 모은다."""
    lg = run_dir / "lg"
    out: dict[str, dict] = {}
    if not lg.is_dir():
        return out

    for csv_path in lg.glob("*_progress.csv"):
        model = _key(csv_path.name[: -len("_progress.csv")])
        try:
            with csv_path.open(newline="") as fh:
                rows = list(csv.DictReader(fh))
        except OSError:
            continue
        if not rows:
            continue
        last = rows[-1]
        out[model] = {
            "episodes": len(rows),
            "episode": _f(last, "episode"),
            "global_step": _f(last, "global_step"),
            "density": _f(last, "density"),
            "best": _f(last, "best_reward_so_far"),
            "val": _f(last, "val_reward_per_sec"),
            "loss": _f(last, "mean_loss"),
            "updates": _f(last, "grad_updates_total"),
            "swaps": _f(last, "swap_count"),
            "delta": _f(last, "mean_delta_actual"),
            "mtime": csv_path.stat().st_mtime,
        }
    return out


def fmt(x, spec="8.4f", dash="       -"):
    return dash if x is None else format(x, spec)


def render(run_dir: Path, discord: bool) -> str:
    st = read_run(run_dir)
    if not st:
        return f"{run_dir.name}: 아직 진행 기록이 없습니다."

    done = [m for m in MODEL_ORDER if _key(m) in st and st[_key(m)]["episodes"] >= 100]
    running = [m for m in MODEL_ORDER if _key(m) in st and st[_key(m)]["episodes"] < 100]
    waiting = [m for m in MODEL_ORDER if _key(m) not in st]

    lines = []
    if discord:
        lines.append(f"**{run_dir.name}**  완료 {len(done)}/9")
        lines.append("```")
        lines.append(f"{'모델':<12}{'에피':>7}{'최고보상':>11}{'손실':>9}{'밀도':>6}")
        for m in MODEL_ORDER:
            s = st.get(_key(m))
            if s is None:
                continue
            lines.append(
                f"{m:<12}{s['episodes']:>4}/100"
                f"{fmt(s['best'], '11.4f', '          -')}"
                f"{fmt(s['loss'], '9.4f', '        -')}"
                f"{fmt(s['density'], '6.0f', '     -')}"
            )
        if waiting:
            lines.append(f"대기: {', '.join(waiting)}")
        lines.append("```")
        return "\n".join(lines)

    lines.append(f"[{run_dir.name}]  완료 {len(done)}/9, 진행 {len(running)}, 대기 {len(waiting)}")
    lines.append("")
    lines.append(
        f"  {'모델':<13}{'에피소드':>9}{'스텝':>9}{'최고보상':>11}"
        f"{'검증보상':>11}{'손실':>9}{'갱신':>8}{'스왑':>6}{'Δ평균':>8}{'밀도':>6}"
    )
    lines.append("  " + "-" * 92)
    for m in MODEL_ORDER:
        s = st.get(_key(m))
        if s is None:
            continue
        lines.append(
            f"  {m:<13}{s['episodes']:>5}/100"
            f"{fmt(s['global_step'], '9.0f', '        -')}"
            f"{fmt(s['best'], '11.4f', '          -')}"
            f"{fmt(s['val'], '11.4f', '          -')}"
            f"{fmt(s['loss'], '9.4f', '        -')}"
            f"{fmt(s['updates'], '8.0f', '       -')}"
            f"{fmt(s['swaps'], '6.0f', '     -')}"
            f"{fmt(s['delta'], '8.2f', '       -')}"
            f"{fmt(s['density'], '6.0f', '     -')}"
        )
    if waiting:
        lines.append("")
        lines.append(f"  대기 중: {', '.join(waiting)}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--discord", action="store_true",
                    help="디스코드로 보낼 짧은 형식")
    ap.add_argument("--run", default=None,
                    help="실행 디렉터리 이름. 생략하면 runs/ 아래 전부")
    args = ap.parse_args()

    if not RUNS.is_dir():
        print("runs/ 가 없습니다.", file=sys.stderr)
        return 1

    dirs = [RUNS / args.run] if args.run else sorted(
        d for d in RUNS.iterdir() if d.is_dir()
    )
    if not dirs:
        print("실행 디렉터리가 없습니다.", file=sys.stderr)
        return 1

    print("\n\n".join(render(d, args.discord) for d in dirs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
