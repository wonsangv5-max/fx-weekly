"""
FX Weekly GitHub Pages 업로드 스크립트
────────────────────────────────────
사용법:
    python upload.py

동작:
    1. output 폴더에서 가장 최신 FX_Weekly_*.docx 파일 읽기
    2. HTML로 변환
    3. GitHub Pages에 자동 업로드
    4. https://wonsangv5-max.github.io/fx-weekly/ 에서 확인

필요 패키지:
    pip install python-docx requests

환경변수:
    GITHUB_TOKEN    GitHub Personal Access Token (필수)
"""

import os, re, base64, json
from pathlib import Path
from datetime import datetime
from docx import Document
import requests

# ── 설정 ──────────────────────────────────────────────────────
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER   = "wonsangv5-max"
GITHUB_REPO   = "fx-weekly"
GITHUB_BRANCH = "main"
OUTPUT_DIR    = Path(os.environ.get("FX_OUTPUT_DIR", "./output"))
API_BASE      = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents"


# ── 최신 docx 파일 찾기 ───────────────────────────────────────
def find_latest_docx() -> Path:
    files = sorted(OUTPUT_DIR.glob("FX_Weekly_*.docx"), reverse=True)
    if not files:
        raise FileNotFoundError(f"output 폴더에 FX_Weekly_*.docx 파일이 없습니다: {OUTPUT_DIR}")
    return files[0]


# ── docx → HTML 변환 ──────────────────────────────────────────
def docx_to_html(docx_path: Path) -> str:
    doc = Document(docx_path)
    date_str = datetime.today().strftime("%Y.%m.%d")

    lines_html = []
    for para in doc.paragraphs:
        if not para.text.strip():
            continue

        # 스타일별 HTML 태그
        if para.text.startswith("FX Weekly"):
            lines_html.append(f'<h1 class="title">{para.text}</h1>')
        elif re.match(r'^\(\d{4}\.\d{2}\.\d{2}', para.text):
            lines_html.append(f'<p class="meta">{para.text}</p>')
        elif re.match(r'^\[주간 흐름 요약\]', para.text):
            lines_html.append(f'<div class="summary-title">{para.text}</div>')
        elif re.match(r'^(원/달러|DXY|주간 흐름):', para.text):
            label, rest = para.text.split(":", 1)
            lines_html.append(
                f'<p class="summary-line"><span class="summary-label">{label}:</span>{rest}</p>'
            )
        elif re.match(r'^\d+\. ', para.text):
            lines_html.append(f'<h2 class="section">{para.text}</h2>')
        elif para.style.name == 'List Paragraph':
            # 일별 내용: 빨간색 run 처리
            inner_html = ""
            for run in para.runs:
                text = run.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                color_elem = run._element.find(
                    './/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color'
                )
                is_red = (color_elem is not None and
                          color_elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') == 'FF0000')
                is_bold = run.font.bold
                if is_red:
                    inner_html += f'<span class="fact">{text}</span>'
                elif is_bold:
                    inner_html += f'<strong>{text}</strong>'
                else:
                    inner_html += text
            # 줄바꿈 처리 (\n → <br>)
            inner_html = inner_html.replace("\n", "<br>")
            lines_html.append(f'<li>{inner_html}</li>')
        else:
            lines_html.append(f'<p>{para.text}</p>')

    # li 태그를 ul로 감싸기
    html_body = []
    in_ul = False
    for line in lines_html:
        if line.startswith("<li>"):
            if not in_ul:
                html_body.append("<ul>")
                in_ul = True
        else:
            if in_ul:
                html_body.append("</ul>")
                in_ul = False
        html_body.append(line)
    if in_ul:
        html_body.append("</ul>")

    body_content = "\n".join(html_body)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FX Weekly — {date_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Malgun Gothic', '맑은 고딕', sans-serif;
    background: #f4f6f9;
    color: #222;
    padding: 32px 16px;
    font-size: 14px;
    line-height: 1.7;
  }}
  .container {{
    max-width: 860px;
    margin: 0 auto;
    background: #fff;
    padding: 48px 56px;
    box-shadow: 0 2px 24px rgba(0,0,0,0.10);
  }}
  h1.title {{
    font-size: 28px;
    font-weight: 800;
    color: #1B3A6B;
    border-bottom: 4px solid #1B3A6B;
    padding-bottom: 10px;
    margin-bottom: 6px;
  }}
  .meta {{
    font-size: 12px;
    color: #888;
    margin-bottom: 24px;
  }}
  .summary-title {{
    font-size: 13px;
    font-weight: 700;
    color: #1B3A6B;
    background: #EFF4FB;
    padding: 8px 14px;
    margin: 16px 0 6px;
    border-left: 4px solid #1B3A6B;
  }}
  .summary-line {{
    font-size: 13px;
    padding: 3px 14px;
    color: #333;
  }}
  .summary-label {{
    font-weight: 700;
    color: #1B3A6B;
    margin-right: 4px;
  }}
  h2.section {{
    font-size: 15px;
    font-weight: 700;
    color: #1B3A6B;
    margin: 28px 0 10px;
    padding-bottom: 4px;
    border-bottom: 2px solid #1B3A6B;
  }}
  ul {{
    list-style: disc;
    padding-left: 20px;
  }}
  li {{
    font-size: 13px;
    margin-bottom: 14px;
    color: #333;
    padding-left: 4px;
  }}
  .fact {{
    color: #CC2222;
    font-weight: 600;
  }}
  strong {{
    font-weight: 700;
  }}
  .footer {{
    margin-top: 32px;
    font-size: 11px;
    color: #aaa;
    border-top: 1px solid #eee;
    padding-top: 12px;
  }}
  @media (max-width: 600px) {{
    .container {{ padding: 24px 20px; }}
    h1.title {{ font-size: 22px; }}
  }}
</style>
</head>
<body>
<div class="container">
{body_content}
<div class="footer">※ 본 보고서는 공개된 뉴스를 바탕으로 작성된 정보 제공용 자료입니다. 투자 판단의 근거로 활용 시 별도 전문가 확인을 권장합니다.</div>
</div>
</body>
</html>"""


# ── GitHub 파일 업로드 ────────────────────────────────────────
def github_upload(filename: str, content: str, commit_msg: str):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"{API_BASE}/{filename}"

    # 기존 파일 SHA 확인 (업데이트 시 필요)
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": commit_msg,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, data=json.dumps(payload))
    if r.status_code in (200, 201):
        return True
    else:
        raise Exception(f"업로드 실패: {r.status_code} {r.text[:200]}")


# ── 인덱스 페이지 생성 ────────────────────────────────────────
def build_index(reports: list) -> str:
    items = ""
    for fname, date_str in reports:
        items += f'<li><a href="{fname}">{date_str} FX Weekly</a></li>\n'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FX Weekly Reports</title>
<style>
  body {{ font-family: 'Malgun Gothic', sans-serif; background: #f4f6f9;
         padding: 40px 20px; color: #222; }}
  .container {{ max-width: 600px; margin: 0 auto; background: #fff;
               padding: 40px 48px; box-shadow: 0 2px 24px rgba(0,0,0,0.10); }}
  h1 {{ font-size: 24px; color: #1B3A6B; border-bottom: 3px solid #1B3A6B;
        padding-bottom: 10px; margin-bottom: 24px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
  a {{ color: #1B3A6B; text-decoration: none; font-weight: 600; font-size: 14px; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 FX Weekly Reports</h1>
  <ul>
{items}
  </ul>
</div>
</body>
</html>"""


# ── 기존 보고서 목록 가져오기 ─────────────────────────────────
def get_existing_reports() -> list:
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    r = requests.get(API_BASE, headers=headers)
    if r.status_code != 200:
        return []
    files = [f["name"] for f in r.json() if re.match(r'FX_Weekly_\d{8}\.html', f["name"])]
    result = []
    for f in sorted(files, reverse=True):
        m = re.search(r'(\d{4})(\d{2})(\d{2})', f)
        if m:
            date_str = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
            result.append((f, date_str))
    return result


# ── 메인 ──────────────────────────────────────────────────────
def main():
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN 환경변수가 설정되지 않았습니다.")
        print("   set GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx")
        return

    # 최신 docx 찾기
    docx_path = find_latest_docx()
    print(f"📄 파일 발견: {docx_path.name}")

    # HTML 변환
    print("🔄 HTML 변환 중...")
    html_content = docx_to_html(docx_path)

    # 날짜 추출
    m = re.search(r'(\d{8})', docx_path.name)
    date_str_raw = m.group(1) if m else datetime.today().strftime("%Y%m%d")
    date_str = f"{date_str_raw[:4]}.{date_str_raw[4:6]}.{date_str_raw[6:]}"
    html_filename = f"FX_Weekly_{date_str_raw}.html"

    # 보고서 업로드
    print(f"⬆️  GitHub 업로드 중: {html_filename}")
    github_upload(html_filename, html_content, f"Add FX Weekly {date_str}")

    # 인덱스 업데이트
    print("📋 인덱스 페이지 업데이트 중...")
    existing = get_existing_reports()
    # 현재 파일이 목록에 없으면 추가
    if not any(f == html_filename for f, _ in existing):
        existing.insert(0, (html_filename, date_str))
    index_html = build_index(existing)
    github_upload("index.html", index_html, f"Update index for {date_str}")

    print(f"\n✅ 업로드 완료!")
    print(f"🌐 보고서: https://{GITHUB_USER}.github.io/{GITHUB_REPO}/{html_filename}")
    print(f"📋 목록:   https://{GITHUB_USER}.github.io/{GITHUB_REPO}/")


if __name__ == "__main__":
    main()
