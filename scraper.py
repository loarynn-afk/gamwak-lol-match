import requests
import json
import re
import time
from datetime import datetime

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

def get_opgg_data(riot_id: str, tag: str) -> dict:
    """OP.GG에서 소환사 데이터 가져오기"""
    
    # URL 인코딩된 소환사명
    encoded_name = requests.utils.quote(f"{riot_id}-{tag}")
    
    # OP.GG 내부 API 시도
    api_url = f"https://lol-web-api.op.gg/api/v1.0/internal/bypass/summoners/kr/{encoded_name}/summary"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.op.gg/",
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return parse_api_response(data)
    except Exception as e:
        print(f"API 요청 실패: {riot_id}#{tag} - {e}")
    
    # 대체 방법: HTML 파싱
    return get_opgg_html(riot_id, tag)

def get_opgg_html(riot_id: str, tag: str) -> dict:
    """OP.GG HTML에서 데이터 파싱"""
    
    encoded_name = requests.utils.quote(f"{riot_id}-{tag}")
    url = f"https://www.op.gg/summoners/kr/{encoded_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        # 티어 추출
        tier_match = re.search(r'"tier":"(\w+)"', html)
        tier = tier_match.group(1) if tier_match else "Unranked"
        
        # 디비전 추출
        division_match = re.search(r'"division":(\d+)', html)
        division = division_match.group(1) if division_match else ""
        
        # LP 추출
        lp_match = re.search(r'"lp":(\d+)', html)
        lp = lp_match.group(1) if lp_match else "0"
        
        # 승/패 추출
        wins_match = re.search(r'"wins":(\d+)', html)
        losses_match = re.search(r'"losses":(\d+)', html)
        wins = int(wins_match.group(1)) if wins_match else 0
        losses = int(losses_match.group(1)) if losses_match else 0
        
        # 승률 계산
        total = wins + losses
        winrate = round(wins / total * 100) if total > 0 else 0
        
        return {
            "tier": tier.capitalize(),
            "division": division,
            "lp": lp,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"HTML 파싱 실패: {riot_id}#{tag} - {e}")
        return {
            "tier": "Unknown",
            "division": "",
            "lp": "0",
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "updated": datetime.now().isoformat()
        }

def parse_api_response(data: dict) -> dict:
    """OP.GG API 응답 파싱"""
    try:
        solo_rank = data.get("data", {}).get("solo_tier_info", {})
        
        tier = solo_rank.get("tier", "Unranked")
        division = solo_rank.get("division", "")
        lp = solo_rank.get("lp", 0)
        
        stats = data.get("data", {}).get("stats", {})
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        
        total = wins + losses
        winrate = round(wins / total * 100) if total > 0 else 0
        
        return {
            "tier": tier.capitalize() if tier else "Unranked",
            "division": str(division) if division else "",
            "lp": str(lp),
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "updated": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"API 응답 파싱 실패: {e}")
        return {
            "tier": "Unknown",
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
    
    result = {
        "updated_at": datetime.now().isoformat(),
        "players": {}
    }
    
    for player in PLAYERS:
        print(f"수집 중: {player['name']} ({player['riot_id']}#{player['tag']})")
        
        data = get_opgg_data(player["riot_id"], player["tag"])
        
        result["players"][player["name"]] = {
            **player,
            **data,
            "opgg_url": f"https://www.op.gg/summoners/kr/{requests.utils.quote(player['riot_id'])}-{player['tag']}"
        }
        
        # 요청 간격 (OP.GG 부하 방지)
        time.sleep(2)
    
    # JSON 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"크롤링 완료: data.json 저장됨")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
