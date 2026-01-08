from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
from typing import List, Optional

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 경로 설정 
REFERENCE_DIR = Path("./speakers/wav")
GENERATED_BASE_DIR = Path("./generated_outputs")
RESULTS_FILE = Path("./review_results.json")

# 프론트엔드 빌드 파일 서빙 (React 빌드 후)
# app.mount("/static", StaticFiles(directory="build/static"), name="static")


class ReviewResults(BaseModel):
    kept: List[str]
    discarded: List[str]
    undecided: List[str]


@app.get("/")
async def read_root():
    """프론트엔드 HTML 반환"""
    html_file = Path("index.html")
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "index.html not found. Please create index.html in the same directory as server.py"}


@app.get("/api/generated-folders")
async def get_generated_folders():
    """Generated 폴더 안의 하위 폴더 목록 반환"""
    try:
        if not GENERATED_BASE_DIR.exists():
            return {"folders": []}
        
        folders = [f.name for f in GENERATED_BASE_DIR.iterdir() if f.is_dir()]
        folders.sort()
        
        return {"folders": folders}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/speakers")
async def get_speakers(folder: Optional[str] = None):
    """
    Reference 폴더에서 {sid}.wav 파일들을 읽고,
    각 sid에 해당하는 generated audio 파일들을 찾아 반환
    folder: generated 폴더 내의 하위 폴더명
    """
    try:
        # Reference 파일 찾기
        if not REFERENCE_DIR.exists():
            raise HTTPException(status_code=404, detail="Reference directory not found")
        
        reference_files = list(REFERENCE_DIR.glob("*.wav"))
        speakers = []
        
        # Generated 폴더 경로 설정
        if folder:
            generated_dir = GENERATED_BASE_DIR / folder
        else:
            # 폴더 지정 안하면 첫번째 폴더 사용
            subfolders = [f for f in GENERATED_BASE_DIR.iterdir() if f.is_dir()]
            if subfolders:
                generated_dir = sorted(subfolders)[0]
            else:
                generated_dir = GENERATED_BASE_DIR
        
        for ref_file in reference_files:
            sid = ref_file.stem  # 확장자 제거
            
            # Generated 파일 찾기 (패턴: *-{sid}-*.wav)
            generated_files = []
            if generated_dir.exists():
                for gen_file in generated_dir.glob("*.wav"):
                    # 파일명에서 sid 추출
                    parts = gen_file.stem.split('-')
                    if len(parts) >= 3 and parts[-2] == sid:
                        generated_files.append(gen_file.name)
            
            speakers.append({
                "sid": sid,
                "referenceAudio": ref_file.name,
                "generatedAudios": sorted(generated_files),
                "generatedFolder": generated_dir.name if folder else (generated_dir.name if generated_dir != GENERATED_BASE_DIR else "")
            })
        
        # sid로 정렬
        speakers.sort(key=lambda x: x["sid"])
        
        return {"speakers": speakers, "selectedFolder": folder or (generated_dir.name if generated_dir != GENERATED_BASE_DIR else "")}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audio/reference/{filename}")
async def get_reference_audio(filename: str):
    """Reference 오디오 파일 반환"""
    file_path = REFERENCE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav")


@app.get("/audio/generated/{filename}")
async def get_generated_audio(filename: str, folder: Optional[str] = None):
    """Generated 오디오 파일 반환"""
    if folder:
        file_path = GENERATED_BASE_DIR / folder / filename
    else:
        # 폴더 지정 안하면 모든 하위 폴더에서 찾기
        for subfolder in GENERATED_BASE_DIR.iterdir():
            if subfolder.is_dir():
                file_path = subfolder / filename
                if file_path.exists():
                    return FileResponse(file_path, media_type="audio/wav")
        file_path = GENERATED_BASE_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav")


@app.post("/api/save-results")
async def save_results(results: ReviewResults):
    """검토 결과를 서버에 저장"""
    try:
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results.dict(), f, indent=2, ensure_ascii=False)
        
        # 텍스트 파일로도 저장
        text_file = RESULTS_FILE.with_suffix('.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"# Keep Files ({len(results.kept)})\n")
            f.write('\n'.join(results.kept))
            f.write(f"\n\n# Discard Files ({len(results.discarded)})\n")
            f.write('\n'.join(results.discarded))
            f.write(f"\n\n# Undecided Files ({len(results.undecided)})\n")
            f.write('\n'.join(results.undecided))
        
        return {"message": "Results saved successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # 디렉토리 생성
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Reference directory: {REFERENCE_DIR.absolute()}")
    print(f"Generated base directory: {GENERATED_BASE_DIR.absolute()}")
    print(f"Results will be saved to: {RESULTS_FILE.absolute()}")
    print("\nStarting server at http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)