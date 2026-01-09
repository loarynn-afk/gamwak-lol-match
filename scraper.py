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
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    # URL 생성
    summoner_name = f"{riot_id}-{tag}"
    encoded_name = requests.utils.quote(summoner_name)
    url = f"https://www.op.gg/summoners/kr/{encoded_name}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        html = response.text
        
        # __NEXT_DATA__ JSON 추출 (Next.js 앱의 초기 데이터)
        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        
        if next_data_match:
            next_data = json.loads(next_data_match.group(1))
            return parse_next_data(next_data)
        
        # 대체: HTML에서 직접 파싱
        return parse_html_fallback(html)
        
    except Exception as e:
        print(f"요청 실패: {riot_id}#{tag} - {e}")
        return get_default_data()

def parse_next_data(data: dict) -> dict:
    """Next.js __NEXT_DATA__에서 소환사 정보 추출"""
    try:
        props = data.get("props", {}).get("pageProps", {})
        
        # 소환사 데이터
        summoner = props.get("data", {})
        
        # 솔로랭크 정보
        league_stats = summoner.get("league_stats", [])
        solo_rank = None
        
        for league in league_stats:
            if league.get("queue_info", {}).get("game_type") == "SOLORANKED":
                solo_rank = league
                break
        
        if solo_rank:
            tier_info = solo_rank.get("tier_info", {})
            tier = tier_info.get("tier", "Unranked")
            division = tier_info.get("division", "")
            lp = tier_info.get("lp", 0)
            
            wins = solo_rank.get("win", 0)
            losses = solo_rank.get("lose", 0)
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
        
        return get_default_data()
        
    except Exception as e:
        print(f"NEXT_DATA 파싱 실패: {e}")
        return get_default_data()

def parse_html_fallback(html: str) -> dict:
    """HTML에서 직접 티어 정보 추출 (대체 방법)"""
    try:
        # 티어 정보 패턴들
        patterns = [
            r'"tier":"(\w+)","division":(\d+),"lp":(\d+)',
            r'"tier_info":\{"tier":"(\w+)","division":(\d+),"lp":(\d+)',
            r'tier&quot;:&quot;(\w+)&quot;,&quot;division&quot;:(\d+),&quot;lp&quot;:(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                tier = match.group(1)
                division = match.group(2)
                lp = match.group(3)
                
                # 승패 추출
                wins_match = re.search(r'"win":(\d+)', html)
                losses_match = re.search(r'"lose":(\d+)', html)
                
                wins = int(wins_match.group(1)) if wins_match else 0
                losses = int(losses_match.group(1)) if losses_match else 0
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
        
        # IRON, BRONZE 등 티어명으로 직접 검색
        tier_patterns = [
            (r'"tier":"(IRON|BRONZE|SILVER|GOLD|PLATINUM|EMERALD|DIAMOND|MASTER|GRANDMASTER|CHALLENGER)"', 
             r'"division":(\d+)', r'"lp":(\d+)')
        ]
        
        for tier_p, div_p, lp_p in tier_patterns:
            tier_match = re.search(tier_p, html, re.IGNORECASE)
            if tier_match:
                tier = tier_match.group(1)
                div_match = re.search(div_p, html)
                lp_match = re.search(lp_p, html)
                
                division = div_match.group(1) if div_match else ""
                lp = lp_match.group(1) if lp_match else "0"
                
                wins_match = re.search(r'"win":(\d+)', html)
                losses_match = re.search(r'"lose":(\d+)', html)
                
                wins = int(wins_match.group(1)) if wins_match else 0
                losses = int(losses_match.group(1)) if losses_match else 0
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
        
        return get_default_data()
        
    except Exception as e:
        print(f"HTML 파싱 실패: {e}")
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
    
    result = {
        "updated_at": datetime.now().isoformat(),
        "players": {}
    }
    
    for player in PLAYERS:
        print(f"수집 중: {player['name']} ({player['riot_id']}#{player['tag']})")
        
        data = get_opgg_data(player["riot_id"], player["tag"])
        
        # 결과 출력
        if data["tier"] != "Unranked":
            print(f"  → {data['tier']} {data['division']} {data['lp']}LP / {data['wins']}승 {data['losses']}패 ({data['winrate']}%)")
        else:
            print(f"  → Unranked")
        
        result["players"][player["name"]] = {
            **player,
            **data,
            "opgg_url": f"https://www.op.gg/summoners/kr/{requests.utils.quote(player['riot_id'])}-{player['tag']}"
        }
        
        # 요청 간격 (OP.GG 부하 방지)
        time.sleep(3)
    
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
