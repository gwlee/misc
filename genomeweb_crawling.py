import os
import time
import re
import shutil
import undetected_chromedriver as uc
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

today = datetime.now()
sevenday_ago = today - timedelta(days=7)

# 1. 파일들을 최종 저장할 현재 폴더 내의 상대 경로 지정
TARGET_FOLDER_NAME = today.strftime('%Y%m%d')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
SAVE_FOLDER_PATH = os.path.join(CURRENT_DIR, TARGET_FOLDER_NAME)

# 브라우저가 최초로 다운로드할 기본 다운로드 폴더 경로 탐색
CHROME_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

def create_driver():
    """보안 차단 및 여러 파일 다운로드 알림창을 자동으로 허용하는 크롬 드라이버를 생성합니다."""
    options = uc.ChromeOptions()
    options.add_argument('--window-size=800,640')
    
    # [수정된 부분] 크롬 창이 보이지 않게 백그라운드(Headless)로 실행되도록 설정
    #options.add_argument('--headless=new')
    
    prefs = {
        "download.default_directory": CHROME_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1 
    }
    options.add_experimental_option("prefs", prefs)

    # [수정된 부분] headless=True 파라미터 추가
    #driver = uc.Chrome(options=options, version_main=148, headless=True)
    driver = uc.Chrome(options=options, version_main=148)
    return driver

def get_main_page_articles(driver, main_url):
    """메인 페이지에서 기사 상세 링크 수집 - 첫 화면의 모든 기사를 수집"""
    print(f"[{main_url}] 접속 중...")
    try:
        driver.get(main_url)
        # 백그라운드 실행 시 로그인은 이미 세션에 저장되어 있어야 합니다.
        print("💡 [안내] 10초 대기 중입니다. (Headless 모드 실행 중)")
        time.sleep(10) 
        
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        article_links = set()
        
        # === 방법 1: 기사 카드의 제목 링크 추출 (가장 정확함) ===
        heading_links = soup.find_all("a", class_="card__heading-link")
        for a_tag in heading_links:
            href = a_tag.get("href", "")
            if href:
                full_url = urljoin(main_url, href)
                article_links.add(full_url)
                print(f'[카드 제목] 링크 확인: {full_url}')
        
        # === 방법 2: 패턴 기반 필터링 (Fallback) ===
        if not article_links:
            print("[경고] card__heading-link 클래스를 찾지 못했습니다. 패턴 기반 필터링을 시도합니다.")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                
                if href.startswith("http") and "genomeweb.com" not in href:
                    continue
                
                skip_patterns = [
                    "/user", "/login", "/logout", "/subscribe", "/rss", "/sitemap",
                    "/about", "/advertise", "/contact", "/faq", "/jobs",
                    "/privacy", "/terms", "/search", "/elastic-search",
                    "/node/", "/taxonomy/term/", "/resources/webinars",
                    "/resources/white-papers", "/resources/jobs",
                    "/resources/new-product", "/resources/people-news",
                    "/resources/sponsored", "/topic/", "/my-topics",
                    "/my-stuff", "/user-dashboard", "/request-premium-quote",
                    "/#", "javascript:", "mailto:", "/breaking-news?"
                ]
                
                if any(pattern in href.lower() for pattern in skip_patterns):
                    continue
                
                path_parts = href.strip('/').split('/')
                if len(path_parts) >= 2 and len(path_parts[1]) > 3:
                    full_url = urljoin(main_url, href)
                    article_links.add(full_url)
                    print(f'[패턴 매칭] 링크 확인: {full_url}')
        
        unique_links = sorted(list(article_links))
        print(f"\n총 {len(unique_links)}개의 고유 기사 링크를 수집했습니다.")
        
        return unique_links
        
    except Exception as e:
        print(f"메인 페이지 로딩 중 오류 발생: {e}")
        return []

def clean_filename(url):
    """URL 기반 안전한 파일명 생성"""
    path = url.split('.com/')[-1]
    clean_path = re.sub(r'[^a-zA-Z0-9_\-]', '_', path)
    if len(clean_path) > 100:
        clean_path = clean_path[:100]
    return f"{clean_path}.html"

def browser_save_link_as(driver, url, filename):
    """브라우저 내부에서 우클릭 저장 명령을 내립니다."""
    js_script = f"""
    fetch("{url}")
      .then(response => response.text())
      .then(text => {{
        const blob = new Blob([text], {{type: "text/html"}});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "{filename}";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }})
      .catch(err => console.error("다운로드 실패:", err));
    """
    try:
        driver.execute_script(js_script)
        return True
    except Exception as e:
        print(f"   [오류] 브라우저 지시 실패: {e}")
        return False

def parse_html_to_txt(html_path, txt_path):
    """
    저장된 HTML 파일을 열어 제목, 날짜, URL, 본문을 추출하고 TXT 파일로 변환합니다.
    7일이 지난 기사는 TXT 변환을 취소하고 HTML 원본을 삭제합니다.
    """
    try:
        # 파일은 이 블록을 빠져나가면 자동으로 닫힙니다 (삭제를 위해 닫혀있어야 함).
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        # 1. 기사 제목 추출
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        else:
            h1_tag = soup.find("h1")
            if h1_tag:
                title = h1_tag.get_text().strip()
            elif soup.title:
                title = soup.title.get_text().replace("| GenomeWeb", "").strip()
        title = title if title else "No Title Available"

        # 2. 기사 작성 날짜 추출
        date_str = ""
        meta_date = soup.find("meta", property="article:published_time") or soup.find("meta", name="sailthru.date")
        if meta_date and meta_date.get("content"):
            date_str = meta_date["content"].split("T")[0].strip()
        else:
            time_tag = soup.find("time")
            if time_tag:
                date_str = time_tag.get_text().strip()
        date_str = date_str if date_str else today.strftime('%Y-%m-%d')

        # --- [추가/수정된 부분] 7일 경과 여부 판단 및 HTML 삭제 ---
        try:
            article_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # GenomeWeb의 다른 날짜 포맷 대비
                article_date = datetime.strptime(date_str, "%B %d, %Y")
            except ValueError:
                # 파싱 불가능한 형식일 경우 안전을 위해 오늘 날짜로 처리 (삭제 방지)
                article_date = today
                
        if article_date < sevenday_ago:
            print(f"   [스킵] 7일이 경과된 기사입니다 ({date_str}). HTML 파일을 삭제합니다.")
            if os.path.exists(html_path):
                os.remove(html_path)
            return False  # txt 파일 작성 중단
        # ----------------------------------------------------------

        # 3. 기사 전체 URL 추출
        article_url = ""
        canonical_link = soup.find("link", rel="canonical")
        if canonical_link and canonical_link.get("href"):
            article_url = canonical_link["href"].strip()
        else:
            og_url = soup.find("meta", property="og:url")
            if og_url and og_url.get("content"):
                article_url = og_url["content"].strip()
        article_url = article_url if article_url else "URL Not Found"

        # 4. 기사 본문 내용 추출
        body_content = []
        body_div = soup.find("div", class_="body") or soup.find(class_=re.compile("item--paragraph--type--body"))
        
        if body_div:
            paragraphs = body_div.find_all("p")
            if paragraphs:
                for p in paragraphs:
                    p_text = p.get_text().strip()
                    if p_text:
                        if "To read the full story" in p_text or "Already Registered" in p_text:
                            continue
                        body_content.append(p_text)
            else:
                body_content.append(body_div.get_text(separator="\n").strip())
        
        if not body_content:
            main_content = soup.find("main") or soup.find("article")
            if main_content:
                body_content.append(main_content.get_text(separator="\n").strip())
            else:
                body_content.append("Body Content Not Available")

        final_body_text = "\n\n".join(body_content)

        # 5. TXT 파일 쓰기
        with open(txt_path, "w", encoding="utf-8") as out_f:
            out_f.write(f"{title}\n")
            out_f.write(f"{date_str}\n")
            out_f.write(f"{article_url}\n")
            out_f.write(f"{final_body_text}")
            
        print(f"   Successfully converted to TXT: {os.path.basename(txt_path)}")
        return True

    except Exception as parse_err:
        print(f"   [파싱 오류 발생]: {parse_err}")
        return False


if __name__ == "__main__":
    target_url = "https://www.genomeweb.com/"
    
    if not os.path.exists(SAVE_FOLDER_PATH):
        os.makedirs(SAVE_FOLDER_PATH)
        print(f"📂 스크립트 위치에 '{TARGET_FOLDER_NAME}' 폴더를 생성했습니다.")
        
    driver = create_driver()
    
    try:
        links = get_main_page_articles(driver, target_url)
        print(f"\n총 {len(links)}개의 기사 링크를 찾았습니다.")
        
        if not links:
            print("수집된 링크가 없어 종료합니다.")
            driver.quit()
            exit()

        print("\n알림창 없는 초고속 연속 다운로드 및 텍스트 자동 파싱을 시작합니다.\n" + "="*50)
        
        for idx, link in enumerate(links, 1):
            filename = clean_filename(link)
            print(f"[{idx}/{len(links)}] 작업 중: {filename}")
            
            browser_save_link_as(driver, link, filename)
            
            temp_source_path = os.path.join(CHROME_DOWNLOAD_DIR, filename)
            final_target_html_path = os.path.join(SAVE_FOLDER_PATH, filename)
            final_target_txt_path = os.path.splitext(final_target_html_path)[0] + ".txt"
            
            file_moved = False
            for _ in range(30):
                if os.path.exists(temp_source_path):
                    try:
                        shutil.move(temp_source_path, final_target_html_path)
                        file_moved = True
                        break
                    except PermissionError:
                        time.sleep(3)
                time.sleep(3)
            
            if file_moved:
                parse_html_to_txt(final_target_html_path, final_target_txt_path)
            else:
                if not os.path.exists(final_target_html_path):
                    print(f"   ⚠️ {filename} 이동 지연 또는 실패 (수동 확인 필요)")
            
            time.sleep(5)
            
        print("="*50 + "\n모든 다운로드, 파싱 및 폴더 정리 작업이 완료되었습니다.")
        print(f"📂 저장 완료된 위치: {SAVE_FOLDER_PATH}")
        
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")
            
    finally:
        time.sleep(3)
        driver.quit()
