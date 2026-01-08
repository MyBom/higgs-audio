import json
import subprocess
from pathlib import Path
import argparse

# --- 파라미터 처리 ---
parser = argparse.ArgumentParser(description="필터링된 오디오를 ffmpeg로 변환해서 저장")
parser.add_argument("wakeword_tag", type=str, help="처리할 wakeword 태그 이름")
args = parser.parse_args()

wakeword_tag = args.wakeword_tag
json_path = "./review_results.json"

input_dir = Path(f"generated_outputs/{wakeword_tag}")
output_dir = Path("filtered_dataset") / wakeword_tag
output_dir.mkdir(parents=True, exist_ok=True)

# --- JSON 읽기 ---
with open(json_path, "r") as f:
    data = json.load(f)

kept_files = data.get("kept", [])

# --- ffmpeg 변환 ---
for fname in kept_files:
    input_file = input_dir / fname
    output_file = output_dir / fname

    if not input_file.exists():
        print(f"[WARNING] 파일 없음: {input_file}")
        continue

    cmd = [
        "ffmpeg",
        "-y",            # 덮어쓰기 허용
        "-i", str(input_file),
        "-ar", "16000",  # 샘플레이트 16kHz
        str(output_file)
    ]

    print(f"Processing: {fname}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] 변환 실패: {fname}")
        print(result.stderr)

print("파일 변환 완료.")
