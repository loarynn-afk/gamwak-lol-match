import requests
import json
import time
import re
from datetime import datetime
from urllib.parse import quote

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
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    
    summoner_name = f"{riot_id}-{tag}"
    encoded_name = quote(summoner_name)
    url = f"https://www.op.gg/summoners/kr/{encoded_name}"
    
    try:
        print(f"  요청: {url[:60]}...")
        response = requests.get(url, headers=headers, timeout=20)
        print(f"  응답: {response.status_code}")
        
        if response.status_code == 200:
            return parse_opgg_html(response.text)
        else:
            print(f"  HTTP 에러: {response.status_code}")
            return get_default_data()
            
    except Exception as e:
        print(f"  요청 에러: {e}")
        return get_default_data()

def parse_opgg_html(html: str) -> dict:
    """OP.GG HTML에서 티어 정보 추출"""
    
    result = get_default_data()
    
    try:
        # __NEXT_DATA__ JSON 추출
        next_data_match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', 
            html, 
            re.DOTALL
        )
        
        if not next_data_match:
            print("  __NEXT_DATA__ 없음, 정규식 파싱 시도...")
            return parse_with_regex(html)
        
        next_data = json.loads(next_data_match.group(1))
        props = next_data.get("props", {}).get("pageProps", {})
        data = props.get("data", {})
        
        if not data:
            print("  data 없음")
            return parse_with_regex(html)
        
        # 1. 현재 시즌 솔로랭크 확인
        league_stats = data.get("league_stats", [])
        current_solo = None
        current_flex = None
        
        for league in league_stats:
            queue_info = league.get("queue_info", {})
            game_type = queue_info.get("game_type", "")
            
            if game_type == "SOLORANKED":
                current_solo = league
            elif game_type == "FLEXRANKED":
                current_flex = league
        
        # 솔로랭크 있으면 사용
        if current_solo:
            tier_info = current_solo.get("tier_info", {})
            tier = tier_info.get("tier", "")
            
            if tier and tier.upper() != "UNRANKED":
                wins = current_solo.get("win", 0)
                losses = current_solo.get("lose", 0)
                total = wins + losses
                
                result = {
                    "tier": tier.capitalize(),
                    "division": str(tier_info.get("division", "")),
                    "lp": str(tier_info.get("lp", 0)),
                    "wins": wins,
                    "losses": losses,
                    "winrate": round(wins / total * 100) if total > 0 else 0,
                    "is_previous_season": False,
                    "updated": datetime.now().isoformat()
                }
                print(f"  현재 시즌 솔랭: {result['tier']} {result['division']}")
                return result
        
        # 2. 현재 시즌 언랭이면 → 지난 시즌 티어 확인
        previous_seasons = data.get("previous_seasons", [])
        
        if previous_seasons:
            # 가장 최근 시즌 (첫 번째)
            latest_season = previous_seasons[0]
            tier_info = latest_season.get("tier_info", {})
            tier = tier_info.get("tier", "")
            season_id = latest_season.get("season_id", "")
            
            if tier and tier.upper() != "UNRANKED":
                result = {
                    "tier": tier.capitalize(),
                    "division": str(tier_info.get("division", "")),
                    "lp": str(tier_info.get("lp", 0)),
                    "wins": 0,
                    "losses": 0,
                    "winrate": 0,
                    "is_previous_season": True,
                    "season": season_id,
                    "updated": datetime.now().isoformat()
                }
                print(f"  지난 시즌({season_id}): {result['tier']} {result['division']}")
                return result
        
        # 3. 자유랭크라도 있으면 사용
        if current_flex:
            tier_info = current_flex.get("tier_info", {})
            tier = tier_info.get("tier", "")
            
            if tier and tier.upper() != "UNRANKED":
                wins = current_flex.get("win", 0)
                losses = current_flex.get("lose", 0)
                total = wins + losses
                
                result = {
                    "tier": tier.capitalize(),
                    "division": str(tier_info.get("division", "")),
                    "lp": str(tier_info.get("lp", 0)),
                    "wins": wins,
                    "losses": losses,
                    "winrate": round(wins / total * 100) if total > 0 else 0,
                    "is_flex": True,
                    "updated": datetime.now().isoformat()
                }
                print(f"  자유랭크: {result['tier']} {result['division']}")
                return result
        
        print("  랭크 정보 없음")
        return result
        
    except json.JSONDecodeError as e:
        print(f"  JSON 파싱 에러: {e}")
        return parse_with_regex(html)
    except Exception as e:
        print(f"  파싱 에러: {e}")
        return get_default_data()

def parse_with_regex(html: str) -> dict:
    """정규식으로 티어 정보 추출 (백업)"""
    
    result = get_default_data()
    
    try:
        # 티어 패턴 찾기
        tier_pattern = r'"tier":"(IRON|BRONZE|SILVER|GOLD|PLATINUM|EMERALD|DIAMOND|MASTER|GRANDMASTER|CHALLENGER)"'
        tier_match = re.search(tier_pattern, html, re.IGNORECASE)
        
        if tier_match:
            tier = tier_match.group(1)
            
            # division, lp, wins, losses 찾기
            div_match = re.search(r'"division":(\d+)', html)
            lp_match = re.search(r'"lp":(\d+)', html)
            win_match = re.search(r'"win":(\d+)', html)
            lose_match = re.search(r'"lose":(\d+)', html)
            
            wins = int(win_match.group(1)) if win_match else 0
            losses = int(lose_match.group(1)) if lose_match else 0
            total = wins + losses
            
            result = {
                "tier": tier.capitalize(),
                "division": div_match.group(1) if div_match else "",
                "lp": lp_match.group(1) if lp_match else "0",
                "wins": wins,
                "losses": losses,
                "winrate": round(wins / total * 100) if total > 0 else 0,
                "updated": datetime.now().isoformat()
            }
            print(f"  정규식 파싱: {result['tier']} {result['division']}")
        
        return result
        
    except Exception as e:
        print(f"  정규식 파싱 에러: {e}")
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
    print(f"=" * 50)
    print(f"크롤링 시작: {datetime.now()}")
    print(f"=" * 50)
    
    result = {
        "updated_at": datetime.now().isoformat(),
        "players": {}
    }
    
    for player in PLAYERS:
        print(f"\n[{player['name']}] {player['riot_id']}#{player['tag']}")
        
        data = get_opgg_data(player["riot_id"], player["tag"])
        
        # 결과 저장
        result["players"][player["name"]] = {
            **player,
            **data,
            "opgg_url": f"https://www.op.gg/summoners/kr/{quote(player['riot_id'])}-{player['tag']}"
        }
        
        # 요청 간격 (OP.GG 부하 방지)
        time.sleep(3)
    
    # JSON 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 요약 출력
    print(f"\n" + "=" * 50)
    print("=== 수집 결과 요약 ===")
    print(f"=" * 50)
    
    ranked_count = 0
    for name, p in result["players"].items():
        tier = p.get("tier", "Unranked")
        division = p.get("division", "")
        
        if tier != "Unranked":
            ranked_count += 1
            extra = ""
            if p.get("is_previous_season"):
                extra = f" (지난시즌 {p.get('season', '')})"
            elif p.get("is_flex"):
                extra = " (자유랭크)"
            print(f"  ✓ {name}: {tier} {division}{extra}")
        else:
            print(f"  ✗ {name}: Unranked")
    
    print(f"\n랭크 정보 수집: {ranked_count}/{len(PLAYERS)}명")
    print(f"data.json 저장 완료!")

if __name__ == "__main__":
    main()
