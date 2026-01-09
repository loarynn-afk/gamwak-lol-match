import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 12명 선수 정보
PLAYERS = [
    # 우왁굳 팀
    {"name": "우왁굳", "riot_id": "메시아빠우왁굳", "tag": "KR1", "team": "wak", "position": "탑"},
    {"name": "릴파", "riot_id": "내가바로 릴파다", "tag": "KR1", "team": "wak", "position": "정글"},
    {"name": "빅토리", "riot_id": "ViCTory", "tag": "0219", "team": "wak", "position": "미드"},
    {"name": "비챤", "riot_id": "빛 챤", "tag": "xoxv", "team": "wak", "position": "원딜"},
    {"name": "고세구", "riot_id": "레츠고세구", "tag": "KR1", "team": "wak", "position": "서포터"},
    {"name": "천양", "riot_id": "돈까스", "tag": "KR1", "team": "wak", "position": "후보"},
    
    # 감스트 팀
    {"name": "감스트", "riot_id": "정글의신", "tag": "1094", "team": "gam", "position": "탑"},
    {"name": "망구랑", "riot_id": "cs못먹어서미안해", "tag": "MGR", "team": "gam", "position": "정글"},
    {"name": "단츄", "riot_id": "단바오", "tag": "owo", "team": "gam", "position": "미드"},
    {"name": "유설아", "riot_id": "정카유설아", "tag": "1445", "team": "gam", "position": "원딜"},
    {"name": "따린", "riot_id": "무슨 생각일까", "tag": "KR1", "team": "gam", "position": "서포터"},
    {"name": "박재박", "riot_id": "올리비아재", "tag": "박재박", "team": "gam", "position": "후보"},
]

def setup_driver():
    """Selenium WebDriver 설정"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 헤드리스 모드
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--lang=ko-KR")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_opgg_data(driver, riot_id: str, tag: str) -> dict:
    """OP.GG에서 소환사 데이터 가져오기"""
    
    # URL 생성
    summoner_name = f"{riot_id}-{tag}"
    from urllib.parse import quote
    encoded_name = quote(summoner_name)
    url = f"https://www.op.gg/summoners/kr/{encoded_name}"
    
    try:
        driver.get(url)
        
        # 페이지 로딩 대기 (티어 정보가 나타날 때까지)
        time.sleep(3)
        
        # 티어 정보 추출
        tier_data = extract_tier_info(driver)
        
        return tier_data
        
    except Exception as e:
        print(f"크롤링 실패: {riot_id}#{tag} - {e}")
        return get_default_data()

def extract_tier_info(driver) -> dict:
    """페이지에서 티어 정보 추출"""
    try:
        # 방법 1: CSS 선택자로 직접 찾기
        try:
            # 티어 텍스트 (예: "Iron 2", "Bronze 3")
            tier_element = driver.find_element(By.CSS_SELECTOR, "[class*='tier-rank']")
            tier_text = tier_element.text.strip()
            
            # "Iron 2" -> tier="Iron", division="2"
            parts = tier_text.split()
            if len(parts) >= 2:
                tier = parts[0]
                division = parts[1]
            else:
                tier = tier_text
                division = ""
                
        except:
            tier = "Unranked"
            division = ""
        
        # LP 추출
        try:
            lp_element = driver.find_element(By.CSS_SELECTOR, "[class*='lp']")
            lp_text = lp_element.text
            lp_match = re.search(r'(\d+)', lp_text)
            lp = lp_match.group(1) if lp_match else "0"
        except:
            lp = "0"
        
        # 승/패 추출
        try:
            # "23승 21패" 형태 찾기
            win_lose_element = driver.find_element(By.CSS_SELECTOR, "[class*='win-lose'], [class*='record']")
            win_lose_text = win_lose_element.text
            
            wins_match = re.search(r'(\d+)승', win_lose_text)
            losses_match = re.search(r'(\d+)패', win_lose_text)
            
            wins = int(wins_match.group(1)) if wins_match else 0
            losses = int(losses_match.group(1)) if losses_match else 0
        except:
            # 대체 방법: 페이지 전체 텍스트에서 찾기
            page_text = driver.page_source
            wins_match = re.search(r'(\d+)승', page_text)
            losses_match = re.search(r'(\d+)패', page_text)
            wins = int(wins_match.group(1)) if wins_match else 0
            losses = int(losses_match.group(1)) if losses_match else 0
        
        # 승률 계산
        total = wins + losses
        winrate = round(wins / total * 100) if total > 0 else 0
        
        # Unranked가 아닌 경우에만 데이터 반환
        if tier.lower() not in ["unranked", ""]:
            return {
                "tier": tier.capitalize(),
                "division": division,
                "lp": lp,
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
                "updated": datetime.now().isoformat()
            }
        
        # 대체 방법: 페이지 소스에서 JSON 데이터 추출
        return extract_from_page_source(driver)
        
    except Exception as e:
        print(f"티어 정보 추출 실패: {e}")
        return get_default_data()

def extract_from_page_source(driver) -> dict:
    """페이지 소스에서 티어 정보 추출 (대체 방법)"""
    try:
        page_source = driver.page_source
        
        # __NEXT_DATA__ JSON 추출
        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page_source, re.DOTALL)
        
        if next_data_match:
            next_data = json.loads(next_data_match.group(1))
            props = next_data.get("props", {}).get("pageProps", {})
            data = props.get("data", {})
            
            # 솔로랭크 정보 찾기
            league_stats = data.get("league_stats", [])
            for league in league_stats:
                queue_info = league.get("queue_info", {})
                if queue_info.get("game_type") == "SOLORANKED":
                    tier_info = league.get("tier_info", {})
                    return {
                        "tier": tier_info.get("tier", "Unranked").capitalize(),
                        "division": str(tier_info.get("division", "")),
                        "lp": str(tier_info.get("lp", 0)),
                        "wins": league.get("win", 0),
                        "losses": league.get("lose", 0),
                        "winrate": round(league.get("win", 0) / (league.get("win", 0) + league.get("lose", 1)) * 100),
                        "updated": datetime.now().isoformat()
                    }
        
        # 정규식으로 직접 추출
        tier_patterns = [
            r'"tier":"(IRON|BRONZE|SILVER|GOLD|PLATINUM|EMERALD|DIAMOND|MASTER|GRANDMASTER|CHALLENGER)"',
        ]
        
        for pattern in tier_patterns:
            tier_match = re.search(pattern, page_source, re.IGNORECASE)
            if tier_match:
                tier = tier_match.group(1)
                
                div_match = re.search(r'"division":(\d+)', page_source)
                lp_match = re.search(r'"lp":(\d+)', page_source)
                win_match = re.search(r'"win":(\d+)', page_source)
                lose_match = re.search(r'"lose":(\d+)', page_source)
                
                wins = int(win_match.group(1)) if win_match else 0
                losses = int(lose_match.group(1)) if lose_match else 0
                total = wins + losses
                
                return {
                    "tier": tier.capitalize(),
                    "division": div_match.group(1) if div_match else "",
                    "lp": lp_match.group(1) if lp_match else "0",
                    "wins": wins,
                    "losses": losses,
                    "winrate": round(wins / total * 100) if total > 0 else 0,
                    "updated": datetime.now().isoformat()
                }
        
        return get_default_data()
        
    except Exception as e:
        print(f"페이지 소스 파싱 실패: {e}")
        return get_default_data()

def get_default_data() -> dict:
    """기본 데이터 반환"""
    return {
        "tier": "Unranked",
        "division": "",
        "lp": "0",
        "wins": 0,
        "losses": 0,
        "winrate": 0,
        "updated": datetime.now().isoformat()
    }

def main():
    """메인 크롤링 함수"""
    print(f"크롤링 시작: {datetime.now()}")
    
    # WebDriver 설정
    driver = setup_driver()
    
    result = {
        "updated_at": datetime.now().isoformat(),
        "players": {}
    }
    
    try:
        for player in PLAYERS:
            print(f"수집 중: {player['name']} ({player['riot_id']}#{player['tag']})")
            
            data = get_opgg_data(driver, player["riot_id"], player["tag"])
            
            # 결과 출력
            if data["tier"] != "Unranked":
                print(f"  → {data['tier']} {data['division']} {data['lp']}LP / {data['wins']}승 {data['losses']}패 ({data['winrate']}%)")
            else:
                print(f"  → Unranked")
            
            from urllib.parse import quote
            result["players"][player["name"]] = {
                **player,
                **data,
                "opgg_url": f"https://www.op.gg/summoners/kr/{quote(player['riot_id'])}-{player['tag']}"
            }
            
            # 요청 간격
            time.sleep(2)
    
    finally:
        driver.quit()
    
    # JSON 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n크롤링 완료: data.json 저장됨")
    
    # 요약 출력
    print("\n=== 수집 결과 요약 ===")
    ranked_count = sum(1 for p in result["players"].values() if p["tier"] != "Unranked")
    print(f"랭크 정보 수집: {ranked_count}/{len(PLAYERS)}명")

if __name__ == "__main__":
    main()
